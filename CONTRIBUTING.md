# Contributing

Start with the Windows or uv setup in README.md. Keep the main dashboard ES5;
no runtime build step, CDN dependency, Grid, CSS variables or fetch.

Before submitting changes run Python tests, Ruff and `npm run check:es5`.
When changing UI, exercise the real page at 1024×768 and a narrow viewport.
Record hardware/browser versions; never describe modern emulation as iOS 9 testing.

New controls must have explicit server-side entity permissions, capabilities,
parameter bounds and tests using Demo or MockTransport. Do not replay service
POSTs after ambiguous failures. Consult official HA/MA documentation before
adding an action. Treat artwork URLs and integration attributes as untrusted.

Keep credentials out of fixtures, logs, screenshots and issues. Report security
issues privately to the maintainer of your deployed fork; no public contact
address or upstream repository has been established for this local project yet.
