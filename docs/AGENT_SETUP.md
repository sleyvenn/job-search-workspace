# Setup performed by the agent

The user gave you this repository to set up and use. Handle installation and startup yourself; do not give the user a terminal checklist when your tools can do the work.

1. Read README.md and AGENTS.md. If you downloaded a ZIP, locate the folder containing run.py. Reuse an existing checkout without overwriting it.
2. Find Python 3.11+ in the environment, including any runtime provided by your agent. The command may be `python`, `python3` or `py -3`. If unavailable, install from an official source when authorized and supported; otherwise explain that specific blocker.
3. Run `python run.py bootstrap`. It creates a private workspace if needed, chooses an available port and starts the app. It preserves existing data and reuses a matching server. Keep the returned URL.
4. Open that URL with your available browser so the user can see the app. Do not start a new instance on every message. `python run.py doctor` reports workspace and PDF capabilities.
5. Read the current profile and preferences. If empty, collect actual experience, location/work arrangement, minimum salary, languages, work authorization and target roles. Use a CV or profile the user has authorized you to read. Group questions and ask only for missing facts.
6. Store confirmed facts in candidate.json with stable IDs. Distinguish each employer's experience from independent work. Save preferences and keep submissions in review mode unless the user authorizes more. Confirm the language for application documents; the app's English interface does not require every CV to be in English.
7. Check your ability to research jobs, use authorized portal sessions and inspect documents. Install `requirements-pdf.txt` in a project-local environment if you need the generator; it needs no API keys. Poppler is optional for image previews, and another viewer can provide visual review.
8. Follow docs/WORKFLOW.md: search, evaluate, register, prepare and show. Complete available work and record concrete blockers. Do not submit applications without authorization.

The user's initial involvement should be limited to facts you do not have and decisions that belong to them. Internal commands are tools for the agent.

If the user only wants to see the product, use `python run.py demo` instead of collecting personal details. When continuing existing work, read its records and notes before acting.
