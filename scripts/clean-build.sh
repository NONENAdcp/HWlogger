#!/usr/bin/env bash
set -euo pipefail

project_root=$(cd "$(dirname "$0")/.." && pwd)
rm -rf "$project_root/build/hwlogger"
rm -rf "$project_root/build/AppDir"
rm -rf "$project_root/dist/HWlogger"
rm -f "$project_root"/dist/HWlogger-*-linux-x86_64.tar.gz
rm -f "$project_root"/dist/HWlogger-*-x86_64.AppImage
echo "HWlogger build artifacts removed."
