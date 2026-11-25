"""Make consented voice clones for the Aletheia accuracy test.

  python clone_local.py en      # Chatterbox, English   (run inside venv-chatterbox)
  python clone_local.py indic   # IndicF5, Hindi+Kannada (run inside venv-indicf5)

Reads refs/ref_<lang>.wav + texts.json, writes output/<name>_<lang>.wav.
"""
import json
import sys
import time
from pathlib import Path

HERE = Path(__file__).resolve().parent
REFS, OUT = HERE / "refs", HERE / "output"
TEXTS = json.loads((HERE / "texts.json").read_text(encoding="utf-8"))
OUT.mkdir(exist_ok=True)


def log(msg: str) -> None:
    print(msg)
    with open(OUT / "log.txt", "a", encoding="utf-8") as f:
        f.write(f"{time.strftime('%H:%M:%S')} {msg}\n")


def check_gpu():
    import torch
    if not torch.cuda.is_available():
        sys.exit("No CUDA GPU visible to PyTorch. Re-run the setup step that installs the CUDA build of torch.")
    log(f"torch {torch.__version__}, GPU: {torch.cuda.get_device_name(0)}")


def run_chatterbox() -> None:
    import torchaudio
    from chatterbox.tts import ChatterboxTTS
    check_gpu()
    model = ChatterboxTTS.from_pretrained(device="cuda")
    for kind in ("clone", "fake_sentence"):
        t = time.time()
        wav = model.generate(TEXTS["en"][kind], audio_prompt_path=str(REFS / "ref_en.wav"))
        path = OUT / f"{kind}_en.wav"
        torchaudio.save(str(path), wav, model.sr)
        log(f"chatterbox wrote {path.name} in {time.time() - t:.1f}s")


def run_indicf5() -> None:
    import numpy as np
    import soundfile as sf
    from transformers import AutoModel
    check_gpu()
    model = AutoModel.from_pretrained("ai4bharat/IndicF5", trust_remote_code=True).to("cuda")
    for lang in ("hi", "kn"):
        for kind in ("clone", "fake_sentence"):
            t = time.time()
            audio = model(TEXTS[lang][kind], ref_audio_path=str(REFS / f"ref_{lang}.wav"),
                          ref_text=TEXTS[lang]["ref_text"])
            audio = np.asarray(audio)
            if audio.dtype == np.int16:
                audio = audio.astype(np.float32) / 32768.0
            path = OUT / f"{kind}_{lang}.wav"
            sf.write(str(path), audio.astype(np.float32), samplerate=24000)
            log(f"indicf5 wrote {path.name} in {time.time() - t:.1f}s")


if __name__ == "__main__":
    which = sys.argv[1] if len(sys.argv) > 1 else ""
    if which == "en":
        run_chatterbox()
    elif which == "indic":
        run_indicf5()
    else:
        sys.exit(__doc__)
    log("done: " + ", ".join(sorted(p.name for p in OUT.glob("*.wav"))))
