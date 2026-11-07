# HomePanel MVP

The supplied specification is the implementation brief. Build locally; do not install into a real HA instance.

1. Dashboard and interactive demo, independent of HA.
2. Typed YAML configuration and environment-only credentials.
3. Session authentication, CSRF checks, explicit entity/action allowlist.
4. HA REST adapter with shared short cache, timeouts and reconnect backoff.
5. Media capabilities, metadata, safe server-side artwork proxy, music view.
6. Docker, local HA OS app packaging, Windows instructions, API tests, browser QA.

Use REST polling rather than a persistent WebSocket for this small MVP. One server cache serves all panels; hidden browser tabs poll less often. No database is needed. Use httpx explicitly for its stable small HTTP/1.1 stack and FastAPI TestClient compatibility.

Secondary music search and queue browsing can follow after the core is verified. Do not invent MA response schemas. Configuration of entity permission belongs to the server YAML, not a browser endpoint.
