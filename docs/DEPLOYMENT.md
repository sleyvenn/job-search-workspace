# Local use and private hosting

The normal entry point is to ask your agent to run `python run.py bootstrap` and open the returned URL. It starts in the background, preserves records and reuses a matching workspace server. Logs are stored in `workspace/runtime/`. The computer must remain on; this command does not install a startup service.

To stop it, verify that the PID in `runtime/server.json` still belongs to `run.py` and that workspace before terminating the process. Run `bootstrap` again to reopen it.

## Optional self-hosting

This version supports **one person and one Telegram recipient per installation**. Hosting requires Python 3.11+, persistent storage and an HTTPS reverse proxy forwarding to the loopback port. Do not expose the development server directly to the internet.

1. Initialize a private workspace outside any public directory and restrict its filesystem permissions.
2. Configure your own Telegram bot and recipient. Copy `.env.example` to `.env`, or use service environment variables. Never include the token in Git, screenshots or shared commands.
3. Set `WORKSPACE_PUBLIC_URL=https://your-subdomain.example`, `WORKSPACE_DIR`, `TELEGRAM_BOT_TOKEN` and `TELEGRAM_CHAT_ID`. The URL must be an HTTPS origin without a path.
4. Run `python run.py serve --port 8765` through the operating system's service manager. `bootstrap` is for local use only.
5. Configure the proxy to preserve the public Host, rate-limit requests and avoid logging bodies containing codes. Restrict direct access to the loopback port.
6. Verify from a signed-out session that documents, notes, reports and API data require authentication. Then test a real code with the bot owner's authorization.

When a public URL is configured, Telegram credentials are required; missing configuration does not expose content. Codes expire after five minutes, are single-use and have request and attempt limits. The session cookie uses Secure, HttpOnly and SameSite=Strict. Sessions last up to 30 days and can be closed from the interface.

`reviews/auth.sqlite` and `reviews/auth.key` are private. Automated tests mock delivery and send no messages. The operator is responsible for actual hosting, the proxy, backups and monitoring.

Hosting the app does not run an agent daily. Searches require an authorized execution environment and scheduler with the necessary tools and sessions.
