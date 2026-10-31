# Task record and handoffs

Keep a short record in the project's established task location, otherwise an ignored `.feature-delivery/<task>.md`. Do not commit session transcripts, credentials, or user configuration. Record enough to resume after compaction or restart:

```markdown
# <task>
State: requirements | design | implement | review | acceptance | release | done
Acceptance: <observable user behavior and relevant checks>
Scope / exclusions: ...
Release target/channel and authorization: ...
Runtime, requested/selected models, fallback: ...
Coordinator / implementer / design-review peer IDs: ...
Peer session locations / cwd (local only): ...
Agreed design, ownership and explicit agreement: ...
Current revision: <commit plus dirty diff digest if needed>
Self-test evidence for this revision: ...
Findings: <ID, severity, evidence, owner, resolution>
Review approval: <peer, exact revision, conditions>
Integrated acceptance evidence: ...
Next step / unresolved decisions: ...
```

For dirty trees, identify the revision with a digest covering relevant tracked diffs and untracked implementation files, not just HEAD. An approval of HEAD does not cover an uncommitted patch. Preserve unrelated user changes. On resume, read the record, inspect current files/revision, reopen the same peers where possible, and invalidate stale approval. If a peer cannot resume, create a fresh independent context, provide the record and artifacts, and disclose replacement; new reviewer rechecks the current revision.

The coordinator supplies requirements, relevant source, constraints, permission boundaries, role, and record location. Implementer supplies a concrete design proposal to its partner. Partner explicitly agrees or explains changes. Implementer records agreement before editing implementation. Every handoff contains revision, changed behavior, test commands/results, unresolved risks, and request for review. Reviewer inspects actual code rather than trusting the handoff, checks credible regressions, and ties findings/approval to the revision. Preserve the same peer through design/review so decisions remain available.

Direct peer messaging is preferred. With relay, coordinator passes messages verbatim with author and revision, then returns each response to its sender. Do not convert a missing response into agreement. After two rounds without progress on the same issue, send the disputed options/evidence to the coordinator for a decision. Unresolved material findings block closure.

# Integration and release

Agree target/channel early (for example local source only, TestFlight internal testing, GitHub tag with release notes/assets, GitLab Release, or a named backend environment). Determine expected release form and artifacts before preparing a GitHub/GitLab Release. Inspect the repository's actual deployment commands, account, environment and health checks before backend release. When target is unknown, continue independent authorized work and resolve it before the external action.

Once pair findings close, coordinator runs the integrated user path, verifies acceptance and reports remaining practical limitations. If available, invoke the existing TestFlight/release skill for an agreed iOS delivery; do not recreate credentials or upload tooling. Keep distinctions precise: build, archive, upload, processing, installable release and deployed/healthy service are different evidence. Never claim uploaded means deployed.

Honor existing authorization without repeated confirmation. Ask only for a material decision or authority still absent. A rollback or retry that changes an agreed external target needs appropriate authority. Record actual release identifier, destination and result, or clearly state source-only completion.
