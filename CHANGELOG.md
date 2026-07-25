# Changelog

All notable changes follow semantic versioning.

## [0.1.6] - 2026-07-26

### Added

- Temperature warning colors for the Current and Maximum cells, with
  independent hysteresis and theme-readable critical levels.
- Dynamic graph areas with independent Y scales for incompatible sensor types
  and units, stable line colors, and synchronized time axes.
- A system tray with show, hide, full-exit, double-click, and KDE activation
  support, plus a configurable close-to-tray option.
- Persistence for window geometry, maximized state, active tab, polling
  interval, and selected graph sensors.

### Fixed

- Graph time now grows from left to right before the history window fills and
  scrolls correctly after it fills.
- Empty graph groups are removed, while `None`, NaN, and infinite readings are
  ignored without producing false zero values.
- Full shutdown now reliably exits from an already hidden tray window and
  finalizes active recordings without leaving worker threads or processes.
- Saved interface state is restored safely when monitors or optional sensors
  disappear, with invalid configuration fields falling back independently.
- Expanded regression, lifecycle, resource, and GUI smoke-test coverage.

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
