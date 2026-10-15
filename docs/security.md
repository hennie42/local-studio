# Security model

Workers are language models acting with tools. They run sandboxed so that a confused or misled worker can damage
nothing outside its project.

- **Filesystem**: Claude Code's sandbox (bubblewrap) lets a worker write only inside its project folder and read
  nothing in your home directory or in any studio folder (other projects, eval graders, model files), except the
  studio's own scripts. `blockReadsOutsideWorkingDirectories` covers the Read tool.
- **Network**: none, except the model endpoint (llama-swap via a socat bridge for local models; Claude Code's own API
  connection for online models). Web fetch and search are denied.
- **Commands**: `sudo` and `git push` are denied; workers never commit (the director reviews and commits).
- **Engines and GPUs**: only through the broker, which runs a fixed list of actions with validated arguments on paths
  inside a registered project (path escapes and shell metacharacters are rejected).
- **MCP servers**: workers start with `--strict-mcp-config` and an empty server list. Without that, Claude Code
  loads your user-level MCP servers, which run outside the sandbox with whatever access you gave them.
- **OpenCode** (optional harness) runs entirely inside `bin/studio-sandbox` (bubblewrap with only /usr, /etc and the
  project visible, its own network namespace) and with `--standalone`, because its default background service would
  run tools outside the sandbox.

What it does not protect against: a worker writing bad code into its own project (that is what review is for), and
models you download (use sources you trust). The director runs unsandboxed with your normal Claude Code permissions.
