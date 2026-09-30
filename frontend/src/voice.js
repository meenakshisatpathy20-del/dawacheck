// Voice output via the browser's speech engine (Indian-language voices where
// installed) plus a short tone per verdict: colour + icon + sound, never colour alone.
// Marathi is written in Devanagari, so a Hindi voice can read it when no Marathi voice is installed.
const FALLBACK_VOICE = { "mr-IN": "hi-IN" };

function findVoice(locale) {
  const voices = window.speechSynthesis.getVoices();
  return voices.find((v) => v.lang === locale) || voices.find((v) => v.lang.startsWith(locale.slice(0, 2)));
}

export function speak(text, locale = "en-IN") {
  if (!text || !("speechSynthesis" in window)) return false;
  window.speechSynthesis.cancel();
  const u = new SpeechSynthesisUtterance(text);
  u.lang = locale;
  const voice = findVoice(locale) || (FALLBACK_VOICE[locale] && findVoice(FALLBACK_VOICE[locale]));
  // No voice for this language on the phone (voice list loaded but empty for it): stay silent rather
  // than read Telugu or Punjabi with an English voice. The text is on screen and the tone still plays.
  if (!voice && window.speechSynthesis.getVoices().length && !locale.startsWith("en")) return false;
  if (voice) u.voice = voice;
  u.rate = 0.9;
  window.speechSynthesis.speak(u);
  return true;
}

// Pre-recorded clips (playbook section 10: "pre-recorded or TTS for templated messages"):
// public/audio/<lang>/<message_key>.mp3 is played when present; it works offline once cached.
// Generate them with scripts/make_voice_clips.py. Anything without a clip is spoken by TTS.
let clipAudio = null;
let manifest = null;
function clipList() {
  manifest = manifest || fetch(`${import.meta.env.BASE_URL}audio/manifest.json`)
    .then((r) => (r.ok ? r.json() : {})).catch(() => ({}));
  return manifest;
}

export async function playClip(lang, key) {
  const list = await clipList();
  if (!(list[lang] || []).includes(key)) return false;
  return new Promise((resolve) => {
    const a = new Audio(`${import.meta.env.BASE_URL}audio/${lang}/${key}.mp3`);
    clipAudio = a;
    a.onended = () => resolve(true);
    a.onerror = () => resolve(false);
    a.play().catch(() => resolve(false));
  });
}

export async function speakVerdict({ verdict, lang, locale, rest, headline }) {
  const played = await playClip(lang, `verdict.${verdict}`);
  speak(played ? rest : [headline, rest].filter(Boolean).join(" "), locale);
}

export function stopSpeaking() {
  if (clipAudio) clipAudio.pause();
  if ("speechSynthesis" in window) window.speechSynthesis.cancel();
}

const TONES = { green: [660, 880], yellow: [520, 520], red: [330, 220], grey: [440] };

export function verdictTone(verdict) {
  try {
    const ctx = new (window.AudioContext || window.webkitAudioContext)();
    (TONES[verdict] || [440]).forEach((f, i) => {
      const o = ctx.createOscillator();
      const g = ctx.createGain();
      o.frequency.value = f;
      o.type = verdict === "red" ? "square" : "sine";
      g.gain.setValueAtTime(0.15, ctx.currentTime + i * 0.25);
      g.gain.exponentialRampToValueAtTime(0.001, ctx.currentTime + i * 0.25 + 0.22);
      o.connect(g).connect(ctx.destination);
      o.start(ctx.currentTime + i * 0.25);
      o.stop(ctx.currentTime + i * 0.25 + 0.24);
    });
  } catch { /* audio blocked until the user taps; the voice still plays */ }
}

// Voice input: "kapas, sundi" -> crop + pest via the synonyms the backend knows.
export function listen(locale, onText) {
  const SR = window.SpeechRecognition || window.webkitSpeechRecognition;
  if (!SR) return null;
  const r = new SR();
  r.lang = locale;
  r.interimResults = false;
  r.onresult = (e) => onText(e.results[0][0].transcript);
  r.start();
  return r;
}
