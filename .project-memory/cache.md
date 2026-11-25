# Cache (updated 2026-11-26)
- Layers, cheapest first: Telegram file id → file sha256 → decoded-audio sha256 (lossless/container changes) → Chromaprint ≥ 0.80 + fingerprint diff → speed/tape/pitch copies (`variants.py`) → API.
- fpcalc needed for the fuzzy layers: Windows `bin/fpcalc.exe` (gitignored), Fedora `sudo dnf install chromaprint-tools`; bot log + /health warn when missing.
- Whole-clip fingerprint scores average away a few fake seconds: every fuzzy hit must pass `fpdiff.diff` (median-relative, ~2 s resolution). Edited copy → API + `edited_copy_of` + reply line; diff feeds the band (`verdict.apply_edits`). Evidence `research/fp_diff.md`, `research/false-match.md`.
- Speed/pitch copies: undo with ffmpeg, re-fingerprint; times stay the original's (`research/speed-test.md`). Detection itself is OK at 0.75–1.75×; 0.5× calls the whole clip fake, 2× unclear.
- Idempotency-Key = sha256 of the sent audio: same bytes within 24 h are free, so judge cache tests by the `via=` log line, not credits.
- Windows: never os.replace onto a file another request may open (PermissionError); use rename-no-clobber.
