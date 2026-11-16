# Claude Code starter: five rules, three files

The files behind the Research Treats video **"I Let Claude Code Run My YouTube Channel"**.
For four and a half months Claude Code built and ran a system that plans, records, voices,
checks and uploads coding lessons. These are the three files that did the most to keep it
honest, cleaned up so you can drop them into your own project.

| File | What it is | The rule it enforces |
|---|---|---|
| [`CLAUDE.md`](CLAUDE.md) | A template for the file Claude Code reads at the start of every session | 1. If Claude can't see it, write it down. Short. |
| [`scripts/mutate.py`](scripts/mutate.py) | A 50-line mutation check: breaks your code on purpose and confirms a test fails | 2. Give it a check it can't fake. |
| [`.claude/hooks/push_guard.py`](.claude/hooks/push_guard.py) + [`.claude/settings.json`](.claude/settings.json) | A hook that blocks any `git push` that isn't to your account's repos, as your account | 3. If a rule can't bend, don't ask - enforce it. |

The other two rules need no file, only a habit (both are lines in the `CLAUDE.md` template):

4. **Trust the world, not the report.** "Success" in a log is a claim. After an upload or a
   deploy, read the result back from the service itself.
5. **Look and listen before anyone else does.** Automated checks pass things a person would
   catch in a second. Review the real output.

## Use it

Needs Python 3.9+, `git`, and for the hook the [GitHub CLI](https://cli.github.com/) (`gh`).

### 1. CLAUDE.md
Copy [`CLAUDE.md`](CLAUDE.md) to your repo's root and fill in the `<placeholders>`. Keep it
short: the exact test commands at the top, then the traps, then the decisions nobody wrote
down. If your project already has one, steal the section headings.

### 2. The mutation check
Copy `scripts/mutate.py`. Write a spec that names the lines to break:

```python
# spec.py
MUTANTS = [
    ("src/billing.py", "if total > LIMIT:", "if False:"),
]
```

```bash
python scripts/mutate.py spec.py tests/test_billing.py -q
```

```
KILLED   src/billing.py: 'if False:' -> 1 failed, 11 passed in 0.42s
1/1 killed
```

`KILLED` means a test failed while the line was broken: the line is tested. `SURVIVED`
means every test still passed: nothing checks that line, however green the suite is. The
file is put back after every run. Ask Claude to write the spec for every change it makes -
and to run it.

Try it here: `python scripts/mutate.py examples/spec_push_guard.py tests/test_push_guard.py -q`

### 3. The push guard
Copy `.claude/hooks/push_guard.py` and the `hooks` block of `.claude/settings.json` into
your repo, and set `OWNER` at the top of the hook to the one GitHub account the project may
push as. From then on, when Claude Code runs `git push`, `gh pr create` or `gh repo create`:

- signed in as another account: blocked;
- the remote belongs to another owner: blocked;
- the account or the remote can't be read: blocked (it fails closed).

Claude sees the reason and stops. You can still push anything yourself from your own
terminal: the hook only watches Claude's commands.

The `permissions.deny` list in the same `settings.json` is a second, simpler kind of rule:
commands Claude may never run (`git add -A`, `git stash`, reading `.env`).

Check it: `python -m pytest tests/test_push_guard.py -q`

## Why a hook and not a note
A line in `CLAUDE.md` is a suggestion: the model decides whether to follow it. A hook is a
script Claude Code runs before the command, and exit code 2 stops it. Use notes for
preferences and hooks for the rules that must never bend. The price: a guard that reads
shell commands will sometimes be too careful. This one once blocked a command that only
*mentioned* a push inside a string; the tests in `tests/test_push_guard.py` are the cases it
got wrong along the way.

## License
MIT - see [LICENSE](LICENSE). Made for the [Research Treats](https://www.youtube.com/channel/UCxL-CHpsg_8BhYL9yftCz7Q) channel.
