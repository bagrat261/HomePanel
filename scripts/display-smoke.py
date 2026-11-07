import json
import os
import statistics
import sys
import threading
import time
from pathlib import Path

import av
import httpx
import psutil


def save_png(frame: av.VideoFrame, path: Path) -> None:
    encoder = av.CodecContext.create("png", "w")
    encoder.width, encoder.height = frame.width, frame.height
    encoder.pix_fmt = "rgb24"
    path.write_bytes(b"".join(bytes(p) for p in encoder.encode(frame.reformat(format="rgb24"))))


def main() -> None:
    base = sys.argv[1] if len(sys.argv) > 1 else "http://127.0.0.1:8090"
    target = Path("artifacts")
    target.mkdir(exist_ok=True)
    ready = threading.Event()
    stopped = threading.Event()
    changed = threading.Event()
    arrivals: list[float] = []
    failures: list[str] = []
    received = 0
    pixel: tuple[int, ...] = ()
    baseline: tuple[int, ...] = ()
    touch_at = 0.0
    changed_at = 0.0
    frame_id = 0
    process = psutil.Process(int(os.environ["HOMEPANEL_BENCH_PID"]))
    cpu_start = sum(process.cpu_times()[:2])
    peak_rss = 0
    with httpx.Client(base_url=base, timeout=20) as client:
        session = client.get("/api/session").json()
        if session.get("demo") is not True:
            raise RuntimeError("This smoke test only operates in isolated Demo mode")
        csrf = session["csrf"]
        client.headers["X-CSRF-Token"] = csrf
        selected = client.post("/api/display/surface", json={"surface": "dashboard"})
        selected.raise_for_status()
        generation = selected.json()["generation"]

        def read() -> None:
            nonlocal received, pixel, changed_at, frame_id
            decoder = av.CodecContext.create("h264", "r")
            try:
                with client.stream(
                    "GET", "/api/display/stream.h264", params={"generation": generation}
                ) as response:
                    response.raise_for_status()
                    for chunk in response.iter_bytes():
                        received += len(chunk)
                        for packet in decoder.parse(chunk):
                            for frame in decoder.decode(packet):
                                for side in frame.side_data:
                                    payload = bytes(side)
                                    if payload.startswith(b"HomePanelFrameID"):
                                        frame_id = int(payload[16:])
                                arrivals.append(time.monotonic())
                                plane = frame.reformat(format="rgb24").planes[0]
                                offset = 345 * plane.line_size + 100 * 3
                                pixel = tuple(memoryview(plane)[offset : offset + 3])
                                if (
                                    touch_at
                                    and baseline
                                    and sum(
                                        abs(a - b) for a, b in zip(pixel, baseline, strict=True)
                                    )
                                    > 30
                                    and not changed.is_set()
                                ):
                                    changed_at = time.monotonic()
                                    save_png(frame, target / "display-tap-result.png")
                                    changed.set()
                                if len(arrivals) == 1:
                                    save_png(frame, target / "display-first.png")
                                    ready.set()
                                if stopped.is_set():
                                    save_png(frame, target / "display-last.png")
                                    return
            except (httpx.HTTPError, av.error.FFmpegError) as error:
                failures.append(str(error))
                ready.set()

        reader = threading.Thread(target=read, daemon=True)
        started = time.monotonic()
        reader.start()
        if not ready.wait(25) or failures:
            raise RuntimeError(f"No decoded frame: {failures}")
        deadline = time.monotonic() + 8
        while len(arrivals) < 45 and time.monotonic() < deadline:
            processes = [process, *process.children(recursive=True)]
            peak_rss = max(peak_rss, sum(p.memory_info().rss for p in processes if p.is_running()))
            time.sleep(0.1)
        baseline = pixel
        before = next(
            e["state"]
            for e in client.get("/api/dashboard").json()["entities"]
            if e["entity_id"] == "light.demo_lounge"
        )
        touch_at = time.monotonic()
        response = client.post(
            "/api/display/input",
            json={
                "generation": generation,
                "frame": frame_id,
                "kind": "tap",
                "x": 225 / 1024,
                "y": 360 / 720,
            },
        )
        response.raise_for_status()
        if not changed.wait(8):
            raise RuntimeError("Tap did not change the decoded device card")
        after = next(
            e["state"]
            for e in client.get("/api/dashboard").json()["entities"]
            if e["entity_id"] == "light.demo_lounge"
        )
        if before == after:
            raise RuntimeError("Tap did not toggle the actual demo entity")
        cpu_end = sum(
            sum(p.cpu_times()[:2])
            for p in [process, *process.children(recursive=True)]
            if p.is_running()
        )
        elapsed = time.monotonic() - started
        stopped.set()
        reader.join(timeout=5)
        if reader.is_alive() or failures:
            raise RuntimeError(f"Stream failed to stop: {failures}")
        intervals = [b - a for a, b in zip(arrivals, arrivals[1:], strict=False)]
        result = {
            "frames": len(arrivals),
            "first_frame_ms": (arrivals[0] - started) * 1000,
            "delivered_fps": (len(arrivals) - 1) / (arrivals[-1] - arrivals[0]),
            "median_frame_ms": statistics.median(intervals) * 1000,
            "max_frame_ms": max(intervals) * 1000,
            "bandwidth_mbps": received * 8 / (time.monotonic() - started) / 1_000_000,
            "server_pid": os.environ.get("HOMEPANEL_BENCH_PID"),
            "server_cpu_percent_one_core": (cpu_end - cpu_start) / elapsed * 100,
            "server_process_tree_peak_rss_mib": peak_rss / 1024 / 1024,
            "local_tap_to_decoded_change_ms": (changed_at - touch_at) * 1000,
            "demo_state_before": before,
            "demo_state_after": after,
            "device_latency": "not measured",
            "ipad_cpu_ram": "not measured",
        }
        (target / "display-smoke.json").write_text(json.dumps(result, indent=2) + "\n")
        print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
