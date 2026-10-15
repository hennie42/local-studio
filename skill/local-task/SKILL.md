---
name: local-task
description: Hand a well-scoped, verifiable coding task to the local model by running `claude-local` headless in the background, then review and verify its work. Use when the user says /local-task, or asks to delegate, offload or hand off work to the local model or local LLM. Good for grunt work such as writing tests, bulk mechanical edits, fixing lint/type errors, or log digging. Not for tasks that need this conversation's context or deep judgment.
argument-hint: <task description>
---

# /local-task: delegate to the local model

`claude-local` is Claude Code pointed at the local llama-swap endpoint (the model set in STUDIO_LOCAL_MODEL; `studio-config` shows it). It runs as a separate headless process. It sees **none** of this conversation, only the prompt you write. Setup and details: the studio repo's docs/local-models.md.

## 1. Check the task fits
Delegate only if all of these hold:
- the goal can be stated in a few sentences without this conversation's context;
- success can be checked mechanically: a test, type checker, linter, build or grep;
- the affected files are known, or easy to find.

If not, say so and offer to do it yourself, or to split off a part that does fit.

The local model is capable but weaker than you. Its output is a draft that you verify.

## 2. Pick the workspace
- **In place** (default): fine when you won't touch the same files while it runs.
- **Worktree**: use one when you or the user keep editing the same area, or the change is large.
  `git worktree add ../<repo>-local-<slug> -b local/<slug>` and run the task there. Afterwards, merge or cherry-pick after review and remove the worktree.

Only one local task runs at a time: the server processes one request at a time, so a second task just queues. Check first; any output means a local session or task is active:
`grep -lsz 'ANTHROPIC_AUTH_TOKEN=local' /proc/[0-9]*/environ`
(It matches on environment, not process name. `pgrep 'claude.*-p'` would also match normal Claude sessions.) If one is running, tell the user, then queue or wait.

## 3. Write a self-contained prompt
Write it to a file in your scratchpad directory, e.g. `<scratchpad>/local-task-<slug>.md`. If no scratchpad is available, use a `mktemp -d` directory. Never put it in the repo. Include:
- **Goal**: what to achieve, in concrete terms.
- **Where**: exact files and directories, and relevant conventions (test framework, style, the commands the project uses).
- **Constraints**: what not to touch; no new dependencies; do not commit, push or delete files unless asked.
- **Done when**: the exact verification command(s) the model must run and get passing.
- **Report**: "End with a short summary: files changed, what you did, and the final output of the verification command. If you could not finish, say exactly what is left and why."

Keep it tight. One clear task is better than three loose ones.

## 4. Launch in the background
Grant the narrowest tools that let it do the job and verify. Always include `Read,Glob,Grep`. Add `Edit,Write` if it changes files. Add `Bash(<cmd>:*)` only for the specific verification and build commands, e.g. `Bash(pytest:*)`, `Bash(npm test:*)`, `Bash(cargo check:*)`. Never grant bare `Bash`, `git push`, or `rm` without the user's explicit OK.

Run with the Bash tool and `run_in_background: true`:

```sh
cd <workdir> && timeout <seconds> claude-local -p "$(cat <prompt-file>)" \
  --permission-mode acceptEdits \
  --allowedTools "Read,Glob,Grep,Edit,Write,Bash(<verify-cmd>:*)" \
  --output-format json \
  > <scratchpad>/local-task-<slug>.json 2> <scratchpad>/local-task-<slug>.err
```

- `timeout`: choose by task size. 1800 s is a sensible default; 3600 s for big tasks.
- `claude-local` starts the llama-swap service if needed. A cold start adds about 15 s.

Tell the user what was delegated, where it runs, and that you'll review it when it finishes. Then carry on with other work, or end the turn. The completion notification will wake you.

## 5. Review when it finishes
1. Parse the result:
   `python3 -c 'import json;d=json.load(open("<json>"));print(d["subtype"],d["is_error"],d["num_turns"],d["duration_ms"]//1000,"s");print(d["permission_denials"]);print(d["result"])'`
   - Ignore `total_cost_usd`: it is computed at Anthropic prices, but the run was local and free.
   - Exit code 124 means it hit `timeout`. Check `.err` for startup or connection errors.
2. Read the diff yourself: `git diff` / `git status` in the workdir. Check scope: did it touch only what it should? Did it change tests to make them pass?
3. Run the verification command yourself. Do not trust its report alone.
4. Then act:
   - **Good**: report to the user (what changed, verification output, turns and time).
   - **Close**: either fix the rest yourself, or send a follow-up to the same session:
     `claude-local -p "<specific correction>" --resume <session_id> ...same flags...`
   - **Bad**: tell the user plainly what went wrong. Revert only the local model's changes, and only with the user's OK; in a worktree, just remove it. Then offer to do the task yourself.
   - **Permission denials**: if it was blocked on a tool it needed, relaunch with that tool added, provided it is narrowly scoped.

Never commit the local model's work without the user asking.
