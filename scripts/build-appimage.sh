#!/usr/bin/env bash
set -euo pipefail

project_root=$(cd "$(dirname "$0")/.." && pwd)
cd "$project_root"

python_bin="$project_root/.venv/bin/python"
version=$("$python_bin" -c 'from hwlogger import __version__; print(__version__)')
appimagetool_bin=${APPIMAGETOOL:-}
if [[ -z "$appimagetool_bin" ]]; then
  appimagetool_bin=$(command -v appimagetool || true)
fi
if [[ -z "$appimagetool_bin" || ! -x "$appimagetool_bin" ]]; then
  echo "appimagetool is required. Set APPIMAGETOOL=/path/to/appimagetool." >&2
  exit 2
fi
if [[ ! -x "$project_root/dist/HWlogger/HWlogger" ]]; then
  echo "PyInstaller output is missing; building it first."
  "$project_root/scripts/build-pyinstaller.sh"
fi

appdir="$project_root/build/AppDir"
rm -rf "$appdir"
cp -a "$project_root/packaging/AppDir" "$appdir"
mkdir -p "$appdir/usr/bin" "$appdir/usr/share/applications" \
  "$appdir/usr/share/icons/hicolor/scalable/apps"
cp -a "$project_root/dist/HWlogger" "$appdir/usr/bin/HWlogger"
cp "$project_root/src/hwlogger/resources/hwlogger.desktop" \
  "$appdir/HWlogger.desktop"
cp "$project_root/src/hwlogger/resources/hwlogger.desktop" \
  "$appdir/usr/share/applications/HWlogger.desktop"
cp "$project_root/src/hwlogger/resources/hwlogger.svg" "$appdir/hwlogger.svg"
cp "$project_root/src/hwlogger/resources/hwlogger.svg" \
  "$appdir/usr/share/icons/hicolor/scalable/apps/hwlogger.svg"
ln -sfn hwlogger.svg "$appdir/.DirIcon"
chmod +x "$appdir/AppRun"

if find "$appdir" -type f -name 'libnvidia-ml.so*' | grep -q .; then
  echo "Refusing to package a host NVIDIA driver library." >&2
  exit 3
fi

output="$project_root/dist/HWlogger-${version}-x86_64.AppImage"
ARCH=x86_64 "$appimagetool_bin" "$appdir" "$output"
chmod +x "$output"
echo "Built: $output"
