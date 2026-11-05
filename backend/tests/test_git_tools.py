import pytest
from app.tools.git_tools import get_git_diff, get_git_history, get_safe_git_env
from app.tools.workspace import InvalidInputError, PathTraversalError


def test_safe_git_env():
    env = get_safe_git_env()
    assert env["GIT_TERMINAL_PROMPT"] == "0"
    assert env["GIT_CONFIG_NOSYSTEM"] == "1"
    assert env["GIT_PAGER"] == "cat"
    assert env["GIT_EXTERNAL_DIFF"] == ""
    assert "INCIDENTOS_API_TOKEN" not in env


def test_git_history(temp_workspace):
    res = get_git_history(count=5, demo_root=temp_workspace)
    assert res.audit.status == "SUCCESS"
    assert len(res.commits) >= 1
    assert res.commits[0].author == "Test User"
    assert "Initial test commit" in res.commits[0].message


def test_git_history_path_filter(temp_workspace):
    res = get_git_history(path="src/PaymentValidator.java", demo_root=temp_workspace)
    assert res.audit.status == "SUCCESS"
    assert len(res.commits) >= 1


def test_git_history_reject_flag_injection(temp_workspace):
    with pytest.raises(InvalidInputError):
        get_git_history(branch="--upload-pack=evil", demo_root=temp_workspace)

    with pytest.raises(InvalidInputError):
        get_git_history(branch="main/../../etc", demo_root=temp_workspace)


def test_git_diff(temp_workspace):
    # Diff working tree
    res = get_git_diff(demo_root=temp_workspace)
    assert res.audit.status == "SUCCESS"
    assert isinstance(res.diff_content, str)


def test_git_diff_reject_malformed_hash(temp_workspace):
    with pytest.raises(InvalidInputError):
        get_git_diff(target_commit="invalid; rm -rf /", demo_root=temp_workspace)

    with pytest.raises(InvalidInputError):
        get_git_diff(base_commit="HEAD~1 && touch evil", demo_root=temp_workspace)


def test_api_git_endpoints(client, temp_workspace, monkeypatch):
    import app.tools.git_tools as git_mod
    monkeypatch.setattr(git_mod, "DEMO_WORKSPACE_ROOT", temp_workspace)

    # Valid history request
    resp = client.get("/api/tools/git/history?count=5")
    assert resp.status_code == 200
    data = resp.json()
    assert len(data["commits"]) >= 1

    # Traversal in path filter
    resp2 = client.get("/api/tools/git/history?path=../../outside")
    assert resp2.status_code == 403

    # Malformed commit hash in diff
    resp3 = client.get("/api/tools/git/diff?target_commit=malformed_hash_123$")
    assert resp3.status_code == 400
