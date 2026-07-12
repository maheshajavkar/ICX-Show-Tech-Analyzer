# ICX-Show-Tech-Analyzer

## Cursor Cloud specific instructions

### What this is
This repo is a **single-file, zero-dependency static web app**: `ICX_ShowTech_Analyzer_v3_0.html`.
It parses Ruckus/CommScope ICX switch "show tech-support" output entirely in the browser and
renders a health/findings dashboard. There is **no package manager, no build step, no backend,
no database, and no automated test/lint tooling** in the repo.

### Run it (development)
Serve the repo root over HTTP and open the file (opening via `file://` also works but a static
server avoids browser quirks):

```
python3 -m http.server 8000
# then open http://localhost:8000/ICX_ShowTech_Analyzer_v3_0.html
```

`python3` is preinstalled; nothing needs to be installed to run this app.

### Non-obvious gotchas
- **Login gate:** the app opens on a login screen. Hardcoded credentials are `ruckus` / `tac@2026`
  (see the `AUTH` object in the HTML). Auth is stored in `sessionStorage`.
- **Input format:** upload an ICX "show tech-support" text file via the drop zone. The section
  splitter (`getSections`) recognizes either `BEGIN:/END:` blocks or prompt-echoed CLI commands
  like `SSH@HOST#show version`. Files that don't contain recognizable `show ...` sections parse
  to an empty dashboard.
- **Optional AI summary** requires a user-supplied Azure OpenAI endpoint + API key (kept in
  `sessionStorage`); it is not needed for core parsing/findings.
- **CDN dependence:** the topology graph (Cytoscape.js) and web fonts load from CDNs. Core
  parsing/findings work offline; the graph/fonts degrade without internet.

### Optional Azure OpenAI backend proxy (`server.py`)
`server.py` (Python stdlib only, no pip installs) is an optional way to run the app.
It serves the HTML **and** proxies AI calls to Azure OpenAI so the API key stays
server-side (avoids browser CORS + key exposure). Configure via env vars
(`AZURE_OPENAI_ENDPOINT`, `AZURE_OPENAI_API_KEY`, `AZURE_OPENAI_DEPLOYMENT`,
`AZURE_OPENAI_API_VERSION`, `PORT`) then `python3 server.py` → `http://localhost:8000/`.
Endpoints: `GET /api/ai/status`, `POST /api/ai/chat`. Full details in
`docs/AZURE_OPENAI_INTEGRATION.md`.

- The page auto-detects the backend via `GET /api/ai/status`; if absent it falls
  back to the browser-entered *Azure OpenAI Configuration* card, then to a local
  summary generator. So the app still runs fine under plain `python3 -m http.server`.
- To test the proxy without a paid Azure resource, point `AZURE_OPENAI_ENDPOINT` at
  any HTTP endpoint returning an Azure-shaped `{"choices":[{"message":{"content":...}}]}`.

### Lint / test / build
None exist. Do not add build/test infrastructure unless explicitly requested.
