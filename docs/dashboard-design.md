# Progress dashboard: design

**Status: designed, not built.** Decided in a `/grilling` interview. Build after the Don't
Panic Island playtest, and only on the user's go-ahead.

**Goal:** the user can always see what the studio is doing and what is left, from this machine or a phone on the
home network, without asking the director. Today that takes reading logs, `studio-dispatch status` and HANDOFF.md.

## Decisions

| topic | decision |
|---|---|
| Purpose | Watch everything. The only control is **Pause / Resume**, on jobs that support it. Retrying or marking tickets, starting runs and stopping units stay with the director and the CLI. |
| Stack | `bin/studio-status`: a Python stdlib HTTP server and one HTML/CSS/JS file (vanilla, no build step, no CDN), like the asset review page. The page polls `/api/status` every 5 s; the JSON is the contract, so a Svelte page could replace it later. |
| Running | Always on: a systemd user service like the broker. It only reads files. `studio-status --once` prints the same summary as text (terminal, the director's monitors, the status line). |
| Access | Home network (LAN), plain HTTP, port **8766**, listening on all interfaces. |
| Protection | A random token in `~/.config/studio/dashboard-token`. `studio-status url` prints the link with the token; the first visit sets a cookie; requests without it get 403. A ufw rule limits the port to the home subnet (the user runs it, it needs sudo): `sudo ufw allow from 10.0.0.0/24 to any port 8766 proto tcp`. TLS is not worth a self-signed certificate for a status page on a WPA2/3 network. |
| Layout | Phone first, one column: now strip with Pause, ETA, Local share, ticket board (compact list), feed, studio queue. Desktop: the same panels in a grid. |
| Scope | Every long job in the studio, not only dispatcher projects: dispatcher runs, comparison clips, eval suites, gen3d runs, the weekly syncs. Dispatcher projects also get the ticket board. |
| Job launcher | New `studio-job <name> [--mem 40G] -- <command>`: runs the unit `studio-job-<name>` with a memory cap (the oomd lesson becomes the default), logs to `/home/user/StudioProjects/evals/jobs/<name>.log`, records start, command and project. The dashboard lists these units (state, runtime, last log line). The director launches every long job through it. |
| What's left | New `queue.json` in the repo (item, status, estimate, depends-on, needs-user), kept current by the director. HANDOFF.md points to it instead of repeating the list. The dashboard shows it with the estimates added up. |
| ETA | Remaining tickets x the project's median minutes per ticket so far, plus a worst case (each failing ticket: up to 3 attempts at its timeout). Shown as "done ~21:40 (worst case 01:10)"; amber when the worst case passes 23:00, the user's usual shutdown. |
| Pause | A button per job that supports it: dispatcher projects (`<project>/.studio/PAUSE`, stops between tickets) and eval/clip runs (`$STUDIO_EVAL_HOME/runs/PAUSE`). No button for jobs without a pause mechanism. Resume removes the file; a paused dispatcher is not restarted automatically, the page shows the command. |
| Alerts | Desktop notifications (`notify-send`) and a badge in the page's title (`⚠ DPI: T11 escalated`) for escalations, finished runs and stalls. No phone push: web notifications need HTTPS, and ntfy.sh would send events off the machine. A self-hosted ntfy only if the user misses things. |
| Stalls | A red **stalled** badge and a notification when an attempt runs 5 min past its timeout, a unit fails, or a running job's log is silent for 30 min. |
| History | No database. Everything is read from existing files (ledgers, dispatch state, transcripts, job logs), so nothing can drift. Finished projects appear in **Recent runs** (from the ledgers) and in the all-time range. |
| Extras | The newest render or screenshot per project as a thumbnail (behind the token). A Claude Code status line from `studio-status --once`, e.g. `DPI 9/14 · T11 a1 gemma 12m · ETA 21:40`. |

## Local share panel

Replaces the "local score" idea: how much of the work the local models did.

| topic | decision |
|---|---|
| Chart | A donut, hand-drawn inline SVG (one arc path per slice, angles interpolated for the animation), with the local percentage in the centre ("78% local"). |
| Measure | **Output tokens** per model. Cache reads would make it ~99% Claude (one director session: ~105M cache-read vs 257k output tokens); wall-clock time flatters slow local models. Failed attempts count: usage is usage. |
| Steps line | Below the donut: "12 of 14 steps done locally: 9 first try, 3 after retry, 2 escalated". Credit goes to whoever made the check pass; director-owned steps (e.g. C1) and escalated tickets the director fixed count as online. The attempt patches show how close the local model got. |
| Slices | One per model; under 1% merged into "other local" / "other online". |
| Local vs online | Local = served by llama-swap (its config is read at startup, so new local models are picked up). Online = `claude-*`. Anything else: grey "unclassified", so it is visible rather than misfiled. |
| Colours | Local: blue-green family; online: orange-red family, clearly darker than the local shades (red/green alone fails for colour-blind viewers). Shades are fixed per model by its position in its group, so colours don't shift between days. Every slice has a direct label (name, %); a legend list beside the donut (colour, name, %, output tokens, sorted by size); hover shows tokens, attempts and minutes. Nothing depends on hue alone. |
| Sources | Local workers: `.studio/workers/<id>-<n>/agent.jsonl` (tokens and duration per model; their `costUSD` is not meaningful). Claude: the session transcripts in `~/.claude/projects/` (tokens per message and model). |
| Attribution | Claude's working directory is not reliable (director sessions often run elsewhere), so only Claude **messages whose tool calls touch the project's path** count toward that project. |
| Range | A selector: active project (default), today, all time across projects. |
| Updates | Live: transcripts grow during an attempt, so the worker's slice grows. Read incrementally: byte offsets and running totals per transcript in `~/.cache/studio-status/usage.json`; only new lines are parsed each poll, a full rescan only when a file shrinks or is replaced. |

## Data sources

| what | source |
|---|---|
| Tickets, deps, status, attempts | `<project>/tickets.json`, `.studio/dispatch.json` |
| Events (feed) | `.studio/dispatch.log`, job logs |
| Who did what | `.studio/ledger.jsonl` |
| GPU jobs | broker spool (`.studio/spool/req`, `res`), `.studio/logs/` |
| Loaded model | llama-swap `127.0.0.1:8080/running` |
| GPU memory and load | `nvidia-smi` |
| Projects | the broker registry `~/.local/state/studio/projects` |
| Jobs | `studio-job-*` user units |
| Queue | `queue.json` |

## Build plan (~3-4 h)

1. **Collector** (director): `status.py` builds the `/api/status` JSON from the sources above, incl. usage parsing,
   attribution and ETA; `studio-status --once`; a JSON fixture for the page.
2. **`studio-job`** (director) and `queue.json` (seeded from HANDOFF.md).
3. **Page** (local worker, `/local-task`): all panels incl. the donut, against the fixture. Check: renders without
   JS errors, slices sum to 100%, colours follow the group rules. Director reviews a screenshot (phone and desktop
   width).
4. **Service, token, status line, notifications** (director); the user adds the ufw rule.
