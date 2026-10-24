# Recurring search instruction

Give this text to the scheduler in the user's chosen agent environment. Installing the repository does not activate any automation.

```text
Work in this repository and read AGENTS.md and docs/WORKFLOW.md.
Check today's date, the authorized period and whether today's run is already recorded.
Read the profile, preferences, application state, notes and reports before acting.

Search for recent jobs in authorized sources. Verify actual dates, location,
work arrangement, hiring eligibility and salary. Deduplicate before preparing
documents. Do not force a quota when opportunities do not fit.

Prepare tailored CVs from confirmed facts, review every page and preserve each
version with its hash. Submit only if the user's current instruction permits
applications within this period and limit. Record that authorization per job
and run check-ready before acting. If only preparation is authorized, leave
the documents for review.

If a session is closed, a fact is unknown or intervention is required, record
the blocker and continue with other jobs. If submission is uncertain, check
whether it already exists before retrying. Never invent confirmation.

Create a report linking each job, the reasoning, the exact CV used and the result.
Record consulted sources and limitations in workspace/runs.json using atomic
writes and preserving prior entries. Distinguish a search with no matches
from a run that could not actually take place.
Stop at the end of the authorized period; do not renew it yourself.
```

The app can run on a server while the agent runs elsewhere. These are separate processes. Work can continue with the user's computer off only when the agent has another running environment with the required tools and sessions. Hosting the table alone does not provide that capability.
