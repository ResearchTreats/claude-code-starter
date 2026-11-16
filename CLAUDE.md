# <Project name>

<One or two lines: what this project does and who it is for.>

<!--
How to use this file
- Claude Code reads it at the start of every session. Keep it under about 60 lines:
  every line is read every time, and a long file gets skimmed.
- Write only what Claude cannot work out from the code: commands, traps, decisions.
- When Claude makes a mistake twice, the fix is a line here. When a line stops being
  true, delete it.
- Delete these comments and every <placeholder> before you use it.
-->

## Verify your work
<!-- The exact commands, fastest first. The fast test command goes at the top:
     without it Claude will happily run the slow one, again and again. -->
- One test file: `<python -m pytest tests/test_x.py -q>`
- Full suite: `<python -m pytest tests/ -n auto -q>` - about <10> min (serial is about
  <31> min). Run it in the background.
- Known flaky test: `<tests/test_y.py::test_z>` can fail under load; rerun it alone
  before believing it.
- Commit only after a green full suite, staging explicit paths (never `git add -A`).
- New tests get a mutation check: `python scripts/mutate.py spec.py tests/test_x.py -q`.
  A surviving mutant is untested code.
- Done means checked in the real world, not reported: after a deploy or an upload, read
  the result back from the service itself before calling it done.

## Gotchas
<!-- Traps of THIS machine and THIS project that cost you time once. One line each. -->
- <The shell mangles backslashes in inline scripts: write a script file and run it.>
- <The API drops connections here: every call retries three times.>
- <`data/` is gitignored: outputs, logs and state live there.>

## Decisions not in the code
<!-- Things a new teammate would have to be told. The ones that can never bend also get
     a hook (see .claude/hooks/push_guard.py): a line here is a request, a hook is a rule. -->
- Pushes go only to `<your-github-account>` repos, signed in as that account
  (`.claude/hooks/push_guard.py` blocks everything else).
- <Deploys, uploads and anything public need my yes for that action.>
- <Never re-run `<command>` on <thing>: it replaces <what>.>

## Where things are
- `<docs/RUNBOOK.md>` - the routine, and one row per mistake that cost time, with its fix
- `<docs/DECISIONS.md>` - why the big choices were made
- `<src/...>` - <what lives where, only if the names don't say it>
