# Agent compatibility

The shared contract is the filesystem, `run.py` commands and `AGENTS.md`. The backend does not call a model API.

| Environment | Starting point | Required capabilities |
| --- | --- | --- |
| Codex with repository access | Open the folder and use START_HERE.md; AGENTS.md provides context | Terminal/Python, web access and an authorized browser for submissions |
| Claude Code | Open the folder; CLAUDE.md imports AGENTS.md | The same capabilities; configure browser access in that environment |
| Another tool-enabled agent | Explicitly ask it to read AGENTS.md and START_HERE.md | Files, command execution and the necessary external tools |
| Chat without files or tools | Can help draft a profile or evaluate supplied job descriptions | Cannot operate this repository or verify submissions by itself |

Models can differ in job selection and writing. The commands keep records consistent, hash documents and detect duplicates; they do not guarantee identical reasoning.

## Initial capability check

1. Run `python run.py doctor` and check the private folder.
2. Research a current opening using an available tool and verify the complete posting.
3. Check for an authorized session on the destination portal before attempting submission.
4. Open the PDF or render its pages. If Poppler is unavailable, use another viewer; do not claim to have reviewed an unseen document.
5. Record specific blockers and continue with independent work.

Browser sessions, commercial plugins and third-party skills are not redistributed. The core workflow is documented here and the PDF generator is included. Skills already installed by a user can complement it.

Official references: [Codex AGENTS.md instructions](https://learn.chatgpt.com/docs/agent-configuration/agents-md), [Claude Code memory and instructions](https://code.claude.com/docs/en/memory). The structure follows these conventions; test a complete workflow in each environment before claiming verified support.
