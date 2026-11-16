"""Each line breaks one piece of the push guard on purpose. Run from the repo root:

    python scripts/mutate.py examples/spec_push_guard.py tests/test_push_guard.py -q

Every mutant should be KILLED: a test fails while the piece is broken. A SURVIVED line
means no test would notice if that piece stopped working."""
HOOK = ".claude/hooks/push_guard.py"

MUTANTS = [
    # the account check never fires
    (HOOK, "if who != OWNER:", "if False:"),
    # any repo counts as the owner's
    (HOOK, 'if (owner_of(url) or "").lower() != OWNER.lower():', "if False:"),
    # only the first push address is checked
    (HOOK, "for url in urls:", "for url in urls[:1]:"),
    # a remote with no address is let through
    (HOOK, "if not urls:", "if False:"),
    # any host counts as GitHub
    (HOOK, 'and host == "github.com" and', "and"),
    # an ssh-looking piece inside another address counts
    (HOOK, "m = _SSH.fullmatch(url)", "m = _SSH.search(url)"),
    # the owner's name must match capital for capital
    (HOOK, '(owner_of(url) or "").lower() != OWNER.lower()', '(owner_of(url) or "") != OWNER'),
    # a push that overrides its remote is not noticed
    (HOOK, "if _overrides(command):", "if False:"),
    (HOOK, 'if any(w == "--repo" or w.startswith("--repo=") for w in words[at + 1:]):', "if False:"),
    # an unreadable account lets the push through
    (HOOK, 'return f"cannot read the gh account ({exc}) - not pushing blind"', "return None"),
    # heredoc bodies are read as shell again
    (HOOK, "for line in strip_heredocs(command).replace", "for line in command.replace"),
    # a wrapper (env X=1 git push) hides the push
    (HOOK, 'i = words.index("git") + 1', 'i = 1 if words[0] == "git" else len(words)'),
    # `gh pr create` is no longer looked at
    (HOOK, 'w[1] in ("pr", "repo")', 'w[1] in ("repo",)'),
]
