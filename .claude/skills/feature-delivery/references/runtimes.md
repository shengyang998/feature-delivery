# Runtime selection

Run `python3 <skill>/scripts/manage.py doctor` for safe version/configured-model diagnostics, and `python3 <skill>/scripts/bridge.py --check` for Pi's required CLI capability checks. `doctor --probe` additionally queries CLI model catalogs without printing credentials or catalog contents. Configuration presence is not authentication or live model proof. Inspect session-exposed tools and available models as well. If requested model is unavailable, report it; choose an explicitly available substitute only within user preferences, record requested/selected/fallback, and preserve independent contexts. Do not silently edit runtime settings or downgrade permissions.

The installer creates `~/.config/feature-delivery/profile.json` once. It is user editable and never overwritten on reinstall. Per-runtime `implementer`, `reviewer`, and `computer_use` values select models; null uses the runtime default. `computer_use` is a coordinator-owned helper when appropriate, not a replacement for either peer. Record a dated local profile when model availability changes. Main model is never selected by this package.

## Codex

Discover native collaboration tool names and current model choices. Spawn implementer and design-review peer in independent contexts; supply shared requirements/artifacts explicitly. Where model override requires `fork_turns="none"`, use it and send the minimum complete task context, not a history clone. Use native direct messaging and persistent peer IDs. Four active slots allow coordinator + pair + one helper, not two full pairs. If native delegation is absent, use an available real CLI peer route or disclose the blocker; do not pretend role switching is delegation.

## OpenCode

Use current native subagent delegation when exposed. Inspect `opencode debug agents` and runtime tool schemas; names differ by version. Installer registers `feature-delivery-implementer` and `feature-delivery-reviewer` user agents from canonical role templates. To apply edited OpenCode profile models, run `python3 <skill>/scripts/manage.py sync-models` (supports `--dry-run`); it refuses manually changed agent files. Null omits the model line and uses OpenCode default. `verify` detects profile/agent drift.

Verified v2.2.2 native tool is `subagent` with `{agent: "feature-delivery-implementer", description: "design proposal", prompt: "..."}`; retain the returned `sessionID`. Follow up using `{agent: "feature-delivery-implementer", sessionID: "ses_...", description: "design reply", prompt: "..."}`. Use the reviewer agent similarly and keep that session from discussion through review. These are tool inputs, not shell commands. Detect the current schema before assuming these names; if changed, report it. If a native tool cannot resume, send the durable record into a new independent context and disclose replacement. Do not assume a text label creates a new context.

`opencode run --help` describes CLI session/model syntax for the installed version; this package does not guess a CLI JSON parser or enable automatic permissions. If native delegation is unavailable, the Pi bridge below is a genuine cross-runtime fallback when Pi is installed and authorized; report that peers execute in Pi and which models they use. Otherwise stop and report missing independence.

When launching any CLI from code, set both process cwd and environment `PWD` to the intended project. OpenCode v2 can otherwise resolve the inherited project despite a changed cwd. Pi bridge sets both.

## Pi

Pi has no built-in subagents by default. This package supplies a narrow subprocess bridge, invoked through Pi's normal bash tool. No copied example extension, npm dependency, or agent server is required. Both peers run independent Pi contexts with stable separate session IDs and cwd. Coordinator relays messages between them. Child prompts explicitly prohibit recursive dispatch. The bridge preserves configured extensions, including permission gates, and normal project instructions. It does not disable safety hooks to prevent recursion; role instructions provide that guard.

```sh
python3 <skill>/scripts/bridge.py --check
python3 <skill>/scripts/bridge.py --task <unique-task-id> --role implementer --cwd <project> < implementer-message.txt
python3 <skill>/scripts/bridge.py --task <same-task-id> --role reviewer --cwd <project> < design-message.txt
```

Repeat the same task/role/cwd to continue that peer, including reviewer findings and implementer responses. Unique task IDs isolate unrelated features. Prompt arrives on stdin, not an interpolated shell command. Output is JSON containing selected model, session identity, resume status and response; errors exit nonzero. `--parent-model provider/id` explicitly passes the coordinator model when inheritance from that session is desired and profile is null. Without it, null means the child's configured runtime default. `--profile` overrides the installed profile location. No automatic fallback is performed by the bridge: unavailable models/errors must be resolved and disclosed by coordinator.

Local session metadata is in `~/.local/state/feature-delivery/peers/` (or `--state-dir`); it is not public package content. Locking rejects overlapping calls to the same peer; interrupted processes release locks. Session metadata rejects cwd/profile model changes mid-task: use a new task ID for a deliberate changed route and disclose replacement. Canceled/failed attempts can resume the same peer. The bridge checks required CLI flags and JSON events, and fails closed when their contract differs. It does not enforce code permissions as a sandbox: delegated peers retain the caller's existing OS/runtime permissions.

## Claude Code

The shared skill and minimal global routing are installed in Claude Code user paths. When Claude Code exposes independent agent tools, use their actual schemas, role model selection, session IDs and message/resume support. Retain the same design-review peer. Do not assume tool names from another product. If unavailable, use an authorized installed bridge and disclose it. Installation verification covers shared files/routing; live Claude Code behavior is not verified by this package's current smoke tests. "CloudCode" in this project's setup means Claude Code.
