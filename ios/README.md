# Native iPad client — ARMv7 build

[Русская инструкция: сборка, установка и подключение](README.ru.md)

The application is Objective-C/UIKit, with NSURLSession streaming and
AVSampleBufferDisplayLayer. It contains no WebView. Chromium runs on the server;
the iPad receives H.264 Baseline 3.1 at 1024×720 below a native 48px toolbar.
The current build is an **unsigned jailbreak IPA**, not device-tested software.

## Build

```sh
HOMEPANEL_IOS_SDK=/Applications/Xcode-10.1.app/Contents/Developer/Platforms/iPhoneOS.platform/Developer/SDKs/iPhoneOS.sdk \
  sh scripts/build-ios.sh
```

Output: `ios/build/HomePanel-armv7-jailbreak-unsigned.ipa`.
The script first links a framework probe, checks ARMv7 and minimum iOS 9.0,
then builds the real application and packages `Payload/HomePanel.app`.
Build directories and IPA are intentionally ignored by Git.

Verified build combination: Apple clang 21.0.0 from Xcode 27.0 with the official
iPhoneOS 12.1 SDK from Xcode 10.1. The current SDK alone cannot link ARMv7.
Xcode 10.1 was installed alongside Xcode 27; system selection is unchanged.
Its old IDE was not launched. Historical signature verification with `codesign`
reported `CSSMERR_TP_NOT_TRUSTED`; no trust bypass or OS setting change was used.
See [toolchain provenance](../docs/MAC-TOOLCHAIN.md).

## Install and connect

Use a jailbreak installer that supports unsigned IPA and the device's signing
bypass. Jailbreak alone does not guarantee installation. Alternatively import
the IPA into Sideloadly for signing with your own Apple account/provisioning;
this path has not been exercised here. No certificates or provisioning assets
are bundled. Do not install an ARM64 substitute on this iPad.

Start the optional [server renderer](../docs/REMOTE-DISPLAY.md), open HomePanel,
tap «Связь», enter its LAN origin (for example `http://192.168.1.10:8090`) and
the panel password. The address is saved; the password is never persisted.
An ephemeral session remains in memory. HA/MA tokens remain on the server.

«Дом» and «Музыка» select server surfaces. Tap controls and swipe vertically
to scroll. The decoder reads frame identities from SEI; input carries both
surface generation and frame identity. Stale frames/touches are rejected.
Backgrounding stops stream input and decoding and releases the idle timer.
Foregrounding reconnects. Missing fresh images disables input and shows offline.

## Verification limits

ARMv7 linking, IPA structure and pure C scanner/SEI tests passed on Mac.
The documented decoder overflow was repaired by removing consumed bytes before
dispatching a NAL and stopping iteration after reset. Actual iPad decoding,
sleep/Wi-Fi recovery, memory, CPU and installation remain unverified.
Server tests are not evidence of hardware decoding or display latency.
