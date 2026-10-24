# Per-user data

`workspace/` is private. Use `--workspace /another/path` to choose another folder. Distributed examples are not the user's profile.

| File or folder | Contents |
| --- | --- |
| candidate.json | Identity, contact details, languages, confirmed facts, unknowns and private names to omit |
| preferences.json | Location, work arrangement, salary, role families, sources and submission scope |
| state.json | Opportunities, assessment summary, CV versions, authorization and observed outcomes |
| analysis.json | Additional assessment by job ID: recommendation, gaps and tailoring plan |
| cv-versions.json | Index of registered documents |
| cv-content/ | Generated CV content and references to profile facts |
| documents/ | PDFs with a new filename per version and SHA-256 hashes |
| receipts/ | Screenshots of real confirmations; these may contain personal details |
| reviews/decisions.json | App notes and decisions, incremental revision and history |
| runs.json, reports/ | Runs and reports; a CLI report does not establish that a new search happened |
| trial.json | Conditions of an authorized recurring trial, when applicable |
| runtime/ | Local server PID, URL and logs |

## Profile

Each `facts` entry has a stable `id`, `text`, `verified` and `scope`. Scope identifies a specific employer, independent work or education. Only facts with `verified: true` can be sources for the CV generator. Interest in a technology and willingness to learn are not professional experience.

`source_refs` in `examples/cv.demo.json` references these IDs. Validation checks that they exist and are confirmed; the accuracy of the wording still requires review.

## Opportunities and documents

Start with `examples/job.demo.json` and use `add-job`. The ID, public URL, company, title, location, work arrangement, reasoning and verification date are required. `external_ids` helps deduplicate a vacancy across LinkedIn and its ATS. A review date is not a publication date.

An unpublished salary uses `minimum: null` and `maximum: null`. Employment ranges are expressed in gross annual euros. If a posting uses another currency or period, preserve the source and verify conversion before comparison. Do not reuse these fields for freelance rates.

`cv_prepared` is the proposed version; `cv_history` preserves earlier ones. A submitted application separately records `cv_sent` and `cv_sha256`, timestamp, channel, answers and confirmation receipt. Preparing another CV does not change the submitted one.

## States

| State | Meaning |
| --- | --- |
| pending | Under assessment or preparation; PDF availability is shown separately |
| reserved | Deferred for an explicit reason |
| discarded | A decision not to proceed, with a reason |
| blocked | A required fact, session or intervention is missing |
| uncertain | The form outcome could not be confirmed; check before retrying |
| sent | An observed confirmation is recorded with the PDF and screenshot |

User decisions and CV review status are separate from submission outcomes. Selecting “Prioritize” or approving CV content neither sends a form nor grants submission authorization by itself.

The initial release used Spanish state values. Those legacy values remain accepted when reading existing records and are normalized to English. Free-text notes, existing CVs, filenames, hashes and receipts are preserved; user data is not automatically translated.

Use the commands to modify opportunities and documents. Read notes before acting; never rebuild `decisions.json` from a stale version. The server rejects writes from a tab with an outdated revision. Do not run multiple servers against the same private workspace.
