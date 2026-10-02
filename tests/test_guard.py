import json
import pytest
from pcb_inspection.guard import digest, write_new, verify_frozen, claim_test_access


def test_freeze_and_no_overwrite(tmp_path):
    (tmp_path/'config').write_text('fixed')
    protocol = {'frozen_files': {'config':digest(tmp_path/'config')}, 'source_terms_resolved':True}
    write_new(tmp_path/'docs/protocol.json', protocol)
    claim_test_access(tmp_path, protocol, 'run', {'config':digest(tmp_path/'config')})
    with pytest.raises(FileExistsError):
        claim_test_access(tmp_path, protocol, 'run', {})
    (tmp_path/'config').write_text('changed')
    with pytest.raises(ValueError, match='identity mismatch'):
        verify_frozen(tmp_path, protocol)


def test_prerequisites_and_terms(tmp_path):
    protocol = {'frozen_files': {}, 'source_terms_resolved':False}
    with pytest.raises(ValueError, match='terms'):
        verify_frozen(tmp_path, protocol)
    protocol['source_terms_resolved'] = True
    (tmp_path/'check').write_text('failed')
    with pytest.raises(ValueError, match='Prerequisite'):
        claim_test_access(tmp_path, protocol, 'run', {'check':'incorrect'})
