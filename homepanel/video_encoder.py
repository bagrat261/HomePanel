from fractions import Fraction
from io import BytesIO

import av


class VideoEncoder:
    def __init__(self, fps: int):
        self.codec = av.CodecContext.create("libx264", "w")
        self.codec.width = 1024
        self.codec.height = 720
        self.codec.pix_fmt = "yuv420p"
        self.codec.time_base = Fraction(1, fps)
        self.codec.framerate = Fraction(fps)
        self.codec.thread_count = 2
        self.codec.bit_rate = 2_500_000
        self.codec.options = {
            "preset": "ultrafast",
            "tune": "zerolatency",
            "profile": "baseline",
            "level": "3.1",
            "g": "1",
            "bf": "0",
            "x264-params": "aud=1:repeat-headers=1:vbv-maxrate=4000:vbv-bufsize=400",
        }
        self.sequence = 0

    def encode(self, jpeg: bytes) -> bytes:
        with av.open(BytesIO(jpeg), format="mjpeg") as source:
            frame = next(source.decode(video=0))
        frame.pts = self.sequence
        frame.time_base = self.codec.time_base
        self.sequence += 1
        packets = self.codec.encode(frame)
        encoded = b"".join(bytes(packet) for packet in packets)
        if encoded[:5] != b"\x00\x00\x00\x01\x09":
            raise RuntimeError("Encoder did not emit the required AUD")
        identity = b"HomePanelFrameID" + str(self.sequence).encode("ascii")
        metadata = b"\x00\x00\x00\x01\x06\x05" + bytes([len(identity)]) + identity + b"\x80"
        return encoded[:6] + metadata + encoded[6:] + b"\x00\x00\x00\x01\x09\xf0\x00\x00\x00\x01"
