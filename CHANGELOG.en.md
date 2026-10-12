# Update history

[한국어](CHANGELOG.md) | [English](CHANGELOG.en.md) | [简体中文](CHANGELOG.zh-CN.md) | [繁體中文](CHANGELOG.zh-TW.md) | [日本語](CHANGELOG.ja.md)

Dates use Korea time (Asia/Seoul), newest first. Add one entry per commit under its date. This history starts with the changes included in the current dev → main merge. Detailed evidence is in `.ai/worklogs/`.

## 2026-10-12

### Improve recording shutdown boundaries and output diagnostics

Finish the last segment and checkpoint before closing FFmpeg input on normal stop, app exit, or task cancellation. Distinguish already-output segments from actual buffer limits, and fail reports and CI on corrupt packets, incomplete input, or forced termination. All 126 tests and real video/audio/PTS checks passed. Native Windows shutdown and overseas live recording remain follow-up validation.

### Update history and recording analysis

Added five-language histories, README links, and a rule to update them with every commit. The domestic VPS video passed decoding and PTS checks. Overseas continuity logs also passed, but Windows shutdown corruption warnings and unavailable overseas media remain follow-up checks.

## 2026-10-11

### Register dev recording tests on main (9ce5929)

Registered manual inputs on main and connected them to dev code at that time. After the merge, tests will check the branch selected for execution.

### Select recording test platforms and channels (8557299)

Added channel and Linux/Windows/macOS selection, latest stable runner images, and a shared test runner. Retained environment versions and diagnostic evidence while preserving video cleanup.

### Preserve follow-up segments during recovery (a32e59a)

Preserved known segment addresses and subsequent complete segments, separating reception from output waits. Added 120-second/256MiB disk buffering, handoff across restarts of the same broadcast and quality, URL-free diagnostics, and code hashes.

### Preserve stalled positions and check CI continuity (b19bc17)

Retained actual output checkpoints and recovery deadlines across restarts. CI fails on gaps, duplicates, unresolved transitions, or incomplete evidence. Five-minute splitting and video cleanup remain enabled.

### Prefer Korean LL-HLS and validate Akamai (50424e5)

Prefer Korean current/history paths and use an Akamai standby only after validating equivalent media. Validate PART groups before output and replace incomplete groups with whole segments.

## 2026-10-10

### Retain HLS recovery positions across restarts (974c512)

Preserved broadcast start and recovery positions. Connected previous-hour recording and file-boundary handling to the CLI and GUI.

### Improve Fcitx input on KDE Wayland (2961cd4)

Prefer native Wayland input in this environment, preserving other environments and explicit settings. Actual Korean composition still requires user verification.

### Display continuity logs in local time (3e87676)

Show the local timezone and UTC offset in recovery and gap messages, retaining original event and cursor timestamps.

### Document issue #82 work (b4cf13b)

Recorded implementation, validation, and verified dev publication in `.ai` worklogs.

### Recover missing segments across advertised CDNs (868dc58)

Strengthened HLS segment ordering and validation, recovering missing segments through advertised CDN paths. If recovery fails, continue in a new file and record confirmed gaps.
