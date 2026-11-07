#!/bin/sh
set -eu

root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
work=$(mktemp -d "${TMPDIR:-/tmp}/homepanel-toolchain.XXXXXX")
trap 'rm -rf -- "$work"' EXIT HUP INT TERM

echo 'HomePanel native ARMv7 / iOS 9 toolchain preflight'
sw_vers
uname -m
xcode-select -p
xcodebuild -version
sdk=${HOMEPANEL_IOS_SDK:-$(xcrun --sdk iphoneos --show-sdk-path)}
printf 'SDK: %s\n' "$sdk"
test -d "$sdk" || { echo 'FAIL: SDK directory does not exist.' >&2; exit 1; }
clang=$(xcrun --find clang)
"$clang" --version

if ! "$clang" -arch armv7 -isysroot "$sdk" -miphoneos-version-min=9.0 \
    -fobjc-arc -Werror=unguarded-availability \
    "$root/ios/ToolchainProbe/main.m" \
    -framework UIKit -framework Foundation -framework AVFoundation \
    -framework CoreMedia -o "$work/HomePanelProbe"; then
    echo 'FAIL: cannot compile/link the native UIKit + H.264 client for ARMv7/iOS 9.' >&2
    echo 'Use an official Apple legacy SDK/toolchain. An ARMv7 .o alone is insufficient.' >&2
    exit 1
fi

archs=$(xcrun lipo -archs "$work/HomePanelProbe")
printf 'Linked architectures: %s\n' "$archs"
test "$archs" = armv7 || { echo 'FAIL: expected ARMv7 executable.' >&2; exit 1; }
xcrun otool -hv "$work/HomePanelProbe"
xcrun otool -L "$work/HomePanelProbe"
xcrun otool -l "$work/HomePanelProbe" > "$work/load-commands.txt"
awk '/LC_VERSION_MIN_IPHONEOS/ { remaining = 4 } remaining > 0 { print; remaining-- }' "$work/load-commands.txt"
if ! awk '
    $1 == "cmd" { version_command = ($2 == "LC_VERSION_MIN_IPHONEOS") }
    version_command && $1 == "version" && $2 == "9.0" { found = 1 }
    END { exit !found }
' "$work/load-commands.txt"; then
    echo 'FAIL: linked binary does not declare LC_VERSION_MIN_IPHONEOS 9.0.' >&2
    exit 1
fi
echo 'PASS: linked ARMv7 executable with minimum iOS 9.0. Device decoding remains unverified.'
