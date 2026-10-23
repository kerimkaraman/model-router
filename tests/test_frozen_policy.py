import copy
import json
import pytest
from eval import frozen_policy


def test_saved_policy_is_consistent():
    policy=json.loads(frozen_policy.POLICY_PATH.read_text())
    frozen_policy.verify_policy(policy)
    assert policy['escalation_threshold']==.6


def test_changed_threshold_rejected():
    policy=json.loads(frozen_policy.POLICY_PATH.read_text())
    policy['escalation_threshold']=.7
    with pytest.raises(ValueError,match='settings'):
        frozen_policy.verify_policy(policy)


def test_changed_frozen_input_rejected(tmp_path,monkeypatch):
    policy=json.loads(frozen_policy.POLICY_PATH.read_text())
    policy['frozen_input_hashes']={'input.txt':'not-the-right-hash'}
    (tmp_path/'input.txt').write_text('changed')
    monkeypatch.setattr(frozen_policy,'ROOT',tmp_path)
    with pytest.raises(ValueError,match='Frozen input changed'):
        frozen_policy.verify_policy(policy)
