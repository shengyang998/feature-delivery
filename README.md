# Feature Delivery

A shared Agent Skill for implementing every feature with a coordinator, independent implementer, and design partner who becomes reviewer. They agree on design before code, iterate revision-bound review, then the coordinator checks the integrated user path and releases to the agreed target.

The maintained skill is `.claude/skills/feature-delivery/`. User installations link to that single copy; keep this checkout at a stable path. Public default profiles inherit runtime defaults. Local model preferences stay in the user profile, outside the repository. No Python dependencies are required; use Python 3.10+ on macOS/Linux with `uv` for dependency management if adding any.

## Install

```sh
git clone https://github.com/shengyang998/feature-delivery.git
cd feature-delivery
python3 .claude/skills/feature-delivery/scripts/manage.py plan
python3 .claude/skills/feature-delivery/scripts/manage.py install
python3 .claude/skills/feature-delivery/scripts/manage.py verify
python3 .claude/skills/feature-delivery/scripts/manage.py doctor
```

Choose a subset with `--runtimes codex,opencode,pi,claude`; use the same selection for repeat installation. `install --dry-run` is equivalent to `plan`. Review any collision; existing skills, agents and unowned marker blocks are never overwritten. Preflight completes before writes, and write failures roll back completed installation writes. Existing instruction bytes outside the managed block and existing file modes are preserved. Symlinked destination parents are rejected. Global instructions get one small feature routing block with a delegated-role recursion guard. Discovery takes effect in a new session or after the runtime's resource reload.

Edit `~/.config/feature-delivery/profile.json` to choose per-runtime `implementer`, `reviewer`, and optional `computer_use` models. Null means that runtime's configured default; it does not claim to inherit the coordinator's current session override. The coordinator's model is unchanged. For OpenCode apply edits with `manage.py sync-models` (first use `--dry-run` to preview); generated agent wrappers include the selected model. Reinstall preserves the profile. Pi bridge reads it each invocation and rejects changing an existing peer's route mid-task. Invalid/unavailable model selections are reported rather than silently downgraded.

```sh
python3 .claude/skills/feature-delivery/scripts/manage.py uninstall --dry-run
python3 .claude/skills/feature-delivery/scripts/manage.py uninstall
```

Uninstall removes owned links, exact routing additions and unedited generated agents. It refuses to alter edited managed routing/agent files or changed links, leaving the whole install intact for review. It preserves an edited user profile and any existing profile. It preserves unrelated edits to global instruction files, restores original missing/no-final-newline state, and retains peer sessions for resumption. Empty directories may remain. Installer manifest is `~/.local/state/feature-delivery/install.json`; peer sessions live beside it in `peers/`. Neither belongs in this public repository. Moving the checkout requires uninstall from the old source before reinstall from the new source.

## Support and smoke checks

| Runtime | Installation | Independent peer route | Verification boundary |
| --- | --- | --- | --- |
| Codex | `~/.codex/skills`, global AGENTS routing | Native collaboration and persistent peer IDs; model override with independent context | Requires session-exposed collaboration tools |
| OpenCode | `~/.config/opencode/skills`, global routing, two named user agents | Native `subagent`, retain/resume `sessionID` | Current v2 CLI/agent schema; detect actual tools |
| Pi | `~/.pi/agent/skills`, global routing | Included persistent subprocess bridge via bash | Installed CLI must expose required session/JSON flags; tested contract on 1.4.0 |
| Claude Code | `~/.claude/skills`, global CLAUDE routing | Detect native agents or explicitly use an available bridge | Shared install only; live Claude runtime currently unverified |

No runtime-native tool means a reported limitation, never simulated independent review in one context. Pi bridge is a narrow real adapter and needs an installed/authenticated Pi CLI; the package does not install models, weaken permissions, or claim to sandbox peers. Shared browsers/simulators/devices must be serialized.

Offline tests never call real models, devices, brokers, deployment systems or message services:

```sh
uv run --no-project python -m unittest discover -s tests -v
```

To smoke Pi without editing a live project, make a temporary empty directory and message files. Replace `<skill>` with the absolute installed skill path, `<temporary-project>` with that directory, and choose a unique task ID. These calls invoke the configured model and may incur usage:

```sh
python3 <skill>/scripts/bridge.py --check
python3 <skill>/scripts/bridge.py --task smoke-unique --role reviewer --cwd <temporary-project> < remember-message.txt
python3 <skill>/scripts/bridge.py --task smoke-unique --role reviewer --cwd <temporary-project> < recall-message.txt
python3 <skill>/scripts/bridge.py --task smoke-unique --role implementer --cwd <temporary-project> < independent-message.txt
```

Ask the reviewer to remember a random marker without tools, then recall it without restating it. Confirm the same returned session and `resumed: true`. Ask implementer to state whether it saw that marker; confirm a distinct session. These prove session persistence/isolation, not feature correctness. For OpenCode, inspect `opencode debug agents`, start the installed reviewer using the native `subagent` tool, retain its `sessionID`, then resume with a marker recall. Start the implementer separately and check isolation. Exact v2 inputs and other runtime steps are in the skill's [runtime reference](.claude/skills/feature-delivery/references/runtimes.md).

For an end-to-end feature smoke, request a tiny feature in an isolated fixture repository. Observe separate pair contexts, explicit pre-code design agreement, implementer test evidence, same-peer review tied to the final revision, and coordinator acceptance. Introduce an affected code change after approval and verify approval is renewed. Agree release form early; uploading an artifact is not proof of deployment.
