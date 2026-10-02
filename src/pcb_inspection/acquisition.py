"""Selective owner-hosted uncompressed TAR acquisition using validated byte ranges.

Reads headers while skipping other categories' payloads. Never falls back to a
full archive download. Each material request is tied to the initial S3 ETag.
"""
import argparse
import csv
import http.client
import json
from pathlib import Path, PurePosixPath
import tarfile
import time
from urllib.parse import urlsplit
from .provenance import sha256_file, immutable_json

ARCHIVE_URL = 'https://amazon-visual-anomaly.s3.us-west-2.amazonaws.com/VisA_20220922.tar'
SOURCE_REVISION = '2a692ab575001cbde74d402d897a7286086c6199'


class RangeReader:
    def __init__(self, url):
        parsed = urlsplit(url)
        self.host, self.path = parsed.netloc, parsed.path
        self.conn = http.client.HTTPSConnection(self.host, timeout=60)
        self.conn.request('HEAD', self.path)
        response = self.conn.getresponse()
        if response.status != 200:
            raise RuntimeError(f'Archive HEAD failed: {response.status}')
        self.size = int(response.getheader('Content-Length'))
        self.etag = response.getheader('ETag')
        self.last_modified = response.getheader('Last-Modified')
        response.read()
        self.transferred = 0
        self.cache_enabled = False
        self.cache_start = 0
        self.cache = b''

    def get(self, start, length):
        if not length:
            return b''
        if self.cache_enabled:
            if self.cache_start <= start and start+length <= self.cache_start+len(self.cache):
                return self.cache[start-self.cache_start:start-self.cache_start+length]
            fetched_length = min(max(length, 8*1024*1024), self.size-start)
        else:
            fetched_length = length
        for attempt in range(4):
            try:
                self.conn.request('GET', self.path, headers={'Range': f'bytes={start}-{start+fetched_length-1}', 'If-Match': self.etag})
                response = self.conn.getresponse()
                expected = f'bytes {start}-{start+fetched_length-1}/{self.size}'
                if response.status != 206 or response.getheader('Content-Range') != expected or response.getheader('ETag') != self.etag:
                    response.close()
                    raise RuntimeError('Server did not honor exact range / ETag; full download refused')
                result = response.read()
                if len(result) != fetched_length:
                    raise RuntimeError('Truncated byte range')
                self.transferred += fetched_length
                if self.cache_enabled:
                    self.cache_start, self.cache = start, result
                return result[:length]
            except (OSError, http.client.HTTPException):
                self.conn.close()
                self.conn = http.client.HTTPSConnection(self.host, timeout=60)
                time.sleep(attempt + 1)
        raise RuntimeError('Range request retries exhausted')


def acquire_pcb1(destination, max_selected_bytes=400_000_000):
    destination = Path(destination)
    destination.mkdir(parents=True, exist_ok=True)
    completed = destination / 'acquisition.json'
    if completed.exists():
        record = json.loads(completed.read_text())
        for entry in record['members']:
            if sha256_file(destination/entry['path']) != entry['sha256']:
                raise RuntimeError(f'Acquired member hash changed: {entry["path"]}')
        return record
    reader = RangeReader(ARCHIVE_URL)
    print(json.dumps({'archive_bytes': reader.size, 'etag': reader.etag, 'strategy': 'selective byte ranges', 'max_selected_bytes': max_selected_bytes}), flush=True)
    # The official CSV defines all required image/mask members. Locate the
    # category in this alphabetically ordered, uncompressed owner TAR with
    # bounded probes, then verify complete CSV coverage before stopping.
    split_file = destination / '1cls.csv'
    if not split_file.exists():
        raise FileNotFoundError('Retrieve the pinned official 1cls.csv first')
    with split_file.open() as stream:
        required = {row[field] for row in csv.DictReader(stream) if row['object'] == 'pcb1' for field in ('image', 'mask') if row[field]}
    low, high = 0, reader.size - 2_000_384
    while high - low > 4_000_000:
        probe = ((low + high) // 2) // 512 * 512
        block = reader.get(probe, 2_000_384)
        found = None
        for position in range(0, len(block)-512, 512):
            try:
                candidate = tarfile.TarInfo.frombuf(block[position:position+512], 'utf8', 'strict')
                if candidate.name and candidate.type in (tarfile.REGTYPE, tarfile.DIRTYPE):
                    found = (probe + position, candidate)
                    break
            except (tarfile.HeaderError, UnicodeError, ValueError):
                continue
        if found is None:
            raise RuntimeError('Bounded category probe found no header; sequential scan required')
        position, candidate = found
        print(f'probe={position} category={candidate.name.split("/")[0]}', flush=True)
        if candidate.name.split('/')[0] < 'pcb1':
            low = position
        else:
            high = position
    offset, selected_bytes, entries = low, 0, []
    seen = set()
    started = time.time()
    while offset + 512 <= reader.size:
        header = reader.get(offset, 512)
        if not any(header):
            break
        info = tarfile.TarInfo.frombuf(header, 'utf8', 'strict')
        path = PurePosixPath(info.name)
        if path.is_absolute() or '..' in path.parts:
            raise ValueError('Unsafe archive member')
        if info.type not in (tarfile.REGTYPE, tarfile.AREGTYPE, tarfile.DIRTYPE):
            raise ValueError(f'Unsupported archive member type: {info.name} {info.type!r}')
        if path.parts and path.parts[0] == 'pcb1' and info.isfile():
            reader.cache_enabled = True
            selected_bytes += info.size
            if selected_bytes > max_selected_bytes:
                raise RuntimeError('PCB1 selected-byte budget exceeded; no full archive fallback')
            target = destination.joinpath(*path.parts)
            target.parent.mkdir(parents=True, exist_ok=True)
            if not target.exists():
                body = reader.get(offset + 512, info.size)
                with target.open('xb') as stream:
                    stream.write(body)
            if target.stat().st_size != info.size:
                raise RuntimeError(f'Existing member has unexpected size: {target}')
            entries.append({'path': str(path), 'archive_offset': offset + 512, 'bytes': info.size, 'sha256': sha256_file(target)})
            seen.add(str(path))
        offset += 512 + ((info.size + 511) // 512) * 512
        if len(entries) and len(entries) % 100 == 0:
            print(f'PCB1 members={len(entries)}, transferred={reader.transferred}, archive_offset={offset}', flush=True)
        if entries and path.parts[0] != 'pcb1':
            break
    if not required.issubset(seen):
        raise RuntimeError(f'Incomplete PCB1 coverage: {len(required-seen)} required members absent')
    if not entries:
        raise RuntimeError('PCB1 was absent')
    record = {'url': ARCHIVE_URL, 'archive_bytes': reader.size, 'archive_etag': reader.etag,
              'archive_last_modified': reader.last_modified, 'retrieved_utc': time.strftime('%Y-%m-%dT%H:%M:%SZ', time.gmtime()),
              'source_revision': SOURCE_REVISION, 'license': 'CC BY 4.0', 'selected_bytes': selected_bytes,
              'required_members': len(required), 'required_members_complete': True,
              'strategy': 'Bounded category header probes, then selective member ranges; official CSV completeness checked.',
              'transferred_bytes': reader.transferred, 'elapsed_seconds': time.time()-started,
              'whole_archive_sha256': None, 'whole_archive_sha256_reason': 'Only selected byte ranges acquired; ETag is multipart, not a checksum.',
              'members': entries}
    immutable_json(destination / 'acquisition.json', record)
    return record


if __name__ == '__main__':
    parser = argparse.ArgumentParser()
    parser.add_argument('--destination', default='data/raw')
    parser.add_argument('--max-selected-bytes', type=int, default=400_000_000)
    args = parser.parse_args()
    acquire_pcb1(args.destination, args.max_selected_bytes)
