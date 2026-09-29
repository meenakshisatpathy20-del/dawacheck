import jsQR from "jsqr";
import { useEffect, useRef, useState } from "react";
import { useStore } from "../store.jsx";
import { t } from "../strings.js";

// Live camera with a guide box (playbook screen 3): QR codes are detected
// automatically; "Take photo" captures the label for OCR. Falls back to the
// phone's photo picker when the camera cannot be opened.
export default function Camera({ onQr, onPhoto, busy }) {
  const { lang } = useStore();
  const video = useRef(null);
  const canvas = useRef(null);
  const file = useRef(null);
  const done = useRef(false);
  const [live, setLive] = useState(false);
  const [err, setErr] = useState(null);

  useEffect(() => {
    let stream;
    let timer;
    const detector = "BarcodeDetector" in window ? new window.BarcodeDetector({ formats: ["qr_code"] }) : null;
    (async () => {
      try {
        stream = await navigator.mediaDevices.getUserMedia({
          video: { facingMode: "environment", width: { ideal: 1920 }, height: { ideal: 1080 } }, audio: false });
        video.current.srcObject = stream;
        await video.current.play();
        setLive(true);
        timer = setInterval(async () => {
          const v = video.current;
          if (done.current || !v || v.readyState < 2) return;
          let text = null;
          if (detector) {
            try { text = (await detector.detect(v))[0]?.rawValue || null; } catch { /* keep trying */ }
          } else {
            const c = canvas.current;
            c.width = v.videoWidth; c.height = v.videoHeight;
            const ctx = c.getContext("2d", { willReadFrequently: true });
            ctx.drawImage(v, 0, 0);
            const img = ctx.getImageData(0, 0, c.width, c.height);
            text = jsQR(img.data, img.width, img.height, { inversionAttempts: "dontInvert" })?.data || null;
          }
          if (text) {
            done.current = true;
            if (navigator.vibrate) navigator.vibrate(80);
            onQr(text, await frameBlob());
          }
        }, 350);
      } catch {
        setErr(t(lang, "cameraOff"));
      }
    })();
    return () => { clearInterval(timer); stream?.getTracks().forEach((tr) => tr.stop()); };
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  const frameBlob = () => new Promise((resolve) => {
    const v = video.current;
    const c = canvas.current;
    c.width = v.videoWidth; c.height = v.videoHeight;
    c.getContext("2d").drawImage(v, 0, 0);
    c.toBlob(resolve, "image/jpeg", 0.9);
  });

  const snap = async () => {
    if (!live) { file.current.click(); return; }
    done.current = true;
    onPhoto(await frameBlob());
  };

  return (
    <div>
      <div className="camera">
        <video ref={video} playsInline muted />
        {live && <div className="guide" aria-hidden><span /></div>}
        {!live && <div className="camera-off">{err || "📷"}</div>}
        <p className="camera-hint">{t(lang, "pointCamera")}</p>
      </div>
      <canvas ref={canvas} hidden />
      <input ref={file} type="file" accept="image/*" capture="environment" hidden
        onChange={(e) => e.target.files?.[0] && onPhoto(e.target.files[0])} />
      <button className="btn block" style={{ marginTop: 10 }} disabled={busy} onClick={snap}>📸 {t(lang, "takePhoto")}</button>
    </div>
  );
}
