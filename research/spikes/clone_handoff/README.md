# Voice-clone handoff (for the GPU laptop)

**Goal:** make 6 AI-cloned audio files of our own (consented) voice, so we can test whether
Aletheia catches them. You run one file, check the results by ear, and send back one zip.

Time: about 30–60 min, mostly downloads (about 10 GB). Needs internet.

---

## What's in this folder

| File | What it is |
|---|---|
| `README.md` | These instructions |
| `setup_and_run.bat` | **Double-click this.** Installs everything and makes the 6 files |
| `clone_local.py` | The script the .bat runs (two models: Chatterbox and IndicF5) |
| `texts.json` | The sentences the clone will say, plus the words spoken in each reference clip |
| `refs/ref_en.wav`, `ref_hi.wav`, `ref_kn.wav` | About 10 s of the real voice in each language. The models copy this voice |
| `output/` | Empty. The 6 clone files appear here |

**Consent:** this is our own teammate's voice, recorded with permission, for testing only.
Don't use these files for anything else, and delete this folder from the GPU laptop when done.

---

## Step 1. Check the laptop has what it needs

- [ ] An **NVIDIA** graphics card with 6 GB or more of graphics memory
- [ ] **Python 3.11** (python.org; tick "Add python.exe to PATH" when installing)
- [ ] **Git for Windows** (git-scm.com)
- [ ] About **10 GB** of free disk space

## Step 2. Check the reference text (2 minutes, important for Hindi and Kannada)

IndicF5 needs the exact words spoken in each reference clip.

1. Play `refs/ref_hi.wav` and read along with `"ref_text"` under `"hi"` in `texts.json`.
2. Do the same for `refs/ref_kn.wav` and `"kn"`.
3. If the clip stops earlier or later than the text, edit the text in `texts.json` so it matches
   **word for word**. Save the file.

(The English one doesn't matter; Chatterbox doesn't use it.)

## Step 3. Run it

Double-click **`setup_and_run.bat`**.

- Part 1 makes `clone_en.wav` and `fake_sentence_en.wav` (Chatterbox).
- Part 2 makes the Hindi and Kannada files (IndicF5).
- The first run downloads the models; this takes the longest.

## Step 4. Listen to the 6 files in `output/`

| File | Should say |
|---|---|
| `clone_en.wav` | The full apartment water notice, in English |
| `fake_sentence_en.wav` | "The association also said everyone must send five hundred rupees…" |
| `clone_hi.wav` / `fake_sentence_hi.wav` | The same in Hindi |
| `clone_kn.wav` / `fake_sentence_kn.wav` | The same in Kannada |

Write one line per file in `output/notes.txt`: does it sound like the real person (yes / sort of /
no), and is anything garbled? If a file sounds bad, run the .bat again; each run comes out a
little different.

## Step 5. Send it back

Right-click the `output` folder → **Send to → Compressed (zipped) folder** → name it
`clones_return.zip` → send it back (USB, Drive or email; **not WhatsApp**, it re-compresses audio).

---

## If something fails

- **"CPU-only torch got installed" / "No CUDA GPU":** update the NVIDIA driver, then delete the
  `venv-chatterbox` or `venv-indicf5` folder and run the .bat again.
- **IndicF5 asks for a login or says "gated" / 401:** make a free account on huggingface.co, open
  the page `huggingface.co/ai4bharat/IndicF5`, accept the terms, then in a terminal run
  `venv-indicf5\Scripts\huggingface-cli login`, paste a read token, and run the .bat again.
- **Only one model works:** fine. Send back whatever is in `output/` plus `output/log.txt`.
- **Anything else:** if this laptop has Claude Code, open this folder in it and say
  "Read README.md and get setup_and_run.bat working". Otherwise send back `output/log.txt` and a
  screenshot of the error.
