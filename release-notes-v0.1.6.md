# HWlogger v0.1.6

HWlogger 0.1.6 improves live monitoring, window behavior, and reliability on
Linux desktops.

## Main changes

- Temperature Current and Maximum cells now use warning colors with hysteresis.
- Graphs with incompatible units use independent Y scales while sharing one
  synchronized time axis.
- Graph history grows from left to right and begins scrolling after the selected
  time window fills.
- Graph areas are created only for active groups, and line colors remain stable.
- Invalid or unavailable graph readings no longer create false zero values.
- A system tray provides show, hide, and full-exit actions, including
  double-click restoration and KDE-compatible activation.
- Closing the window can hide HWlogger in the tray while polling and recording
  continue.
- Window geometry, maximized state, active tab, polling interval, and selected
  graph sensors are restored across launches.

## Reliability fixes

- Full exit works correctly even when the main window is already hidden.
- Active recordings are finalized before shutdown.
- Missing optional sensors and disconnected monitors are handled safely during
  state restoration.
- Invalid individual configuration fields fall back without discarding other
  valid settings.

## Downloads

- `HWlogger-0.1.6-x86_64.AppImage` — portable AppImage.
- `HWlogger-0.1.6-linux-x86_64.tar.gz` — standalone one-folder build.
- `SHA256SUMS` — checksums for both artifacts.

## Running

For the AppImage:

```bash
chmod +x HWlogger-0.1.6-x86_64.AppImage
./HWlogger-0.1.6-x86_64.AppImage
```

For the tar.gz build:

```bash
tar -xzf HWlogger-0.1.6-linux-x86_64.tar.gz
./HWlogger/HWlogger
```

## Known limitations

- Linux x86_64 GUI is the only supported platform.
- Optional readings depend on hardware, kernel drivers, NVIDIA drivers, and
  host permissions.
- Some devices do not expose every temperature, power, or fan sensor.
- The interface is currently available in Russian only.
