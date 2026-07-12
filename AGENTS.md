# ICX-Show-Tech-Analyzer

## Cursor Cloud specific instructions

### What this is
A single-file, fully client-side web app: `ICX_ShowTech_Analyzer_v3_0.html`. It parses Ruckus ICX "show tech-support" text dumps entirely in the browser and renders a diagnostics dashboard (overview, findings, topology, VLANs, routing, ports). There is **no backend, build step, package manager, lockfile, or test suite**.

### Running the app (dev)
Serve the folder that contains the HTML file over HTTP and open it — do not open via `file://` (the CDN scripts/fonts and file APIs behave better over HTTP). `python3 -m http.server` serves files relative to its working directory, so run it from the repo root or pass `--directory`:

```
python3 -m http.server 8090 --directory /path/to/ICX-Show-Tech-Analyzer
```

Then browse to `http://localhost:8090/ICX_ShowTech_Analyzer_v3_0.html`.

Any free port works — just match it in the URL. If the browser reports "file not found", the server was almost certainly started from a directory that does not contain `ICX_ShowTech_Analyzer_v3_0.html` (fix with `cd` into the repo root or the `--directory` flag). Check a port before use with `ss -ltnp | grep :8090`.

Note: run the HTTP server yourself when you need it (e.g. via tmux); it is intentionally NOT part of the startup/update script.

### Login
The login is a hardcoded client-side gate (see `const AUTH` in the `<script>`): username `ruckus`, password `tac@2026`. Auth state is kept in `sessionStorage` (`tac_auth`).

### Exercising core functionality
After login, upload a show-tech text file on the upload screen to auto-parse and render the dashboard. `sample_showtech.txt` in the repo root is a synthetic ICX show-tech that triggers a representative spread of findings (critical/warning/ok/info) and is handy for manual testing.

### Non-obvious notes
- External runtime deps (Cytoscape for topology, Google Fonts) load from CDNs, so topology rendering and fonts need network egress; the rest works offline.
- The optional "AI executive summary" feature calls a user-configured Azure OpenAI endpoint; without config it falls back to a local generator, so no key is required to use the app.
- Lint/test/build: none exist. Validation is manual via the browser flow above.
