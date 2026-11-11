# Native PC continuous-integration guide

The default branch remains unchanged until the native Windows and Linux builds
are proven. Work on `feature/native-desktop-ci` and review
[Pull Request #1](https://github.com/Treston12360/Emerald-PC-Engine/pull/1).

## First-time GitHub Actions setup

For a repository imported through GitHub Importer, Actions may be disabled by
default and older workflow commits do not necessarily trigger retroactive runs.
Enable workflows on the repository's **Actions** page. A new branch commit then
triggers the `.github/workflows/build.yml` workflow; the workflow also supports
manual **Run workflow** dispatch.

## Acceptance checklist

- `core-tests`: executes ROM-free LZ and ROM-base compatibility suites.
- `linux-x64`: builds and uploads an ELF64 executable archive.
- `windows-x64`: cross-compiles and uploads a PE x64 executable archive.
- If a job fails, inspect its failing command and fix the code/toolchain or
  the runner's dependencies. Never label a job successful solely because the
  workflow parsed.
- Keep build artifacts ROM-free; the player supplies their own original
  Pokémon Emerald ROM through the launcher.
- Once all jobs are green, perform actual boot/gameplay testing. CI compilation
  alone does not establish the original game is fully playable.

## Stable source branch

This imported repository's base branch is
`agent/prepare-v0.1.0-alpha` at an R15 source-port milestone.
The older upstream `TPizzle1996/pokeemerald-recomp` snapshots have different
file layouts; do not apply earlier proof-of-concept patches blindly.

## Future improvements

After initial CI succeeds, establish determinism tests for game simulation
timing and save compatibility, then implement presentation-only 120/144/240 Hz
visual interpolation behind an opt-in setting. Keeping original gameplay
and user data correct is required before changing frame scheduling.
