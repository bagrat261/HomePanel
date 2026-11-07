import time

import pytest
from fastapi import HTTPException

from homepanel.configuration import Settings
from homepanel.display import Display
from homepanel.display_models import DisplayConfig, DisplayInput
from homepanel.security import Security


def test_stopping_worker_retains_single_renderer_slot():
    from homepanel.renderer import Renderer

    display = Display(DisplayConfig(enabled=True), Security(Settings()))
    display.select("owner", "dashboard")
    renderer = Renderer(display.config, "dashboard", "cookie")
    import threading

    released = threading.Event()
    renderer.worker = threading.Thread(target=released.wait)
    renderer.worker.start()
    display.renderer = renderer
    try:
        with pytest.raises(HTTPException) as error:
            display.select("owner", "dashboard")
        assert error.value.status_code == 409
        assert display.renderer is renderer
    finally:
        released.set()
        renderer.worker.join()
    assert display.select("owner", "dashboard") == 2


def test_expired_or_unknown_frame_cannot_enqueue_a_touch():
    from homepanel.renderer import Renderer

    renderer = Renderer(DisplayConfig(), "dashboard", "cookie")
    renderer.frame_times.append((7, time.monotonic() - 3))
    for identity in (7, 8):
        with pytest.raises(HTTPException) as error:
            renderer.tap(DisplayInput(generation=1, frame=identity, kind="tap", x=0.5, y=0.5))
        assert error.value.status_code == 409
    assert renderer.inputs.empty()


def test_latest_independent_frame_replaces_backlog():
    from homepanel.renderer import Renderer

    renderer = Renderer(DisplayConfig(), "dashboard", "cookie")
    for frame in (b"oldest", b"previous", b"latest"):
        renderer.publish(frame)
    assert [renderer.output.get_nowait(), renderer.output.get_nowait()] == [b"previous", b"latest"]


def test_stop_during_guard_prevents_queued_click():
    from types import SimpleNamespace

    from homepanel.renderer import Renderer

    renderer = Renderer(DisplayConfig(), "dashboard", "cookie")
    renderer.frame_times.append((1, time.monotonic()))
    renderer.tap(DisplayInput(generation=1, frame=1, kind="tap", x=0.5, y=0.5))
    clicked = []

    class PageStoppingDuringGuard:
        mouse = SimpleNamespace(click=lambda *point: clicked.append(point))

        @property
        def url(self):
            renderer.stop()
            return "http://127.0.0.1:8090/#home"

    renderer.capture(PageStoppingDuringGuard())
    assert clicked == []
