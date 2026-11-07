# Mac toolchain check — 2026-11-07

Repository checked at `1cdf53d`. This is a build prerequisite report, not an
implementation or device-performance result.

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

## Scope still outstanding

The four requested handoff documents and native draft were read. The current
native directory is still an incomplete decoder draft, including its documented
overflow issue. There is no native application or IPA. No unofficial SDK was
downloaded, no substitute binary was packaged, and no signing assets were used.

The HA visual redesign, renderer, authenticated display protocol, actual Music
Assistant frontend, native networking/lifecycle and IPA packaging remain to be
implemented. None is represented as complete by this prerequisite change.
There are no measured latency, FPS, bandwidth, CPU or RAM results. Physical iPad,
HA/MA integration, jailbreak installation and Sideloadly remain unverified.
