# Native iPad client — incomplete source checkpoint

Implementation stopped at the user's request for a GitHub/Mac handoff.

Only `HomePanel/HPAnnexB.h`, `HPAnnexB.c`, `HPVideoView.h`, and `HPVideoView.m` exist. These are preliminary scanner and AVSampleBufferDisplayLayer decoder sources, not an application. They have NOT been compiled or run. No Xcode project, application entry point, network client, build scripts, tests, or IPA exists in this directory.

The server `/api/display/*` protocol is NOT IMPLEMENTED. These files must not be presented as a working client.

Before integration, implement and verify the full native shell and server display protocol from the Mac handoff. Use an Apple toolchain supporting iOS 9 and ARMv7 (such as Xcode 10.1 on a compatible Mac OS). A modern Xcode installation alone may not support this target. Verify a real Mach-O ARMv7 application and minimum deployment version before packaging Payload into an IPA. Signing/provisioning or jailbreak installation must be validated separately on the actual iPad.

Known review work: decoder overflow inside acceptNAL currently calls reset, which mutates the pending buffer while consume is iterating it; repair that path before use. Validate frame boundaries, multi-slice streams, SPS/PPS changes, missing AUD, packet fragmentation, truncated NALs, decoder backpressure, IDR recovery, main-thread rendering and a bounded serial networking queue. Confirm iOS 9 compilation and actual device decoding. The scanner currently has no executed boundary tests.
