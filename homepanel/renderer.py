import queue
import threading
import time
from collections import deque
from collections.abc import Iterator
from urllib.parse import urlencode, urlsplit

from fastapi import HTTPException
from playwright.sync_api import Error as BrowserError
from playwright.sync_api import Page, Route, sync_playwright

from homepanel.display_models import DisplayConfig, DisplayInput, Surface
from homepanel.video_encoder import VideoEncoder


class Renderer:
    def __init__(self, config: DisplayConfig, surface: Surface, cookie: str):
        self.config = config
        self.surface = surface
        self.cookie = cookie
        self.output: queue.Queue[bytes] = queue.Queue(maxsize=2)
        self.inputs: queue.Queue[DisplayInput] = queue.Queue(maxsize=4)
        self.stopped = threading.Event()
        self.input_lock = threading.Lock()
        self.last_frame = 0.0
        self.error: str | None = None
        self.dropped = 0
        self.worker: threading.Thread | None = None
        self.frame_times: deque[tuple[int, float]] = deque(maxlen=32)

    @property
    def alive(self) -> bool:
        return bool(self.worker and self.worker.is_alive())

    def fresh(self, identity: int) -> bool:
        return any(
            number == identity and time.monotonic() - captured < 2
            for number, captured in tuple(self.frame_times)
        )

    def stop(self) -> None:
        with self.input_lock:
            self.stopped.set()

    def tap(self, event: DisplayInput) -> None:
        with self.input_lock:
            if self.stopped.is_set() or not self.fresh(event.frame):
                raise HTTPException(409, "Кадр устарел; касание отклонено")
            try:
                self.inputs.put_nowait(event)
            except queue.Full:
                raise HTTPException(
                    429, "Слишком много касаний; повторите после обновления экрана"
                ) from None

    def frames(self) -> Iterator[bytes]:
        worker = threading.Thread(target=self.run, name="homepanel-renderer", daemon=True)
        self.worker = worker
        worker.start()
        try:
            while not self.stopped.is_set():
                try:
                    frame = self.output.get(timeout=1)
                except queue.Empty:
                    continue
                self.last_frame = time.monotonic()
                yield frame
        finally:
            self.stop()
            worker.join(timeout=20)

    def publish(self, frame: bytes) -> None:
        try:
            self.output.put_nowait(frame)
        except queue.Full:
            try:
                self.output.get_nowait()
            except queue.Empty:
                self.output.put_nowait(frame)
                return
            self.output.put_nowait(frame)
            self.dropped += 1

    def destination(self) -> str:
        if self.surface == "dashboard":
            return self.config.dashboard_url.rstrip("/") + "/#home"
        query = urlencode({"code": self.config.music_token.get_secret_value()})
        fragment = urlencode(
            {
                "player": self.config.music_player,
                "frameless": "true",
                "showFullscreenPlayer": "true",
            }
        )
        return self.config.music_url.rstrip("/") + "/?" + query + "#/home?" + fragment

    def route(self, route: Route) -> None:
        target = urlsplit(route.request.url)
        origin = urlsplit(
            self.config.dashboard_url if self.surface == "dashboard" else self.config.music_url
        )
        if (target.scheme, target.netloc) != (origin.scheme, origin.netloc):
            route.abort()
        elif route.request.is_navigation_request() and target.path not in ("", "/"):
            route.abort()
        else:
            route.continue_()

    def guard(self, page: Page) -> bool:
        location = urlsplit(page.url)
        expected = urlsplit(
            self.config.dashboard_url if self.surface == "dashboard" else self.config.music_url
        )
        allowed_hash = ("home", "") if self.surface == "dashboard" else ("/home", "/", "")
        if (location.scheme, location.netloc) != (expected.scheme, expected.netloc):
            return False
        return location.fragment.split("?", 1)[0] in allowed_hash

    def capture(self, page: Page) -> None:
        encoder = VideoEncoder(self.config.fps)
        while not self.stopped.is_set():
            started = time.monotonic()
            if not self.guard(page):
                self.error = "Navigation outside the selected surface was blocked"
                return
            try:
                event = self.inputs.get_nowait()
            except queue.Empty:
                event = None
            with self.input_lock:
                if self.stopped.is_set():
                    return
                if event and self.fresh(event.frame):
                    match event.kind:
                        case "tap":
                            page.mouse.click(min(event.x * 1024, 1023), min(event.y * 720, 719))
                        case "swipe":
                            page.mouse.move(min(event.x * 1024, 1023), min(event.y * 720, 719))
                            page.mouse.wheel(
                                (event.x - event.end_x) * 1024, (event.y - event.end_y) * 720
                            )
                    if not self.guard(page):
                        self.error = "Navigation outside the selected surface was blocked"
                        return
            jpeg = page.screenshot(type="jpeg", quality=75, animations="disabled", timeout=5000)
            if len(jpeg) > 2 * 1024 * 1024:
                self.error = "Capture exceeds memory limit"
                return
            encoded = encoder.encode(jpeg)
            if len(encoded) > 2 * 1024 * 1024:
                self.error = "Encoded access unit exceeds memory limit"
                return
            self.frame_times.append((encoder.sequence, started))
            self.publish(encoded)
            self.stopped.wait(max(0, 1 / self.config.fps - (time.monotonic() - started)))

    def run(self) -> None:
        try:
            if self.stopped.is_set():
                return
            with sync_playwright() as playwright:
                if self.stopped.is_set():
                    return
                with playwright.chromium.launch(headless=True) as browser:
                    if self.stopped.is_set():
                        return
                    context = browser.new_context(
                        viewport={"width": 1024, "height": 720},
                        device_scale_factor=1,
                        reduced_motion="reduce",
                    )
                    if self.surface == "dashboard":
                        context.add_cookies(
                            [
                                {
                                    "name": "homepanel_session",
                                    "value": self.cookie,
                                    "url": self.config.dashboard_url,
                                }
                            ]
                        )
                    context.route("**/*", self.route)
                    page = context.new_page()
                    page.on("popup", lambda popup: popup.close())
                    page.goto(self.destination(), timeout=15000, wait_until="domcontentloaded")
                    if self.surface == "dashboard":
                        page.add_style_tag(
                            content=".rail,.player{display:none!important}#main{margin-left:0;padding-bottom:24px}"
                        )
                    self.capture(page)
        except (OSError, BrowserError, BrokenPipeError):
            self.error = "Renderer failed; check dependencies and upstream availability"
        finally:
            self.stopped.set()
