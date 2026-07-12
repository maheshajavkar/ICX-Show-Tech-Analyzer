# Azure OpenAI / Azure AI Foundry Integration Guide

This guide explains how the **ICX Show-Tech Analyzer** connects to **Azure OpenAI**
(also surfaced through **Azure AI Foundry**, formerly Azure AI Studio) so engineers
can ask AI-based troubleshooting questions about an uploaded show-tech capture.

The existing UI is unchanged. The AI features live on the **🤖 AI Troubleshoot**
tab:

- **Troubleshoot Search** - ask a free-form question; the answer is rendered inline.
- **AI Executive Summary** - generate a TAC-style health summary of the device.

There are two ways the page can reach Azure OpenAI:

1. **Backend proxy (recommended, secure)** - a tiny server (`server.py`) holds the
   API key and forwards requests. The key never touches the browser and there are
   no CORS problems.
2. **Direct from the browser (fallback)** - the user pastes the endpoint/key into
   the *Azure OpenAI Configuration* card. Simple for a quick demo, but the key is
   exposed client-side and most Azure resources block direct browser calls (CORS).

The page auto-detects a backend: if `server.py` is running it uses the proxy;
otherwise it falls back to the browser config; otherwise it uses the built-in
local summary generator.

---

## 1. Azure OpenAI / Azure AI Foundry setup

You need an Azure subscription with access to Azure OpenAI.

1. **Create the resource**
   - Azure Portal (`portal.azure.com`) -> **Create a resource** -> search
     **Azure OpenAI** -> **Create**.
   - Pick a subscription, resource group, region, and name, then create it.
   - (Equivalently, in **Azure AI Foundry** at `ai.azure.com` you can create/attach
     an Azure OpenAI resource under a project.)

2. **Deploy a model**
   - Open the resource, then **Azure AI Foundry portal** -> **Deployments** ->
     **Deploy model** (a chat model such as `gpt-4o`, `gpt-4o-mini`, or `gpt-4`).
   - Give the deployment a name (for example `gpt-4o`). **This deployment name is
     what you configure below** - it is not necessarily the raw model name.

3. **Get the endpoint and key**
   - Resource -> **Keys and Endpoint**.
   - Copy the **Endpoint** (e.g. `https://my-resource.openai.azure.com`) and **KEY 1**.

4. **Pick an API version**
   - Use a current version such as `2024-12-01-preview`.

5. **Authentication options**
   - **API key** (used by this tool): send the key in the `api-key` header.
   - **Microsoft Entra ID (AAD)**: for keyless auth you would assign the
     *Cognitive Services OpenAI User* role and send a bearer token instead of a
     key. `server.py` uses the API-key method; swapping to AAD only changes how the
     server authenticates upstream (see "Production hardening").

You now have four values: **endpoint**, **API key**, **deployment name**,
**API version**.

---

## 2. Backend changes (the proxy)

The backend is a single file, `server.py`, using only the Python standard library
(no `pip install` needed). It:

- serves the analyzer HTML and static assets, and
- exposes a same-origin API that keeps the key server-side:

| Method & path        | Purpose                                                                 |
|----------------------|-------------------------------------------------------------------------|
| `GET /`              | Serves `ICX_ShowTech_Analyzer_v3_0.html`.                               |
| `GET /api/ai/status` | Returns `{configured, deployment, apiVersion}` (never the key).         |
| `POST /api/ai/chat`  | Forwards `{messages, max_tokens, temperature}` to Azure OpenAI.         |

Configure it with environment variables (see `.env.example`):

```
AZURE_OPENAI_ENDPOINT=https://your-resource.openai.azure.com
AZURE_OPENAI_API_KEY=your-azure-openai-key
AZURE_OPENAI_DEPLOYMENT=gpt-4o
AZURE_OPENAI_API_VERSION=2024-12-01-preview
PORT=8000
```

Run it:

```bash
set -a && . ./.env && set +a     # load your local .env (do not commit real keys)
python3 server.py
# -> http://localhost:8000/
```

Internally `POST /api/ai/chat` calls:

```
POST {endpoint}/openai/deployments/{deployment}/chat/completions?api-version={version}
Header: api-key: {key}
Body:   {messages, max_tokens, temperature}
```

and returns Azure's JSON response verbatim.

---

## 3. Frontend integration (existing HTML page)

**No visual/UI changes were made** - only client-side JavaScript wiring was added,
so the layout, colors, fonts, and styling are identical.

- A helper `aiChatCompletion(messages, opts)` was added. It:
  1. probes `GET /api/ai/status`; if a backend is configured, it calls
     `POST /api/ai/chat` (secure proxy),
  2. otherwise falls back to a direct browser call using the *Azure OpenAI
     Configuration* card,
  3. otherwise throws `not-configured` (the page then shows Copilot hand-off links
     or the local summary).
- The existing **AI Troubleshoot** (`askTroubleshoot`) and **AI Executive Summary**
  (`generateAISummary`) functions now call this helper. When the proxy answers, the
  source label reads `Azure OpenAI - <deployment> - secure proxy`.
- The **Test Connection** button also validates the backend when no browser config
  is present.

Because the page is served by `server.py` from the same origin, calls to
`/api/ai/*` are same-origin (no CORS) and no key is stored in the browser.

---

## 4. How show-tech data is sent, and how answers are displayed

**What is sent (data flow):**

1. You upload a show-tech file; the app parses it entirely in the browser into a
   `parsed` object plus a `findings` list.
2. When you ask a question, `buildDeviceContext()` builds a compact,
   PII-light context from the parsed data: hostname, model, software/uptime, stack
   topology, VLAN/LAG counts, BGP/VRRP state, and the top critical/warning findings.
   For the executive summary, a richer prompt with routing, temperature, and the
   full findings list is built.
3. That context is placed in the chat `messages` (a `system` role that defines the
   "senior Ruckus TAC engineer" persona plus a `user` role containing the context
   and your question).
4. `aiChatCompletion` sends the messages to the backend proxy (or directly to Azure
   when configured that way).

> Note: the raw file is **not** uploaded wholesale - only the parsed summary and
> findings are sent, which keeps prompts small and avoids leaking unnecessary data.
> To send more detail, extend `buildDeviceContext()` (for example, include selected
> raw sections from `parsed.rawSections`).

**How answers are displayed:**

- The model's markdown reply is converted to HTML (`markdownToHTML`) and rendered in
  the **AI Troubleshooter** card (`#ts-answer-content`), with a source badge and
  Copilot hand-off links.
- The executive summary is rendered in the **AI Analysis** card
  (`#ai-content-area`), ready to paste into a TAC/SFDC case.

---

## 5. Testing locally and deploying to production

### Test locally (with a real Azure resource)

```bash
export AZURE_OPENAI_ENDPOINT="https://your-resource.openai.azure.com"
export AZURE_OPENAI_API_KEY="<key>"
export AZURE_OPENAI_DEPLOYMENT="gpt-4o"
python3 server.py
```

1. Open `http://localhost:8000/`, log in, and upload a show-tech file.
2. Go to **🤖 AI Troubleshoot**, type a question, click **Ask**. The answer renders
   inline with the `secure proxy` badge.
3. Quick API checks:

   ```bash
   curl http://localhost:8000/api/ai/status
   curl -X POST http://localhost:8000/api/ai/chat \
     -H 'Content-Type: application/json' \
     -d '{"messages":[{"role":"user","content":"Reply with just: OK"}],"max_tokens":5}'
   ```

### Test locally without a paid Azure resource

Point the server at any HTTP endpoint that returns an Azure-shaped chat-completion
JSON (`{"choices":[{"message":{"content":"..."}}]}`) by setting
`AZURE_OPENAI_ENDPOINT` to that stand-in. This exercises the full
browser -> proxy -> upstream path without incurring Azure costs.

### Direct-from-browser (no backend)

Serve the HTML any way you like (even `python3 -m http.server`), open **AI
Troubleshoot -> AI Executive Summary**, and fill in the **Azure OpenAI
Configuration** card (endpoint, key, deployment). Note the CORS/key-exposure caveats
above; prefer the backend proxy for anything beyond a personal demo.

### Deploy to production

- Run `server.py` behind a production reverse proxy (nginx / Azure App Service /
  container) terminating **HTTPS**. Keep it internal to your TAC network.
- Provide the Azure values as platform environment variables or secrets
  (e.g. Azure App Service *Application settings*, Key Vault references) - never
  commit real keys.
- **Production hardening to consider:**
  - Put the tool behind SSO/authentication (the built-in login is a demo gate only).
  - Prefer **Microsoft Entra ID (managed identity)** over API keys for the
    server->Azure call, and restrict the Azure resource's networking.
  - Add rate limiting / request-size limits and logging/monitoring.
  - Restrict `Access-Control-Allow-Origin` to your known origin(s) if you serve the
    API cross-origin (not needed when the page is served same-origin by `server.py`).
