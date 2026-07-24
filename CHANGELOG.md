# Changelog

All notable changes follow semantic versioning.

## [0.1.5] - Unreleased

### Added

- Linux hwmon, psutil, Intel RAPL, and optional NVIDIA NVML sensor sources.
- Background polling and live sensor statistics.
- UTF-8 CSV recording, JSON metadata, and automatic summaries.
- Streaming interval analysis and bounded CSV preview.
- Live pyqtgraph graphs for up to eight sensors.
- Atomic XDG configuration and deterministic fake/smoke-test modes.
- PyInstaller, AppImage, and GitHub Actions release infrastructure.

### Fixed

- Fast, bounded application shutdown with ordered timer and worker cleanup.
- GUI polling updates and sensor table scrolling.
- Portable paths and standalone Linux release resources.
