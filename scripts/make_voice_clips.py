"""Generate pre-recorded voice clips for the fixed messages (playbook section 10).

Writes frontend/public/audio/<lang>/<key>.mp3 for every message without {placeholders}
(verdict headlines, gear, colours, SOS lines). The app plays these when present and
falls back to the phone's text-to-speech otherwise, so clips also work offline.

Engines (pick one):
  --engine gtts       pip install gTTS            (needs internet while generating)
  --engine command    any CLI, e.g. an AI4Bharat Indic TTS model:
                      --cmd "python infer.py --lang {lang} --text {text} --out {out}"
Listen to every clip with a native speaker before the demo.
"""
from __future__ import annotations

import argparse
import json
import shlex
import subprocess
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
I18N = ROOT / "backend" / "app" / "i18n"
OUT = ROOT / "frontend" / "public" / "audio"
GTTS_LANG = {"en": "en", "hi": "hi", "mr": "mr", "pa": "pa", "te": "te"}
PREFIXES = ("verdict.", "gear.", "colour.", "sos.", "red_confirm", "weather.ok", "rotation.ok", "toxicity_stacking")


def fixed_messages(lang: str) -> dict[str, str]:
    table = json.loads((I18N / f"{lang}.json").read_text(encoding="utf-8"))
    return {k: v for k, v in table.items() if k.startswith(PREFIXES) and "{" not in v}


def main() -> None:
    ap = argparse.ArgumentParser()
    ap.add_argument("--engine", choices=["gtts", "command"], default="gtts")
    ap.add_argument("--cmd", help="command template with {lang} {text} {out}")
    ap.add_argument("--langs", default="en,hi,mr,pa,te")
    a = ap.parse_args()
    for lang in a.langs.split(","):
        (OUT / lang).mkdir(parents=True, exist_ok=True)
        for key, text in fixed_messages(lang).items():
            out = OUT / lang / f"{key}.mp3"
            if a.engine == "gtts":
                from gtts import gTTS  # type: ignore

                gTTS(text=text, lang=GTTS_LANG[lang]).save(str(out))
            else:
                subprocess.run(shlex.split(a.cmd.format(lang=lang, text=shlex.quote(text), out=out)), check=True)
            print(out.relative_to(ROOT))


if __name__ == "__main__":
    main()
