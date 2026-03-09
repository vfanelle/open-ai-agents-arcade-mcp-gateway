# Integration Challenges: OpenAI Agents SDK + Arcade MCP Gateway

## 1. Wrong constructor signature for `MCPServerStreamableHttp`
**Fault:** Us

The `MCPServerStreamableHttp` constructor requires a `params` argument typed as `MCPServerStreamableHttpParams` (a TypedDict). We initially passed `url` and `headers` as direct keyword arguments, which is wrong.

**Fix:** Wrap config in `MCPServerStreamableHttpParams(url=..., headers=...)` and pass as `params=`.

---

## 2. Header value was a string literal instead of a variable
**Fault:** Us

The `Arcade-User-ID` header was set to the string `"ARCADE_USER_ID"` instead of the variable `ARCADE_USER_ID`, so Arcade never received the actual user identity.

**Fix:** Remove the quotes — `"Arcade-User-ID": ARCADE_USER_ID`.

---

## 3. Wrong environment variable name
**Fault:** Us

The code was reading `ARCADE_USER_EMAIL` from the environment but the `.env` file used `ARCADE_USER_ID`. The header was silently sending `None`.

**Fix:** Align the `os.getenv()` call with the actual key in `.env` (`ARCADE_USER_ID`).

---

## 4. Session timeout too short for `list_tools`
**Fault:** MCP client defaults / gateway latency

The default `client_session_timeout_seconds` is 5 seconds. The Arcade gateway takes longer than that to respond to the initial `list_tools` request, causing a `McpError: Timed out while waiting for response`.

**Fix:** Set `client_session_timeout_seconds=30`, `timeout=30`, and `sse_read_timeout=300` on the server config.

---

## 5. OAuth re-prompt despite existing authorization
**Fault:** Us (wrong user ID being sent)

Even though Gmail was already authorized in Arcade, the agent kept triggering the OAuth flow. This was a downstream effect of issue #3 — `None` or the wrong user ID was being sent in the `Arcade-User-ID` header, so Arcade couldn't look up the existing authorization.

**Fix:** Resolved by fixing the env var name (issue #3).

---

## 6. No signal when URL elicitation (OAuth) completes (OAI MCP client)
**Fault:** MCP protocol limitation

After the agent presents an OAuth URL, there is no mechanism in the MCP protocol for the gateway to push a "authorization complete" notification back to the client. The agent just stalls waiting for the user to do something.

**Fix:** Updated the system prompt to instruct the agent to ask the user to confirm when authorization is complete, then automatically retry the original request.

---

# FastMCP Client

## 7. `fastmcp` not installed in the virtual environment
**Fault:** Us

Ran `pip install fastmcp` against the system Python instead of the project venv, so the module wasn't available when running `python3 main.py` inside the venv.

**Fix:** Install into the venv explicitly — `venv/bin/pip install fastmcp`.

---

## 8. Invalid tool schema — object missing `properties`
**Fault:** Arcade gateway / OpenAI API strictness

Some tools (e.g. `Gmail_ListLabels`) have an input schema of `{"type": "object"}` with no `properties` field. OpenAI's API rejects these with `invalid_function_parameters`.

**Fix:** Added a `sanitize_schema()` helper that injects `"properties": {}` into any object schema missing it before passing to `FunctionTool`.

---

## 9. `CallToolResult` is not iterable
**Fault:** Us (incorrect assumption about FastMCP's return type)

Assumed `client.call_tool()` returns a list of content items directly (like the raw MCP SDK). FastMCP wraps the result in a `CallToolResult` object — iterating over it directly raises `TypeError: 'CallToolResult' object is not iterable`.

**Fix:** Access `.content` on the result — `result.content` is the list of MCP content items.
