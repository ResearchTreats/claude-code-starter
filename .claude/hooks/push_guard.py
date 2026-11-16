"""PreToolUse hook: Claude Code pushes only to repos owned by OWNER, signed in as OWNER.

Why a hook and not a line in CLAUDE.md: a note is a suggestion, and the model decides
whether to follow it. A hook is a script Claude Code runs before the command, so a rule
that can never bend is enforced, not asked for.

Set OWNER below to the one GitHub account this project may push as. Everything else is
blocked: a push to any other owner's repo, a push while `gh` is signed in as another
account, and `gh pr create` / `gh repo create` as another account.

Reads the tool call as JSON on stdin; exits 2 with the reason on stderr to block, 0 to
let the command through. Fails closed: if the account or the remote cannot be read, the
push is blocked. Needs `git` and the GitHub CLI (`gh`) on PATH."""
import json
import re
import shlex
import subprocess
import sys
from typing import Callable, List, Optional, Tuple

OWNER = "your-github-account"   # <- change this


_OPS = {"&&", "||", ";", "|", "&", ";;", "|&"}


_HEREDOC = re.compile(r"<<-?\s*(['\"]?)([A-Za-z_][A-Za-z0-9_]*)\1")


def strip_heredocs(command: str) -> str:
    """The command without its heredoc bodies - they are data, not shell. (A note written
    through a heredoc said "git push and gh pr ..."; its apostrophes broke the tokenizer
    and the prose was read as a push.)"""
    lines, out, i = command.split("\n"), [], 0
    while i < len(lines):
        out.append(lines[i])
        terms = [m.group(2) for m in _HEREDOC.finditer(lines[i])]
        i += 1
        for term in terms:
            while i < len(lines) and lines[i].strip() != term:
                i += 1
            i += 1
    return "\n".join(out)


def segments(command: str) -> List[List[str]]:
    """The command's simple commands as word lists: heredoc bodies dropped, one line at
    a time, split at shell operators AFTER quotes are read - a quoted "a && git push"
    stays one word."""
    out: List[List[str]] = []
    for line in strip_heredocs(command).replace("\\\n", " ").split("\n"):
        lex = shlex.shlex(line, posix=True, punctuation_chars=True)
        lex.whitespace_split = True
        try:
            tokens = list(lex)
        except ValueError:
            tokens = line.split()
        cur: List[str] = []
        for t in tokens:
            if t in _OPS:
                out.append(cur)
                cur = []
            else:
                cur.append(t)
        out.append(cur)
    return [w for w in out if w]


def _push_at(words: List[str]) -> Optional[int]:
    """Index of `push` when these words are `[wrapper ...] git [global options] push ...`
    - a wrapper (env X=1, nice, time, command) does not hide a push."""
    if "git" not in words:
        return None
    i = words.index("git") + 1
    while i < len(words) and words[i].startswith("-"):
        i += 2 if words[i] in ("-C", "-c") else 1
    return i if i < len(words) and words[i] == "push" else None


def push_target(command: str, cwd: str) -> Optional[Tuple[str, str]]:
    """(directory, remote) of the command's `git push`, or None when it pushes nothing.
    The directory is `git -C DIR`, else the last `cd DIR` before it, else cwd."""
    directory = cwd
    for words in segments(command):
        if words[0] == "cd" and len(words) > 1:
            directory = words[1]
        at = _push_at(words)
        if at is None:
            continue
        if "-C" in words[:at]:
            directory = words[words.index("-C") + 1]
        rest = [w for w in words[at + 1:] if not w.startswith("-")]
        return directory, (rest[0] if rest else "origin")
    return None


def _gh_create(command: str) -> bool:
    return any(len(w) >= 3 and w[0] == "gh" and w[1] in ("pr", "repo") and w[2] == "create"
               for w in segments(command))


def decide(command: str, cwd: str, login: Callable[[], str],
           remote_url: Callable[[str, str], str]) -> Optional[str]:
    """The reason to block this command, or None to let it through."""
    target = push_target(command, cwd)
    if target is None and not _gh_create(command):
        return None
    try:
        who = login().strip()
    except Exception as exc:
        return f"cannot read the gh account ({exc}) - not pushing blind"
    if who != OWNER:
        return (f"gh is signed in as {who!r}, not {OWNER}: this project pushes only as "
                f"{OWNER} (switch with `gh auth switch`, or push it yourself)")
    if target is not None:
        directory, name = target
        try:
            url = remote_url(directory, name).strip()
        except Exception as exc:
            return f"cannot read remote {name!r} ({exc}) - not pushing blind"
        if not re.search(rf"github\.com[/:]{re.escape(OWNER)}/", url):
            return f"{url} is not a {OWNER} repo - Claude does not push it"
    return None


def _login() -> str:
    return subprocess.run(["gh", "api", "user", "--jq", ".login"], capture_output=True,
                          text=True, timeout=30, check=True).stdout


def _remote(directory: str, name: str) -> str:
    return subprocess.run(["git", "-C", directory, "remote", "get-url", name],
                          capture_output=True, text=True, timeout=15, check=True).stdout


def main() -> int:
    data = json.loads(sys.stdin.read() or "{}")
    command = str((data.get("tool_input") or {}).get("command") or "")
    reason = decide(command, str(data.get("cwd") or "."), _login, _remote)
    if reason:
        print(f"Blocked by .claude/hooks/push_guard.py: {reason}", file=sys.stderr)
        return 2
    return 0


if __name__ == "__main__":
    sys.exit(main())
