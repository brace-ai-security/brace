"""GitHub approval verification with the HTTP layer mocked.

The git side is real: each test builds a temporary repository and commits the
exception file, so `git log` and `git hash-object` run for real.
"""
import io
import json
import urllib.error
import urllib.parse

import pytest

from conftest import brace, good_exception

ITEM = "R01"  # G2
STEM = f"{ITEM}-input-checks"
REL = f".brace/exceptions/{STEM}.yaml"
REPO_NAME = "acme/agent"


class FakeResponse:
    def __init__(self, body, link=""):
        self._body = json.dumps(body).encode()
        self.headers = {"Link": link} if link else {}

    def read(self):
        return self._body

    def __enter__(self):
        return self

    def __exit__(self, *a):
        return False


class FakeGitHub:
    """Routes request URLs (path + query) to canned JSON. Missing routes are 404."""

    def __init__(self):
        self.routes = {}
        self.calls = []

    def add(self, path, body, query=None, link=""):
        key = path + ("?" + urllib.parse.urlencode(query) if query else "")
        self.routes[key] = (body, link)

    def urlopen(self, req, timeout=None):
        url = req.full_url
        assert req.headers.get("Authorization") == "Bearer test-token"
        parsed = urllib.parse.urlsplit(url)
        q = urllib.parse.parse_qsl(parsed.query)
        q = [(k, v) for k, v in q if k != "per_page"]
        key = parsed.path + ("?" + urllib.parse.urlencode(q) if q else "")
        self.calls.append(key)
        if key not in self.routes:
            raise urllib.error.HTTPError(url, 404, "Not Found", {}, io.BytesIO(b"{}"))
        body, link = self.routes[key]
        return FakeResponse(body, link)


@pytest.fixture
def gh_repo(repo, monkeypatch):
    repo.git_init()
    repo.add("exceptions", STEM, good_exception(ITEM))
    repo.set_item(ITEM, outcome="gap", lead="@bob", exception=STEM)
    sha = repo.commit_all("Accept risk for R01")
    blob = repo.git("hash-object", REL)
    fake = FakeGitHub()
    monkeypatch.setattr(brace.urllib.request, "urlopen", fake.urlopen)
    monkeypatch.setenv("GITHUB_TOKEN", "test-token")
    monkeypatch.setenv("GITHUB_REPOSITORY", REPO_NAME)
    repo.sha, repo.blob, repo.fake = sha, blob, fake
    return repo


def pr(number=7, author="bob", merged=True):
    return {"number": number, "user": {"login": author}, "merged_at": "2026-10-01T10:00:00Z" if merged else None}


def review(login, state="APPROVED", commit="reviewed-commit"):
    return {"user": {"login": login}, "state": state, "commit_id": commit}


def setup_pr(r, reviews, author="bob", blob=None, merged=True, number=7):
    base = f"/repos/{REPO_NAME}"
    r.fake.add(f"{base}/commits/{r.sha}/pulls", [pr(number, author, merged)])
    r.fake.add(f"{base}/pulls/{number}/reviews", reviews)
    for rv in reviews:
        r.fake.add(f"{base}/contents/{REL}", {"sha": blob or r.blob}, query={"ref": rv["commit_id"]})


def test_approved_by_listed_user(gh_repo):
    setup_pr(gh_repo, [review("carol")])
    code, res = gh_repo.check("--approvals", "github", "--strict")
    assert code == 0, res["reasons"]
    assert "approved by @carol" in res["items"][ITEM]["approval"]


def test_approved_only_by_author(gh_repo):
    # Listed approver opened the PR and is the only approval: doesn't count.
    setup_pr(gh_repo, [review("carol")], author="carol")
    code, res = gh_repo.check("--approvals", "github")
    assert code == 1
    assert "approved only by its author @carol" in "\n".join(res["reasons"])


def test_approved_by_non_approver(gh_repo):
    setup_pr(gh_repo, [review("mallory")])
    code, res = gh_repo.check("--approvals", "github")
    assert code == 1
    assert "@mallory is not a configured approver" in "\n".join(res["reasons"])


def test_approved_by_team_member(gh_repo):
    setup_pr(gh_repo, [review("dana")])
    gh_repo.fake.add("/orgs/acme/teams/ai-governance/memberships/dana", {"state": "active", "role": "member"})
    code, res = gh_repo.check("--approvals", "github")
    assert code == 0, res["reasons"]
    assert "@acme/ai-governance" in res["items"][ITEM]["approval"]


def test_pending_team_membership_does_not_count(gh_repo):
    setup_pr(gh_repo, [review("dana")])
    gh_repo.fake.add("/orgs/acme/teams/ai-governance/memberships/dana", {"state": "pending"})
    code, _ = gh_repo.check("--approvals", "github")
    assert code == 1


def test_no_pr(gh_repo):
    gh_repo.fake.add(f"/repos/{REPO_NAME}/commits/{gh_repo.sha}/pulls", [])
    code, res = gh_repo.check("--approvals", "github")
    assert code == 1
    assert "is not part of a merged pull request" in "\n".join(res["reasons"])


def test_unmerged_pr_does_not_count_outside_pr_run(gh_repo):
    setup_pr(gh_repo, [review("carol")], merged=False)
    code, _ = gh_repo.check("--approvals", "github")
    assert code == 1


def test_current_pr_counts_during_pr_run(gh_repo, tmp_path, monkeypatch):
    setup_pr(gh_repo, [review("carol")], merged=False, number=9)
    event = tmp_path / "event.json"
    event.write_text(json.dumps({"pull_request": {"number": 9}}))
    monkeypatch.setenv("GITHUB_EVENT_NAME", "pull_request")
    monkeypatch.setenv("GITHUB_EVENT_PATH", str(event))
    code, res = gh_repo.check("--approvals", "github")
    assert code == 0, res["reasons"]
    assert any("counts once the PR is merged" in w for w in res["warnings"])


def test_file_changed_after_approval(gh_repo):
    # The approving review saw different content than the file has now.
    setup_pr(gh_repo, [review("carol")], blob="0" * 40)
    code, res = gh_repo.check("--approvals", "github")
    assert code == 1
    assert "changed after @carol approved" in "\n".join(res["reasons"])


def test_later_unreviewed_commit_is_checked(gh_repo):
    # PR #7 approved the first version; a later commit changed the file with no PR.
    setup_pr(gh_repo, [review("carol")])
    gh_repo.add("exceptions", STEM, {**good_exception(ITEM), "threat": "edited later"})
    new_sha = gh_repo.commit_all("edit after merge")
    gh_repo.fake.add(f"/repos/{REPO_NAME}/commits/{new_sha}/pulls", [])
    code, res = gh_repo.check("--approvals", "github")
    assert code == 1
    assert new_sha[:7] in "\n".join(res["reasons"])


def test_changes_requested_after_approval(gh_repo):
    setup_pr(gh_repo, [review("carol"), review("carol", state="CHANGES_REQUESTED")])
    code, _ = gh_repo.check("--approvals", "github")
    assert code == 1


def test_review_pagination(gh_repo):
    base = f"/repos/{REPO_NAME}"
    gh_repo.fake.add(f"{base}/commits/{gh_repo.sha}/pulls", [pr()])
    next_url = f"https://api.github.com{base}/pulls/7/reviews?per_page=100&page=2"
    gh_repo.fake.add(f"{base}/pulls/7/reviews", [review("mallory", state="COMMENTED")],
                     link=f'<{next_url}>; rel="next", <{next_url}>; rel="last"')
    gh_repo.fake.add(f"{base}/pulls/7/reviews", [review("carol")], query={"page": "2"})
    gh_repo.fake.add(f"{base}/contents/{REL}", {"sha": gh_repo.blob}, query={"ref": "reviewed-commit"})
    code, res = gh_repo.check("--approvals", "github")
    assert code == 0, res["reasons"]
    assert f"{base}/pulls/7/reviews?page=2" in gh_repo.fake.calls


def test_uncommitted_change_blocks(gh_repo):
    setup_pr(gh_repo, [review("carol")])
    (gh_repo.root / REL).write_text((gh_repo.root / REL).read_text() + "notes: local edit\n")
    code, res = gh_repo.check("--approvals", "github")
    assert code == 1
    assert "not committed" in "\n".join(res["reasons"])


def test_api_error_is_invalid(gh_repo, monkeypatch):
    def boom(req, timeout=None):
        raise urllib.error.HTTPError(req.full_url, 500, "err", {}, io.BytesIO(b""))

    monkeypatch.setattr(brace.urllib.request, "urlopen", boom)
    code, _ = gh_repo.check("--approvals", "github")
    assert code == 2


def test_next_link_parsing():
    h = '<https://api.github.com/x?page=2>; rel="next", <https://api.github.com/x?page=5>; rel="last"'
    assert brace._next_link(h) == "https://api.github.com/x?page=2"
    assert brace._next_link("") is None
