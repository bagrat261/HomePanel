# Remote display setup and measured limits

HomePanel is a native Objective-C iPad client plus an optional renderer in the
HomePanel server, separate from HA Core. The renderer executes Dashboard or the
actual Music Assistant frontend in Chromium, captures JPEG on the server, and
encodes H.264 with PyAV/FFmpeg libx264. JPEG is never sent to the iPad.

## Local server

```sh
uv sync --extra dev --extra renderer
uv run python -m playwright install chromium
HOMEPANEL_DISPLAY_ENABLED=true uv run uvicorn homepanel.app:app --host 0.0.0.0 --port 8090 --workers 1
```

For LAN access add the server IP/hostname to `allowed_hosts`. Set a unique
`PANEL_PASSWORD`. Configure live HA using the existing instructions. The internal
renderer origin defaults to `http://127.0.0.1:8090`; change `display.dashboard_url`
if listening elsewhere. Run exactly one server worker: ownership and sessions
are deliberately in-process. The ordinary backend still runs without renderer
dependencies when display is disabled (default).

Optional bounded container: `docker compose -f docker-compose.renderer.yml up --build`.
This uses a separate Dockerfile, one worker, 2 CPU / 1 GiB / 128 PID limits and
256 MiB shared memory. It is **not build/run verified** in this environment.
Its loopback-only port binding must be changed intentionally for LAN.
No HAOS or real HA system was installed or modified. There is no renderer-specific
HAOS package yet; the original HAOS package remains the base backend.

## Actual Music Assistant frontend

Create a separate restricted MA user with access to only intended players and
music sources. Create that user's long-lived token. On the server set `MA_URL`
and `MA_TOKEN` through environment/secret management. Do not send the token to
the iPad, commit it, or use an administrator token. Add to private YAML:

```yaml
display:
  enabled: true
  dashboard_url: http://127.0.0.1:8090
  fps: 15
  music_player: Livingroom
  music_restricted_user: true
```

`music_restricted_user` records operator configuration; it does **not** verify
the account's privileges. MA itself must enforce the restricted role. Until
configured, Music returns 503 rather than a substitute player. The server opens
the official frontend using `?code=...#/home?player=...&frameless=true&showFullscreenPlayer=true`.
External HTTP navigation, popups and routes outside the selected home/player
surface are blocked or stop the stream before the next capture. Settings routes
are not exposed as native destinations. Same-route dialogs depend on MA's role
authorization. Frameless/menu hiding is not a security boundary. Playlists are
not enabled in this first slice.

Official references:
[frontend URL options](https://www.music-assistant.io/faq/how-to/),
[user management](https://www.music-assistant.io/settings/user-management/).
No live MA instance/credentials were available; actual playback, restricted-role
authorization and every settings dialog still require integration testing.

## Protocol and resource bounds

- GET `/api/display/status`: authenticated feature status and 1024×720 dimensions.
- POST `/api/display/surface`: CSRF-protected `dashboard` or `music`, returns generation.
- GET `/api/display/stream.h264?generation=N`: authenticated Annex B stream.
- POST `/api/display/input`: CSRF-protected generation, frame, kind, x/y in 0..1.
  Swipes additionally require end_x/end_y. No arbitrary URL or JavaScript input.

One session owns the display. Competing sessions receive 409. Replacements wait
for the previous browser worker to finish. Output holds two independent frames;
input holds four events. Each compressed frame is limited to 2 MiB. Frames older
than 2 seconds, unknown identities and events from old generations are rejected;
age is checked again before executing an accepted event. The last 32 frame
capture timestamps are retained. SEI UUID `HomePanelFrameID` plus an ASCII integer
binds the native input to a captured frame. All frames are IDR with repeated
SPS/PPS and AUD, no B-frames, Baseline level 3.1, 15 fps maximum. This initial
all-IDR choice favours safe dropping over compression efficiency.

The application disables touches after two seconds without new enqueued frames;
that timestamp does not measure actual glass presentation. Background disconnect
cleanup and bounded queues reduce accumulation; TCP/proxy buffering remains a
field-test concern. Disable reverse-proxy buffering for this endpoint.

## Observed local benchmark

Command: `HOMEPANEL_BENCH_PID=<uvicorn-pid> .venv/bin/python scripts/display-smoke.py`.
The harness is intended for isolated Demo only; it toggles the first Demo light.
It decodes real H.264 and detects the changed device-card pixels, then confirms
the actual entity state changed. It does not issue live HA commands.

Mac ARM64 / macOS 26.6.2, local loopback, 1024×720, requested 15 fps, latest 48-frame run:

| Measurement | Observed |
|---|---:|
| Delivered rate | 14.31 fps |
| Median / maximum frame interval | 67.09 / 117.79 ms |
| Session start to first decoded frame | 1.03 s |
| Local tap to changed decoded frame | 94.33 ms |
| Traffic averaged over entire session including startup | 2.00 Mbit/s |
| Server plus live children CPU, one core = 100% | 49.68% |
| Sampled peak sum of server/child RSS | 568.36 MiB |

This is a short run, not a percentile study or a sustained-load claim. Browser
regression QA overlapped its startup on the same Mac; it was not an idle-host
benchmark. The prior isolated 49-frame run delivered 14.37 fps, tap-to-decoded
change 134.55 ms, 48.88% CPU and 531.89 MiB RSS. Demo state changed off→on in the
latest run and on→off in the prior run. RSS sums count shared pages more than
once. Earlier cold startup took 10.75 s.
Chromium and encoding remain material load for a weak HA host. iPad CPU/RAM,
Wi-Fi latency, hardware-decoder latency and actual touch-to-glass latency were
**not measured**. There is no evidence yet to promise smoothness on iPad 2.
Compare lower fps and a short inter-frame GOP on the intended host before changing
the independent-frame transport; dropping predicted frames would require an
explicit IDR recovery policy.
