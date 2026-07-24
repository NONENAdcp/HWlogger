# HWlogger

HWlogger — read-only Linux monitor for live hardware sensors and CSV recording.

Version 0.1.0 currently implements the first development milestone: Linux hwmon,
CPU/RAM/system sensors, optional NVIDIA NVML, sensor selection, online statistics,
CSV sessions, automatic summaries, and basic persistent settings.

## Development

```bash
./scripts/install-dev.sh
./scripts/run-dev.sh
```

Logs default to `~/HWLogs`; configuration uses
`~/.config/hwlogger/config.json`. HWlogger never writes to sysfs and does not
require root.

## Privacy and security

All readings and logs stay local. Do not run HWlogger as root. Report security
issues privately to the repository owner once the GitHub URL is configured.

License: GPL-3.0-or-later.
