# Choose the delivery path

Judge the changed behavior and its consequences, not the number or names of files.
Use the independent pair for substantial shared cross-component contracts/core
behavior, meaningful default-output semantics, persisted/interchanged formats,
production decoder interpretation/rendering math, release-sensitive behavior,
or explicit invocation of feature-delivery/an independent pair. Otherwise
the main agent implements directly with relevant tests and one appropriate
actual-path check. That check may be a CLI operation, rendered view, document
validation or another bounded use of the changed behavior; it does not require a
full suite, device, deployment or new peer session by default.

| Change | Path and reason |
| --- | --- |
| A small isolated UI control fix with stable interfaces | Direct; exercise the control and related checks. |
| The same control now changes a shared persistence contract | Paired; the shared format/behavior is consequential. |
| Many documentation, label or test-name corrections | Direct; file count does not change their semantic scope. |
| One-line decoder formula or rendering equation change | Paired; decoded samples/default output can change. |
| An internal diagnostic adds report fields only | Direct; inspect its actual report. |
| That diagnostic also changes production interpretation or shared stored data | Paired; an internal label does not reduce the risk. |
| A diagnostic/report formula correction, with no production or shared-storage change | Direct; add a relevant numerical regression and replay the actual report inputs. |
| Routine authorized build-number or release-note wording correction | Direct; verify the resulting value/text. |
| Signing, artifact selection or distribution behavior | Paired; release integrity is affected. |

These are examples, not a path/keyword classifier. If scope grows into a
substantial change, establish the pair before making that change. Explicit user
instructions and existing authorization still govern the task.

The remaining record, handoff and release procedure applies once paired delivery
is selected.

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

For dirty trees, identify the revision with a digest covering relevant tracked diffs and untracked implementation files, not just HEAD. An approval of HEAD does not cover an uncommitted patch. Preserve unrelated user changes. On resume, read the record, inspect current files/revision, reopen the same peers where possible, and recheck approval only where substantive changed behavior makes it stale. If a peer cannot resume, create a fresh independent context, provide the record and artifacts, and disclose replacement; new reviewer rechecks the current revision.

The coordinator supplies requirements, relevant source, constraints, permission boundaries, role, and record location. Implementer supplies a concrete design proposal to its partner. Partner explicitly agrees or explains changes. Implementer records agreement before editing implementation. Every handoff contains revision, changed behavior, test commands/results, unresolved risks, and request for review. Reviewer inspects actual code rather than trusting the handoff, checks credible regressions, and ties findings/approval to the revision. Preserve the same peer through design/review so decisions remain available.

After approval, a substantive change to core logic, interfaces or behavior needs
re-review of the affected part and relevant verification. Do not restart the
whole workflow or re-review unchanged areas. Typos, documentation and corrections
to stale test expectations that preserve the asserted behavior can receive a
bounded coordinator check without resetting approval. A test edit that weakens
the contract to accept changed behavior is substantive, even if test-only.

Keep coordination bounded. Agree the contract in one concise exchange where
possible, batch non-blocking findings, and reuse compatible evidence. The
coordinator should not shadow the implementer with repeated speculative audits.
During a long check, keep a short checkpoint and wait for its result; do not
re-derive settled behavior or repeatedly restart peers without new information.

Direct peer messaging is preferred. With relay, coordinator passes messages verbatim with author and revision, then returns each response to its sender. Do not convert a missing response into agreement. After two rounds without progress on the same issue, send the disputed options/evidence to the coordinator for a decision. Unresolved material findings block closure.

# Integration and release

Agree target/channel early (for example local source only, TestFlight internal testing, GitHub tag with release notes/assets, GitLab Release, or a named backend environment). Determine expected release form and artifacts before preparing a GitHub/GitLab Release. Inspect the repository's actual deployment commands, account, environment and health checks before backend release. When target is unknown, continue independent authorized work and resolve it before the external action.

Once pair findings close, coordinator runs the integrated user path, verifies acceptance and reports remaining practical limitations. If available, invoke the existing TestFlight/release skill for an agreed iOS delivery; do not recreate credentials or upload tooling. Keep distinctions precise: build, archive, upload, processing, installable release and deployed/healthy service are different evidence. Never claim uploaded means deployed.

Honor existing authorization without repeated confirmation. Ask only for a material decision or authority still absent. A rollback or retry that changes an agreed external target needs appropriate authority. Record actual release identifier, destination and result, or clearly state source-only completion.
