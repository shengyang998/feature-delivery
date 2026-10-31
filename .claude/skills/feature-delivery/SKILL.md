---
name: feature-delivery
description: Deliver an implementation request through a coordinator, independent implementer, and independent design partner who becomes reviewer, including small features. Use for requested feature implementation; not pure discussion or research.
---

Use this workflow for every feature, including tiny changes. Announce its use once. If assigned a delegated implementer/reviewer role, follow that role and return to the coordinator; do not recursively start this workflow.

The main agent stays coordinator: clarify requirements, dispatch work, integrate, run acceptance checks, and manage release. Keep its model unchanged. Create separate agent contexts for implementer and design partner; the same design partner later reviews. Separate contexts can use the same model. Never substitute roleplay in one context for independent review. If independent contexts are unavailable, report that limitation and stop implementation until a real peer route is available.

1. Read [workflow.md](references/workflow.md). Establish acceptance criteria, scope, release target/channel, and a short durable task record before dispatch. Existing authorization persists; an implementation request does not itself authorize publication or deployment.
2. Read only the applicable section of [runtimes.md](references/runtimes.md). Detect actual runtime tools, model availability and capacity. Use the editable installed profile, or [default.json](profiles/default.json). Model IDs belong in profiles, never this file. Report requested versus selected models and any fallback explicitly. A null profile means runtime configured default, not automatic inheritance of the coordinator's current model.
3. Have implementer and design partner discuss concrete interfaces, ownership and tests. The implementer must receive explicit design agreement before editing implementation. Use direct messaging where supported, coordinator relay otherwise. Preserve both peers through design and review iterations.
4. Implementer codes and self-tests every handoff and commit. The design partner becomes reviewer, reviews the actual revision and tests, and returns actionable findings. Iterate until findings close. Escalate disputed design or repeated no-progress to the coordinator; do not silently waive findings.
5. After pair closure, the coordinator integrates and checks the real user path against acceptance criteria. Any code change invalidates approval for affected code; obtain affected re-review and rerun relevant checks. Report evidence and limitations, then release only to the agreed authorized target.

Constrain parallel pairs by available slots. Isolate editing work in worktrees or explicit non-overlapping interface ownership; serialize shared browser, simulator and device use. A coordinator plus one pair fits three contexts. Do not promise concurrent pairs when capacity cannot support them.
