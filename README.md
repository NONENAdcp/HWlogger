# HWlogger

HWlogger is a read-only Linux hardware sensor monitor, recorder, and log
analysis application built with Python, PySide6, and pyqtgraph.

> **Platform status:** Linux only. Version 0.1.5 is an early release intended
> for testing on current x86_64 Linux distributions under Wayland or X11.

![Sensors tab placeholder](docs/screenshots/sensors.png)
![Graphs tab placeholder](docs/screenshots/graphs.png)
![Logs tab placeholder](docs/screenshots/logs.png)

## Features

- Live discovery and display of Linux hardware sensors.
- Sensor selection and UTF-8 CSV recording.
- Online minimum, average, and maximum statistics without retaining the full
  recording in memory.
- Automatic temperature, power, and fan summaries.
- Streaming analysis of complete recordings or selected time intervals.
- Bounded live graphs for up to eight sensors.
- Safe handling of unavailable sensors and optional NVIDIA GPUs.
- Atomic configuration writes and XDG-compatible application directories.
- No root privileges required for normal operation.

## Sensor sources

- Linux hwmon (`/sys/class/hwmon`) for temperatures, fans, power, energy,
  voltage, current, and supported frequency inputs.
- `psutil` for CPU utilization, frequencies, load averages, RAM, swap, and
  uptime.
- Intel RAPL power domains when readable.
- NVIDIA NVML through `nvidia-ml-py`. GPU wake-up polling is disabled by
  default.

HWlogger never writes to sysfs and does not change clock frequencies, fan
controls, or power limits.

## Requirements

- Linux x86_64
- Python 3.11 or newer when running from source
- A readable `/sys` and `/proc`
- Optional: an installed NVIDIA driver for NVML sensors

## AppImage installation

Download `HWlogger-0.1.5-x86_64.AppImage` from the Releases page:

```bash
chmod +x HWlogger-0.1.5-x86_64.AppImage
./HWlogger-0.1.5-x86_64.AppImage
```

The AppImage does not bundle an NVIDIA driver. It uses NVML from the host
driver when available.

## Running from source

```bash
git clone https://github.com/NONENAdcp/HWlogger.git
cd HWlogger
./scripts/install-dev.sh
./scripts/run-dev.sh
```

All Python packages are installed into the project-local `.venv`.

## Development

```bash
.venv/bin/pytest -q
.venv/bin/ruff check .
HWLOGGER_FAKE_SENSORS=1 ./scripts/run-dev.sh
HWLOGGER_SMOKE_TEST=1 ./scripts/run-dev.sh
```

`HWLOGGER_FAKE_SENSORS=1` replaces host sensors with deterministic test
sensors. `HWLOGGER_SMOKE_TEST=1` also closes the application automatically.

## PyInstaller build

The primary standalone format is a one-folder build:

```bash
./scripts/build-pyinstaller.sh
```

Outputs:

```text
dist/HWlogger/
dist/HWlogger-0.1.5-linux-x86_64.tar.gz
```

The executable runs without a system Python or the development virtual
environment.

## AppImage build

First build the PyInstaller application, then provide `appimagetool`:

```bash
./scripts/build-pyinstaller.sh
./scripts/build-appimage.sh
```

Output:

```text
dist/HWlogger-0.1.5-x86_64.AppImage
```

Set `APPIMAGETOOL=/path/to/appimagetool` when it is not available in `PATH`.
GitHub Actions can build the AppImage without installing tools on the host.

## Data locations

HWlogger follows XDG Base Directory variables where applicable:

| Data | Default location |
|---|---|
| Raw logs and summaries | `~/HWLogs` |
| Configuration | `~/.config/hwlogger/config.json` |
| Application log | `~/.local/state/hwlogger/hwlogger.log` |
| Cache | `~/.cache/hwlogger` |

A recording normally contains:

```text
hwlog_YYYY-MM-DD_HH-MM-SS.csv
hwlog_YYYY-MM-DD_HH-MM-SS.json
hwlog_YYYY-MM-DD_HH-MM-SS_summary.csv
```

## Known limitations

- Linux is the only supported operating system.
- Release builds are architecture-specific.
- Sensor availability and labels depend on the kernel driver and firmware.
- Unknown ThinkPad EC sensors are deliberately shown with neutral names.
- Some NVIDIA metrics are unsupported on specific GPUs or driver versions.
- NVIDIA fallback coverage is currently more limited than NVML coverage.
- Mixed graph units share one plot and are accompanied by a warning.

## Privacy

HWlogger performs no telemetry, analytics, network upload, or cloud
synchronization. Sensor readings, configuration, and recordings remain on the
local computer unless the user copies them elsewhere.

## Security

HWlogger is a read-only monitor. It does not require root, write to sysfs,
control fans, modify clocks, or change power limits. Open files and directories
are passed to the desktop environment using Qt.

Please report security issues privately to the repository owner after the
placeholder repository URL has been replaced.

## Reporting bugs

Open a GitHub issue using the bug report template. Include the Linux
distribution, Wayland/X11 environment, HWlogger version, hardware, installation
method, reproduction steps, and relevant lines from
`~/.local/state/hwlogger/hwlogger.log`. Remove sensitive information first.

## License

HWlogger is licensed under **GPL-3.0-or-later**. See [LICENSE](LICENSE).
