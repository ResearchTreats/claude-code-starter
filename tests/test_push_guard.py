""".claude/hooks/push_guard.py: Claude pushes only to the owner's repos, signed in as the owner.

Run: python -m pytest tests/test_push_guard.py -q
The tests read OWNER from the hook, so they pass whatever account you set there."""
import json
import runpy
import subprocess
import sys
from pathlib import Path

HOOK = Path(__file__).resolve().parents[1] / ".claude" / "hooks" / "push_guard.py"
G = runpy.run_path(str(HOOK))
OWNER = G["OWNER"]
MINE = f"https://github.com/{OWNER}/some-repo.git"
OTHER = "https://github.com/someone-else/their-repo.git"


def _decide(command, login=OWNER, remotes=None, cwd="C:/repo"):
    remotes = remotes or {}
    seen = []

    def remote(directory, name):
        seen.append((directory, name))
        return remotes[(directory, name)]
    return G["decide"](command, cwd, lambda: login, remote), seen


def test_a_push_to_another_owners_repo_is_blocked():
    reason, _ = _decide("git push origin feat/x", remotes={("C:/repo", "origin"): OTHER})
    assert reason and "someone-else/their-repo" in reason


def test_a_push_to_the_owners_repo_as_the_owner_goes_through():
    reason, seen = _decide("cd sub/project && git push -u origin main",
                           remotes={("sub/project", "origin"): MINE})
    assert reason is None and seen == [("sub/project", "origin")]


def test_an_ssh_remote_of_the_owner_goes_through():
    reason, _ = _decide("git push", remotes={("C:/repo", "origin"): f"git@github.com:{OWNER}/x.git"})
    assert reason is None


def test_git_dash_c_and_a_named_remote_are_read():
    reason, seen = _decide("git -C sub/x push upstream main",
                           remotes={("sub/x", "upstream"): MINE})
    assert reason is None and seen == [("sub/x", "upstream")]


def test_another_account_never_pushes_or_opens_prs():
    reason, _ = _decide("git push", login="another-account", remotes={("C:/repo", "origin"): MINE})
    assert reason and "'another-account'" in reason
    reason, _ = _decide('gh pr create --title "x"', login="another-account")
    assert reason and OWNER in reason


def test_an_unreadable_account_or_remote_blocks():
    def broken():
        raise RuntimeError("network")
    assert "cannot read the gh account" in G["decide"]("git push", ".", broken, lambda d, n: MINE)
    reason, _ = _decide("git push", remotes={})
    assert reason and "cannot read remote" in reason


def test_other_commands_are_not_looked_at():
    def fail():
        raise AssertionError("gh must not be called")
    for cmd in ("git status", "git commit -m 'push the fix'", "python -m pytest -q"):
        assert G["decide"](cmd, ".", fail, lambda d, n: MINE) is None


def test_a_push_mentioned_inside_a_string_is_not_a_push():
    def fail():
        raise AssertionError("gh must not be called")
    for cmd in ('python -c "print(\'a && git push origin main\')"',
                'for c in "git push origin x" "cd y && git push"; do echo "$c"; done'):
        assert G["decide"](cmd, ".", fail, lambda d, n: MINE) is None, cmd


def test_a_heredoc_body_is_data_not_a_push():
    def fail():
        raise AssertionError("gh must not be called")
    cmd = ("cd \"/c/notes\" && cat > n.md <<'EOF'\n- the hook: git push and gh pr create go\n"
           "  only where it's allowed; don't push other repos\nEOF\necho done")
    assert G["decide"](cmd, ".", fail, lambda d, n: MINE) is None


def test_a_push_after_a_heredoc_or_on_its_own_line_is_still_seen():
    cmd = "cat > n.md <<'EOF'\nhello\nEOF\ngit add n.md\ngit push origin main"
    reason, _ = _decide(cmd, remotes={("C:/repo", "origin"): OTHER})
    assert reason and "someone-else/their-repo" in reason


def test_a_wrapped_push_is_still_a_push():
    for cmd in ("env GIT_TRACE=1 git push", "nice -n 5 git push origin main"):
        reason, _ = _decide(cmd, remotes={("C:/repo", "origin"): OTHER})
        assert reason and "someone-else/their-repo" in reason, cmd


def test_a_windows_path_stays_one_word():
    reason, seen = _decide("git -C C:/Users/x/project push origin main",
                           remotes={("C:/Users/x/project", "origin"): MINE})
    assert reason is None and seen == [("C:/Users/x/project", "origin")]


def test_the_last_cd_before_the_push_is_where_it_runs():
    reason, seen = _decide("cd a; cd sub/x && git status && git push",
                           remotes={("sub/x", "origin"): MINE})
    assert reason is None and seen == [("sub/x", "origin")]


def test_the_script_reads_a_tool_call_and_the_settings_wire_it_in(tmp_path):
    subprocess.run(["git", "init", "-q", str(tmp_path)], check=True)
    subprocess.run(["git", "-C", str(tmp_path), "remote", "add", "origin", OTHER], check=True)
    r = subprocess.run([sys.executable, str(HOOK)], capture_output=True, text=True,
                       input=json.dumps({"cwd": str(tmp_path), "tool_name": "Bash",
                                         "tool_input": {"command": "git status"}}))
    assert r.returncode == 0
    settings = json.loads((HOOK.parents[1] / "settings.json").read_text(encoding="utf-8"))
    handlers = [h for g in settings["hooks"]["PreToolUse"] for h in g["hooks"]]
    assert {"Bash(git push *)", "PowerShell(git push *)"} <= {h.get("if") for h in handlers}
    assert all("push_guard.py" in h["command"] for h in handlers)


def test_a_lookalike_address_is_not_the_owners_repo():
    # The first version looked for "github.com/OWNER/" anywhere in the address.
    for url in (f"https://evil.example/github.com/{OWNER}/x.git",
                f"https://github.com.evil.example/{OWNER}/x.git",
                f"https://evil.example/?next=github.com/{OWNER}/x",
                f"git@evil.example:github.com/{OWNER}/x.git",
                f"https://github.com/{OWNER}-other/x.git"):
        reason, _ = _decide("git push", remotes={("C:/repo", "origin"): url})
        assert reason and "is not a" in reason, url


def test_every_push_address_of_the_remote_is_checked():
    reason, _ = _decide("git push", remotes={("C:/repo", "origin"): MINE + "\n" + OTHER})
    assert reason and "someone-else/their-repo" in reason
    reason, _ = _decide("git push", remotes={("C:/repo", "origin"): ""})
    assert reason and "no push address" in reason


def test_the_owners_name_is_matched_whatever_its_capitals():
    url = f"https://github.com/{OWNER.upper()}/x.git"
    assert _decide("git push", remotes={("C:/repo", "origin"): url})[0] is None
    assert _decide("git push", remotes={("C:/repo", "origin"): f"ssh://git@github.com/{OWNER}/x"})[0] is None


def test_a_push_that_overrides_the_remote_is_blocked():
    for cmd in (f"git -c remote.origin.pushurl={OTHER} push origin main",
                f"git -c url.{OTHER}.insteadOf={MINE} push",
                f"git push --repo={OTHER}",
                f"git push --repo {OTHER} main"):
        reason, _ = _decide(cmd, remotes={("C:/repo", "origin"): MINE})
        assert reason and "overrides" in reason, cmd
