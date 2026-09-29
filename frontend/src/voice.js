// Voice output via the browser's speech engine (Indian-language voices where
// installed) plus a short tone per verdict: colour + icon + sound, never colour alone.
export function speak(text, locale = "en-IN") {
  if (!text || !("speechSynthesis" in window)) return false;
  window.speechSynthesis.cancel();
  const u = new SpeechSynthesisUtterance(text);
  u.lang = locale;
  const voice = window.speechSynthesis.getVoices().find((v) => v.lang === locale)
    || window.speechSynthesis.getVoices().find((v) => v.lang.startsWith(locale.slice(0, 2)));
  if (voice) u.voice = voice;
  u.rate = 0.9;
  window.speechSynthesis.speak(u);
  return true;
}

export function stopSpeaking() {
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
