# Progress dashboard (`studio-status`)

What the studio is doing and what is left, from this machine or a phone on the home network. Design and the
decisions behind it: [dashboard-design.md](dashboard-design.md).

```sh
studio-status url        # the link with the token; open it once per browser (sets a cookie)
studio-status --once     # the same summary as text
studio-status --line     # one line, for the Claude Code status line
studio-job <name> [--mem 40G] [--project DIR] -- <command...>   # launch a long job so the dashboard sees it
```

- **Service:** `systemctl --user enable --now studio-status` (unit in `systemd/`). It only reads files, except
  Pause / Resume (a `PAUSE` file) and its usage cache (`~/.cache/studio-status/usage.json`).
- **Access:** plain HTTP on port **8767**, all interfaces (8766 is `studio-serve`'s default). Requests without the
  token cookie get 403. The token is in `~/.config/studio/dashboard-token`; delete it and restart the service to
  revoke every browser. Limit the port to the home subnet:
  `sudo ufw allow from 10.0.0.0/24 to any port 8767 proto tcp`.
- **Alerts:** escalations, finished dispatcher runs, finished or failed jobs and stalls go to `notify-send` and the
  page's title (`⚠ …`). Stalled = an attempt 5 min past its timeout, a worker transcript silent for 15 min with no
  GPU job pending, a job log silent for 30 min, or a failed job.
- **What's left:** `queue.json` in the repo (private: not exported), kept current by the director.
- **Jobs:** `studio-job` runs the command as the user unit `studio-job-<name>` with `MemoryMax` (default 40G),
  in the current directory; output in `$STUDIO_EVAL_HOME/jobs/<name>.log`, exit code in `<name>.exit` (137 = killed,
  usually out of memory). `studio-job list`, `studio-job stop <name>`.

## Where the numbers come from

| panel | source |
|---|---|
| Projects | the broker registry `~/.local/state/studio/projects` |
| Tickets, ETA | `<project>/tickets.json`, `.studio/dispatch.json`, `.studio/dispatch.log` |
| Steps (who made each pass) | `.studio/ledger.jsonl` |
| Running attempts | `studio-worker` / `studio-dispatch` processes (`/proc`), `.studio/workers/<step>-<n>/` |
| GPU jobs | broker spool `.studio/spool/req` (pending) and `res` (done) |
| Jobs | `$STUDIO_EVAL_HOME/jobs/*.json` + `studio-job-*` units |
| Machine | `nvidia-smi`, llama-swap `/running`, `systemctl --user` |
| Local share | output tokens per message in `~/.claude/projects/**/*.jsonl` (workers' sessions are there too) |

**ETA** (dispatcher projects): remaining local tickets x the median minutes of the passed tickets so far, minus the
running ticket's elapsed time; worst case = every remaining ticket uses all its attempts at its timeout. Amber
when the worst case passes 23:00.

**Steps line:** a step passed locally when a verdict or the dispatcher's check passed a local attempt (first try =
attempt 1); escalated = the director passed it after local attempts; director-owned = no local attempt.

**Local share:** output tokens per model. A local model's message counts for the project it runs in (its `cwd`);
a Claude message counts for the projects its tool calls touch (by path, split evenly when it touches several).
Local = a model llama-swap serves (or a configured local model); online = `claude-*`; anything else is grey
"unclassified". Slices under 1% merge into "other local" / "other online".

## `/api/status` (the page's contract)

`GET /api/status` returns one JSON object; `tests/dashboard/fixture.json` is a full example of a busy evening.
Times are local ISO strings (`2026-10-23T20:41:05`), durations in seconds (`_s`) or minutes (`_min`, `minutes`).

| key | content |
|---|---|
| `time` | when it was collected |
| `active_project` | name of the project shown first (running work, else the latest activity) |
| `projects[]` | one per registered project, active first: `name`, `path`, `engine` (`godot`/`unreal`), `active`, `paused`, `can_pause` (dispatcher projects), `resume_cmd`, `last_activity`, `image` (`{path, time}` or null: fetch `/api/image?project=<name>`), `steps[]` (`id`, `status` open/failing/pass, `by` local/escalated/director, `attempts`, `model`, `first_try`, `note`), `steps_line` (`done`, `local`, `first_try`, `after_retry`, `escalated`, `director`, `text`), `workers[]` (running attempts: `step`, `attempt`, `model`, `elapsed_s`, `timeout_s`, `silent_s`), `gpu_pending[]` (`action`, `args`, `since`), `gpu_recent[]`, `dispatcher` (a dispatcher is running), `board` (null, or tickets: `id`, `title`, `status` pending/running/pass/escalated, `owner`, `deps`, `attempts[]` (`n`, `kind`, `model`, `check`, `minutes`), `max_attempts`, `timeout`, `minutes`, `commit`), `counts` (status -> n), `eta` (null, or `remaining`, `median_min`, `likely_min`, `worst_min`, `done`, `worst`, `amber`, `running`) |
| `jobs[]` | running first, then the 10 latest: `name`, `state` (running / done / failed (...)), `command`, `project`, `start`, `end`, `runtime_s`, `silent_s`, `last_line`, `stalled`, `mem`, `log` |
| `eval_pause` | `{paused, path}`: the eval/clip runs' PAUSE file |
| `machine` | `gpus[]` (`index`, `name`, `mem_used_mb`, `mem_total_mb`, `util`), `llm` (loaded models, or null if llama-swap is down), `services` (unit -> active state) |
| `queue` | `items[]` (`id`, `item`, `status` next/waiting/blocked/done/dropped, `estimate_h`, `depends_on`, `needs_user`, `ref`), `open`, `estimate_h`, `needs_user` |
| `share` | `project` (active project, plus `name` and `steps_line`), `today`, `all`: each `{total_tokens, local_pct, slices[]}`, a slice = `model`, `group` (local/online/unclassified), `tokens`, `messages`, `attempts` (sessions), `minutes`, `pct`, `shade` (0-5: fixed per model within its group; 9 = merged or unclassified), `other` (merged slice) |
| `stalls[]` | `project`, `what`, `why` |
| `alerts[]` | `key` (stable id), `level` (red/info), `title`, `detail`, `time` |
| `feed[]` | newest first: `time`, `project`, `kind` (pass/fail/escalated/director/gpu/info), `text` |

`POST /api/pause` and `POST /api/resume` with `{"target": "<project name>" | "evals"}` create or remove the PAUSE
file (only for `can_pause` projects and `evals`). A paused dispatcher stops between tickets and is not restarted
automatically: the page shows `resume_cmd`.
