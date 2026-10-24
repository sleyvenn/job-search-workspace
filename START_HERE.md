# Start here

Give your agent the repository link and say:

> Download this repository and use it as the base for my job search. Set up the app and help me complete my profile and preferences.

The agent follows `docs/AGENT_SETUP.md`: download, start and open the app. You provide only the missing facts and decisions.

For a more specific scope, use:

```text
Read AGENTS.md and docs/WORKFLOW.md. I want to use this app to find a job.
First check that you can read and write files, run Python, research current
openings and, when authorized, use official application forms.

Initialize my private workspace without overwriting existing files.
Help me complete my profile with confirmed facts and my preferences for
location, work arrangement, salary, languages, contract type and roles.
Ask only for missing information; do not infer experience from job requirements.

Find an initial selection of recent jobs, explain why they fit or why you
discard them, register them without duplicates and prepare a tailored PDF
for each selected opportunity. Open the table and show me the PDFs.
Do not submit anything without an instruction from me authorizing that step.
If a capability is unavailable, record the blocker and complete independent work.
```

To continue with another agent:

```text
Read AGENTS.md, workspace/candidate.json, workspace/preferences.json,
workspace/state.json, workspace/reviews/decisions.json and workspace/runs.json.
Resume from these records. Do not duplicate submissions or assume authorization.
Check uncertain outcomes before retrying. Preserve all existing PDFs.
```

For recurring searches, agree on the period, schedule, daily limit and whether the agent may submit or only prepare. Use that environment's scheduler and `docs/DAILY_RUN.md`. This app does not keep an agent running or keep work going when its execution environment is switched off.
