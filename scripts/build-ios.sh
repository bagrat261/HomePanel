#!/bin/sh
set -eu
root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
sh "$root/scripts/check-ios-toolchain.sh"
sdk=${HOMEPANEL_IOS_SDK:-$(xcrun --sdk iphoneos --show-sdk-path)}
out="$root/ios/build"
stage=$(mktemp -d "${TMPDIR:-/tmp}/homepanel-package.XXXXXX")
trap 'rm -rf -- "$stage"' EXIT HUP INT TERM
app="$stage/Payload/HomePanel.app"
mkdir -p "$app" "$out"
clang=$(xcrun --find clang)
"$clang" -arch armv7 -isysroot "$sdk" -miphoneos-version-min=9.0 \
    -fobjc-arc -O2 -Wall -Wextra -Werror=unguarded-availability \
    "$root/ios/HomePanel/"*.m "$root/ios/HomePanel/HPAnnexB.c" \
    -framework UIKit -framework Foundation -framework AVFoundation \
    -framework CoreMedia -framework QuartzCore -framework CoreGraphics -o "$app/HomePanel"
cp "$root/ios/HomePanel/Info.plist" "$app/Info.plist"
plutil -lint "$app/Info.plist"
xcrun lipo -verify_arch armv7 "$app/HomePanel"
xcrun otool -l "$app/HomePanel" > "$out/load-commands.txt"
xcrun otool -L "$app/HomePanel" > "$out/linked-libraries.txt"
file "$app/HomePanel"
(cd "$stage" && /usr/bin/zip -qr "$out/HomePanel-armv7-jailbreak-unsigned.ipa" Payload)
printf 'Built unsigned jailbreak IPA: %s\n' "$out/HomePanel-armv7-jailbreak-unsigned.ipa"
shasum -a 256 "$out/HomePanel-armv7-jailbreak-unsigned.ipa"
