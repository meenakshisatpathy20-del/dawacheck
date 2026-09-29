// On-device label / bill reading (playbook section 10: "Google ML Kit text recognition" on the phone).
// Used when the server has no OCR engine and no vision model (e.g. Vercel without an API key).
// Tesseract runs in the browser as WebAssembly; its files are served by this app (public/ocr/).
let workerPromise = null;

function getWorker() {
  if (!workerPromise) {
    const base = `${import.meta.env.BASE_URL}ocr`;
    workerPromise = import("tesseract.js").then(({ createWorker }) =>
      createWorker("eng", 1, {
        workerPath: `${base}/worker.min.js`,
        corePath: base,
        langPath: base,
        gzip: true,
      }));
    workerPromise.catch(() => { workerPromise = null; });
  }
  return workerPromise;
}

export async function readOnDevice(image) {
  const worker = await getWorker();
  const { data } = await worker.recognize(image);
  return (data.text || "").trim();
}
