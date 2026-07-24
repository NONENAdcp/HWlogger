#!/usr/bin/env bash
set -euo pipefail

project_root=$(cd "$(dirname "$0")/.." && pwd)
cd "$project_root"

if [[ -n "${VIRTUAL_ENV:-}" ]]; then
  python_bin=python
elif [[ -x "$project_root/.venv/bin/python" ]]; then
  python_bin="$project_root/.venv/bin/python"
else
  python_bin=python
fi

if ! "$python_bin" -c 'import PyInstaller' >/dev/null 2>&1; then
  echo "PyInstaller is missing from the active Python environment." >&2
  echo "Install requirements-dev.txt before building." >&2
  exit 1
fi

version=$("$python_bin" -c 'from hwlogger import __version__; print(__version__)')
architecture=$(uname -m)
if [[ "$architecture" != "x86_64" ]]; then
  echo "Warning: this release script is intended for x86_64, found $architecture." >&2
fi

"$python_bin" -m PyInstaller --noconfirm --clean packaging/hwlogger.spec
cp "$project_root/LICENSE" "$project_root/dist/HWlogger/LICENSE"
cp "$project_root/README.md" "$project_root/dist/HWlogger/README.md"
cp "$project_root/src/hwlogger/resources/hwlogger.desktop" \
  "$project_root/dist/HWlogger/hwlogger.desktop"
cp "$project_root/src/hwlogger/resources/hwlogger.svg" \
  "$project_root/dist/HWlogger/hwlogger.svg"

smoke_root=$(mktemp -d /tmp/hwlogger-built-smoke-XXXXXX)
cleanup() {
  rm -rf "$smoke_root"
}
trap cleanup EXIT

XDG_CONFIG_HOME="$smoke_root/config" \
XDG_STATE_HOME="$smoke_root/state" \
XDG_CACHE_HOME="$smoke_root/cache" \
HOME="$smoke_root/home" \
QT_QPA_PLATFORM=offscreen \
HWLOGGER_SMOKE_TEST=1 \
timeout 20s "$project_root/dist/HWlogger/HWlogger"

archive="$project_root/dist/HWlogger-${version}-linux-x86_64.tar.gz"
tar -C "$project_root/dist" -czf "$archive" HWlogger
echo "Built: $project_root/dist/HWlogger"
echo "Archive: $archive"
