# Mac toolchain check — 2026-11-07

Repository checked at `1cdf53d`. This is a build prerequisite report, not an
implementation or device-performance result.

## Follow-up: genuine native build achieved

With the user's authorization, official `Xcode_10.1.xip` (5.63 GB shown by Apple)
was downloaded through the authenticated Apple Developer archive and expanded
into `/Applications/Xcode-10.1.app`. `/Applications/Xcode.app` and system selection
were preserved. The legacy IDE/compiler was not executed. `xip` reported the
Software Update signing certificate with validation not attempted; subsequent
`codesign --verify` returned `CSSMERR_TP_NOT_TRUSTED`. No trust bypass was applied.

Apple clang 21.0.0 from Xcode 27 successfully compiled and linked against the
official iPhoneOS 12.1 SDK from Xcode 10.1. The framework probe and real HomePanel
binary both identify as ARMv7; `LC_VERSION_MIN_IPHONEOS` is 9.0. The application
was packaged in `Payload/HomePanel.app` as an unsigned jailbreak IPA. This does
not prove launch, installation or hardware decoding on iPad 2. See
[native build instructions](../ios/README.md) and [measurements](REMOTE-DISPLAY.md).

The observations below record why the current SDK alone failed before the legacy
SDK was available; they are retained as provenance rather than the current blocker.

## Observed environment

- macOS 26.6.2 (25G83), ARM64 host.
- Selected developer directory: `/Applications/Xcode.app/Contents/Developer`.
- Xcode 27.0 (27A266a), iPhoneOS SDK 27.0.
- `clang -arch armv7 -miphoneos-version-min=9.0 -x c -c /dev/null` succeeds;
  `lipo -info` identifies the result as ARMv7. This only proves object emission.
- Linking against the selected SDK fails. The linker reports missing ARMv7
  slices in `libSystem.B.tbd`, `UIKit.tbd`, and `Foundation.tbd`, then
  `dynamic executables or dylibs must link with libSystem.dylib`.
- The linker itself lists ARMv7 among its supported architectures. Its presence
  does not restore the missing SDK libraries.

Apple documents removal of 32-bit app builds starting with Xcode 14:
https://developer.apple.com/news/upcoming-requirements/?id=06062022a

## Reproduce before building

```sh
sh scripts/check-ios-toolchain.sh
```

The preflight must compile and link UIKit, Foundation, AVFoundation and CoreMedia,
verify the resulting Mach-O architecture, and verify minimum iOS 9.0. A compiler
accepting `-arch armv7` or an archive containing `Payload/` does not pass this gate.
The probe is temporary; it is never packaged as HomePanel.

An official legacy Xcode/SDK obtained from Apple is required to investigate the
next build path. Xcode 10.1 is a candidate from the original brief, not a verified
working toolchain on this macOS/Apple Silicon host. Do not change the system
Xcode selection or assume that an old Xcode application runs here. A compatible
older Mac/build host may be needed. Use an explicit developer directory to test:

```sh
DEVELOPER_DIR=/path/to/LegacyXcode.app/Contents/Developer \
  sh scripts/check-ios-toolchain.sh
```

An explicitly supplied official SDK can also be probed with
`HOMEPANEL_IOS_SDK=/path/to/iPhoneOS.sdk`; compatibility with the selected compiler
and linker still has to pass the actual link and device tests.

Apple downloads: https://developer.apple.com/download/all/

## Initial checkpoint and remaining verification

The four requested handoff documents and native draft were read. The documented
overflow path was repaired, a native application and renderer were implemented,
and a real ARMv7 IPA was built. No unofficial SDK, substitute binary or signing
assets were used.

Local H.264 decoding, returned Demo touch, FPS, latency and server CPU/RAM were
measured; results and limits are in REMOTE-DISPLAY.md. Physical iPad, live HA/MA,
jailbreak installation, Sideloadly and container/HAOS deployment remain unverified.
