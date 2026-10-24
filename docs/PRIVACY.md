# Share the code, keep personal records private

The repository distributes the app, instructions and a fictional demo. Each person creates their own workspace. There is no telemetry or central backend receiving applications.

The local app does not call an AI provider. Your chosen agent may process the files you give it according to that service and its configuration. Application portals receive the details and documents submitted to them. With optional remote access, Telegram receives the login code and site URL.

Never commit `workspace/`, real CVs, receipts, notes, reports, `.env`, sessions, keys or backups. `.gitignore` helps but does not protect already tracked files or copies placed elsewhere. Screenshots can contain personal details too.

## Source export

`public-files.txt` explicitly lists distributable files. To audit and create a ZIP:

```sh
python scripts/audit_export.py
python scripts/audit_export.py --zip dist/job-search-workspace.zip
```

The audit rejects private or unexpected paths, symbolic links, some credential patterns and tracked files outside the list. The ZIP includes only listed files and refuses to replace an existing archive. These checks alone cannot prove that every text or image is anonymous: inspect changes before publishing, especially examples, PDFs and screenshots.

## Local storage

The server binds to `127.0.0.1`. Local use assumes a trusted computer and operating-system account. Do not expose that port directly or publish a copy of a personal workspace as a demo.

The app does not encrypt workspace files. Use operating-system permissions and encryption. For a consistent backup, stop the server and any agents writing to the workspace, then copy the entire private folder to a private destination. Removing a published secret from the latest commit does not revoke it: rotate the credential and review the history.
