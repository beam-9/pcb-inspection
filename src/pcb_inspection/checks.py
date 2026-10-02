"""Execute the suite against the frozen source and record an exclusive receipt."""
import json
import subprocess
import sys
from pathlib import Path
from .guard import digest, now, verify_frozen, write_new


def main():
    root=Path(__file__).resolve().parents[2]
    protocol=json.loads((root/'docs/protocol.json').read_text());verify_frozen(root,protocol)
    result=subprocess.run([sys.executable,'-m','pytest','-q'],cwd=root,capture_output=True,text=True)
    print(result.stdout,end='');print(result.stderr,end='',file=sys.stderr)
    if result.returncode:
        raise SystemExit(result.returncode)
    receipt={'completed_utc':now(),'exit_code':result.returncode,
        'protocol_sha256':digest(root/'docs/protocol.json'),
        'command':'python -m pytest -q','stdout':result.stdout,'stderr':result.stderr}
    path=root/'artifacts/tests_passed.json'
    if path.exists():
        previous=json.loads(path.read_text())
        if previous['protocol_sha256']!=receipt['protocol_sha256'] or previous['exit_code']!=0:
            raise ValueError('Existing test receipt refers to another protocol')
        print('Current tests passed; original immutable receipt retained')
    else:
        write_new(path,receipt)


if __name__=='__main__': main()
