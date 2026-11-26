# Server test: edited copies pay only for their new seconds (paste into Claude Code on the Fedora laptop)

Pull branch `efficiency` and test the new edited-copy savings (`app/core/edits.py`). Use a CLEAN test
DB so the real `data/app.db` is untouched. Expected cost: about 63 credits (original may replay free).

1. `git fetch && git checkout efficiency && git pull`, then `python -m pytest -q` (expect 150 pass).
2. Don't stop the running bot/API. In a separate shell, with the real API (not mock):
   `DB_PATH=data/edit-e2e.db MOCK_ALETHEIA= PYTHONPATH=. python research/spikes/edit_copy_e2e.py`
   It needs `research/test-audio/spliced_whatsapp.mp3` (in git) and `~/Downloads/edit-test/1-4_*.mp3`
   (already on this laptop from the earlier diff test).
3. Expected (one JSON line per file):
   - spliced_whatsapp: partly_fake [[10.0, 14.0]]
   - 1_replace_3s_at_2s: mode excerpt, charged ~21, partly_fake incl. ~2–6 s and ~10–14 s
   - 2_insert_2s_at_18s: mode excerpt, charged ~21, partly_fake incl. a region around 16.6–22.8 s
   - 3_cut_3s_at_16s: mode cut, charged 0, partly_fake [[10.0, 14.0]]
   - 4_replace_1s_at_20s: mode excerpt, charged ~21, partly_fake [[10.0, 14.0]]
4. Edge-silence trim (only if `research/real-audio/whatsapp/` exists on this laptop; ~116 credits):
   `DB_PATH=data/edge-e2e.db MOCK_ALETHEIA= PYTHONPATH=. python research/spikes/edge_trim_e2e.py spliced_en notice_hi`
   Expect spliced_en: charged ~46 (not 49), partly_fake [[12.0, 16.0]]; notice_hi: charged ~70 (not 75), no_signs.
   Then delete `data/edge-e2e.db`.
5. `curl -s localhost:8000/health` still ok (the live server is unchanged until a restart).
6. Delete `data/edit-e2e.db` afterwards.

Report SHORT: pass/fail per file (mode, credits, band), total credits, anomalies. Tables only on failure.
Do NOT merge to master or restart the bot; the dev laptop decides after your report.
