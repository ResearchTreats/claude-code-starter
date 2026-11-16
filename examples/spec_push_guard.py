"""Each line breaks one piece of the push guard on purpose. Run from the repo root:

    python scripts/mutate.py examples/spec_push_guard.py tests/test_push_guard.py -q

Every mutant should be KILLED: a test fails while the piece is broken. A SURVIVED line
means no test would notice if that piece stopped working."""
HOOK = ".claude/hooks/push_guard.py"

MUTANTS = [
    # the account check never fires
    (HOOK, "if who != OWNER:", "if False:"),
    # any repo counts as the owner's
    (HOOK, 'if not re.search(rf"github\\.com[/:]{re.escape(OWNER)}/", url):', "if False:"),
    # an unreadable account lets the push through
    (HOOK, 'return f"cannot read the gh account ({exc}) - not pushing blind"', "return None"),
    # heredoc bodies are read as shell again
    (HOOK, "for line in strip_heredocs(command).replace", "for line in command.replace"),
    # a wrapper (env X=1 git push) hides the push
    (HOOK, 'i = words.index("git") + 1', 'i = 1 if words[0] == "git" else len(words)'),
    # `gh pr create` is no longer looked at
    (HOOK, 'w[1] in ("pr", "repo")', 'w[1] in ("repo",)'),
]
