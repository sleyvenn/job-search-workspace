# Operating workflow

Run these commands from the repository root. Some systems use `python3`. For a different private folder, put `--workspace /private/path` before the subcommand.

## 1. Profile and preferences

Run `python run.py bootstrap`, or `python run.py init` if startup is being handled separately. Complete `workspace/candidate.json` and `workspace/preferences.json` with confirmed information. Each fact has an `id`, `text`, `verified` and `scope`, distinguishing employer experience, independent work and education. Store missing information in `unknowns`.

Ask about location, work arrangement, work authorization, languages, salary and target roles when missing. Confirm whether the user wants employment, freelance work or both. Keep permission to submit separate from preferences. Choose the application language based on the user's instructions and the job, not the interface language.

## 2. Search and assessment

Use authorized sources and verify each full posting. Search the last 24 hours when useful and prioritize the last hour where supported. Record the actual publication information, review date, public link and ATS ID if available.

Prepare a JSON file based on `examples/job.demo.json`, with reasons, supported strengths, gaps and next steps:

```sh
python run.py add-job --file workspace/offer.json
```

If the command identifies a duplicate, resume the existing record. Do not change IDs to bypass the check.

## 3. Tailored CV

Select and order real facts. For the included generator, prepare content like `examples/cv.demo.json`. Each claim uses `source_refs` containing profile fact IDs:

```sh
python -m pip install -r requirements-pdf.txt
python run.py create-cv --job ats-123 --file workspace/cv-draft.json --why "Highlight integrations and user-facing work" --language en
```

References provide traceability, but text can cite a valid source and still overstate it. Check that titles, dates, proficiency and scope match the evidence.

For a PDF generated elsewhere:

```sh
python run.py attach-cv --job ats-123 --file /path/cv.pdf --why "Reviewed adaptation for this opportunity" --language en
```

Documents are copied under a new filename in `workspace/documents/`. Inspect **every page**. The app previews page one and offers the complete original for opening or download. Each version retains its hash and earlier versions.

## 4. Review and authorization

The user can review the job, PDF and notes in the app. Prioritizing a job or approving CV content does not itself authorize submission.

Only after a real user instruction:

```sh
python run.py approve --job ats-123 --note "The actual user instruction authorizing this submission"
python run.py check-ready --job ats-123
```

The recorded authorization is linked to the PDF and expires after 24 hours. A new version requires recording a current authorization again. Respect the user's actual conditions and limits: the command cannot certify consent by itself.

## 5. Application form and outcome

Use the official form through the agent's authorized tools. Verify the selected PDF and provide only confirmed facts. Do not infer permission for contracts, expenses or additional access.

If blocked:

```sh
python run.py record-outcome --job ats-123 --status blocked --reason "A required question needs an unconfirmed fact"
```

If the submission outcome is unclear:

```sh
python run.py record-outcome --job ats-123 --status uncertain --reason "No confirmation appeared; check existing applications before retrying"
```

After observing a real confirmation, save a screenshot and record exact details:

```sh
python run.py record-application --job ats-123 --cv ats-123_YYYY-MM-DD_v1.pdf --sha256 ACTUAL_PDF_HASH --receipt workspace/confirmation.png --confirmation "Actual confirmation text observed on the portal" --channel "Employer ATS" --at ISO_TIMESTAMP_WITH_TIMEZONE
```

`--answers workspace/answers.json` adds relevant form answers. Never store passwords, login codes or temporary access URLs. Recording the same submission twice is idempotent; conflicting PDF details are rejected.

This command records an observation. It does not prove that the program submitted an application or that a screenshot's contents are authentic. Never use it to simulate activity. Late confirmations can be recorded, with a note if prior authorization is missing, rather than hiding an observed submission.

## 6. Reporting and continuity

```sh
python run.py validate
python run.py report
```

Report reviewed, prepared, submitted, discarded and blocked jobs with reasons. The app links to the latest report. Generated reports summarize existing records; they do not prove that a search happened that day.

Before another session, read the records and user notes again. For recurring work, use `DAILY_RUN.md` with an authorized period and limit.
