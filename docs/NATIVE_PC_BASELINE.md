# Native Emerald PC baseline and validation gates

This repository is the **vanilla Emerald** native-source foundation. Emerald Expansion,
Wally's Journey, and other projects should be downstream editions, not hard dependencies.

## Imported state, verified November 11, 2026

- The imported branch `agent/prepare-v0.1.0-alpha` includes R15 content/resource work.
  It is newer than the original August 2026 upstream snapshot; **do not apply**
  the earlier Emerald PC timing POC unmodified.
- `Makefile_pc` has native `NATIVE_LINUX=1 LINUX64=1` and `WINDOWS64=1`
  build targets, plus `release-linux` and `release-windows` package targets.
- The native platform is already separated into `desktop_scheduler.c`,
  `desktop_video.c`, `desktop_input.c`, `desktop_audio.c`,
  `desktop_storage.c` and other modules.
- The previous `.github/workflows/build.yml` targeted the older GBA ROM
  compare/symbol-push workflow, not current PC binaries.

## CI acceptance gates

1. Execute ROM-free tests:
   `tests/run_emerald_resource_lz.sh` and
   `tests/run_emerald_rom_base_provider.sh`.
2. Build/package Linux x64 with `make -f Makefile_pc release-linux -j2`;
   require an ELF64 executable and nonempty release archive.
3. Cross-compile/package Windows x64 with
   `make -f Makefile_pc release-windows -j2`; require a PE x86-64
   executable and nonempty release ZIP.
4. Upload archives as short-lived GitHub Actions artifacts.
5. Do not upload Nintendo ROM/BIOS files, extracted game assets,
   user saves, or profiles as CI artifacts.

**A successful build is not a gameplay-verified release.** CI runs must first
complete before claiming the build works. Build failures are diagnostic data
and must be fixed rather than bypassed.

## High-FPS design: keep gameplay timing authentic

GBA video cadence is 16,777,216 / 280,896 = approximately 59.7275 Hz.
The existing PC loop uses nominal 60 Hz (`fixedTimestep` and
`PacePresentation`); the audio scheduler also uses 60 Hz. Audit all
three before changing any one.

The desired architecture is fixed-rate simulation with independently
timed PC presentation. Additional visual frames should interpolate
**semantic game objects** (camera, characters, sprites, animation
transforms), not blend adjacent 240x160 framebuffers.

Important cases to test: teleports, camera snapping, map changes,
fades, sprite creation/removal, save-state loading, pause, battle
animations, 1-5x speed, music, input, RTC, and scripts.

Presenting a static texture at 144 Hz is **not** true 144 FPS motion.
Do not claim interpolation until its implementation and tests exist.

## Gameplay qualification

After the first green CI build, verify the packaged game manually
against a legally obtained compatible Emerald ROM: startup/import,
menus, overworld movement, battle progression, audio, controls, RTC,
normal save/load, cross-process save states, and speed modes.

Keep imported/default branch unchanged until the proposed CI change
has been reviewed and tested.
