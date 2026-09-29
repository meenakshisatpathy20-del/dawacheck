// Builds docs/DawaCheck_pitch.pptx (playbook section 15: ten slides, one idea per slide).
// Run: cd docs/deck && npm install && node build_deck.js
const pptxgen = require("pptxgenjs");

const C = {
  forest: "14532D", green: "1F7A3A", mint: "E3F3E7", amber: "A86A00", amberBg: "FFF2CF",
  red: "B3261E", redBg: "FDE4E1", ink: "1D231F", muted: "5D665F", line: "D6DDD7", white: "FFFFFF", paper: "F7FAF7",
};
const HEAD = "Cambria";
const BODY = "Calibri";

const pres = new pptxgen();
pres.layout = "LAYOUT_16x9"; // 10 x 5.625 in
pres.title = "DawaCheck pitch";

const text = (slide, t, o) => slide.addText(t, { fontFace: BODY, color: C.ink, margin: 0, isTextBox: true, ...o });
const title = (slide, t, o = {}) => text(slide, t, { x: 0.5, y: 0.35, w: 9, h: 0.7, fontFace: HEAD, fontSize: 30, bold: true, ...o });
const source = (slide, t, dark = false) =>
  text(slide, t, { x: 0.5, y: 5.2, w: 9, h: 0.28, fontSize: 9, color: dark ? "B7D3BF" : C.muted, italic: true });
const card = (slide, x, y, w, h, fill = C.white) =>
  slide.addShape(pres.shapes.ROUNDED_RECTANGLE, { x, y, w, h, rectRadius: 0.12, fill: { color: fill },
    line: { color: C.line, width: 0.75 } });
const dot = (slide, x, y, d, fill, label, fontSize = 18) => {
  slide.addShape(pres.shapes.OVAL, { x, y, w: d, h: d, fill: { color: fill }, line: { color: fill } });
  text(slide, label, { x, y, w: d, h: d, align: "center", valign: "middle", fontSize, bold: true, color: C.white });
};

// Phone mockup showing a green verdict (drawn with shapes so the deck has no external assets).
function phone(slide, x, y, verdict = "green") {
  const fill = { green: C.mint, red: C.redBg, yellow: C.amberBg }[verdict];
  const ink = { green: C.green, red: C.red, yellow: C.amber }[verdict];
  slide.addShape(pres.shapes.ROUNDED_RECTANGLE, { x, y, w: 2.3, h: 4.4, rectRadius: 0.3, fill: { color: "0F1A12" }, line: { color: "0F1A12" } });
  slide.addShape(pres.shapes.ROUNDED_RECTANGLE, { x: x + 0.12, y: y + 0.18, w: 2.06, h: 4.04, rectRadius: 0.2, fill: { color: C.white }, line: { color: C.white } });
  slide.addShape(pres.shapes.ROUNDED_RECTANGLE, { x: x + 0.25, y: y + 0.45, w: 1.8, h: 1.6, rectRadius: 0.15, fill: { color: fill }, line: { color: fill } });
  dot(slide, x + 0.87, y + 0.6, 0.56, ink, verdict === "green" ? "✓" : "!", 22);
  text(slide, { green: "Safe to use as per label", red: "Stop. Do not use", yellow: "Caution" }[verdict],
    { x: x + 0.3, y: y + 1.25, w: 1.7, h: 0.7, fontSize: 11, bold: true, color: ink, align: "center" });
  const lines = [["30 ml per 15 L tank", true], ["8 tanks for your 1 acre", false], ["Do not harvest before 14 Oct", false], ["Wear gloves and mask", false]];
  lines.forEach(([t, b], i) => text(slide, t, { x: x + 0.3, y: y + 2.2 + i * 0.36, w: 1.7, h: 0.3, fontSize: 9.5, bold: b, color: C.ink }));
  slide.addShape(pres.shapes.ROUNDED_RECTANGLE, { x: x + 0.3, y: y + 3.65, w: 1.7, h: 0.38, rectRadius: 0.08, fill: { color: C.green }, line: { color: C.green } });
  text(slide, "Save spray", { x: x + 0.3, y: y + 3.65, w: 1.7, h: 0.38, fontSize: 10, bold: true, color: C.white, align: "center", valign: "middle" });
}

// 1 Title
{
  const s = pres.addSlide();
  s.background = { color: C.forest };
  text(s, "AgriTech track", { x: 0.6, y: 0.6, w: 5.5, h: 0.35, fontSize: 14, color: "B7D3BF", bold: true });
  text(s, "DawaCheck", { x: 0.6, y: 1.05, w: 5.8, h: 1.0, fontFace: HEAD, fontSize: 48, bold: true, color: C.white });
  text(s, "Plantix tells you the disease. DawaCheck tells you whether the pesticide the dealer handed you is genuine, approved for your crop, safe to mix, and when your harvest is safe to sell.",
    { x: 0.6, y: 2.15, w: 5.6, h: 1.4, fontSize: 16, color: "E8F2EA", italic: true });
  text(s, "Voice-first pesticide check at the moment of purchase", { x: 0.6, y: 3.8, w: 5.6, h: 0.4, fontSize: 13, color: "B7D3BF" });
  phone(s, 7.0, 0.6, "green");
  s.addNotes("Add your team name here before the pitch. One line: DawaCheck checks the bottle, not the leaf.");
}

// 2 Hook
{
  const s = pres.addSlide();
  s.background = { color: C.forest };
  title(s, "Yavatmal, Maharashtra, 2017", { color: C.white });
  text(s, "Cotton farmers sprayed what the dealer gave them. Warnings were printed in English and Hindi; most spoke Marathi.",
    { x: 0.5, y: 1.1, w: 9, h: 0.6, fontSize: 15, color: "E8F2EA" });
  [["20+", "deaths in the district"], ["~800", "hospital admissions"], ["100s", "with temporary blindness; staff could not identify the toxin"]]
    .forEach(([n, l], i) => {
      const x = 0.5 + i * 3.05;
      s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x, y: 2.0, w: 2.8, h: 2.4, rectRadius: 0.15, fill: { color: "1D6B3A" }, line: { color: "1D6B3A" } });
      text(s, n, { x, y: 2.2, w: 2.8, h: 1.2, fontSize: 54, bold: true, color: i === 2 ? "FFB4AB" : C.white, align: "center", fontFace: HEAD });
      text(s, l, { x: x + 0.2, y: 3.45, w: 2.4, h: 0.8, fontSize: 14, color: "E8F2EA", align: "center" });
    });
  source(s, "Sources: Public Eye, 'The Yavatmal scandal'; NHRC notice (2017). Figures for Jul to Oct 2017.", true);
  s.addNotes("Yavatmal, 2017. Over 20 farmers died and about 800 reached hospital after spraying cotton. Doctors did not know which poison it was. The farmer had bought what the dealer gave him.");
}

// 3 Problem chain
{
  const s = pres.addSlide();
  s.background = { color: C.white };
  title(s, "The harm happens after the diagnosis");
  const steps = [
    ["52%", "buy on credit from the dealer who advises them", C.amber],
    ["20%", "read the pesticide label", C.amber],
    ["Blind", "tank mixes of several products", C.amber],
    ["Rare", "gloves or masks while spraying", C.red],
    ["2.8%", "of food samples above MRL", C.red],
    ["97", "EU detections of tricyclazole in Indian rice", C.red],
  ];
  steps.forEach(([n, l, col], i) => {
    const x = 0.45 + i * 1.55;
    card(s, x, 1.45, 1.4, 2.9, C.paper);
    text(s, String(i + 1), { x: x + 0.1, y: 1.55, w: 0.4, h: 0.3, fontSize: 11, color: C.muted, bold: true });
    text(s, n, { x, y: 1.95, w: 1.4, h: 0.8, fontSize: n.length > 4 ? 22 : 30, bold: true, color: col, align: "center", fontFace: HEAD });
    text(s, l, { x: x + 0.12, y: 2.85, w: 1.16, h: 1.4, fontSize: 11.5, color: C.ink, align: "center" });
    if (i < 5) text(s, "›", { x: x + 1.38, y: 2.6, w: 0.2, h: 0.4, fontSize: 20, color: C.muted, align: "center" });
  });
  text(s, "Purchase  ·  Label  ·  Mixing  ·  Spraying  ·  Harvest  ·  Export", { x: 0.45, y: 4.5, w: 9.1, h: 0.35, fontSize: 13, color: C.muted, align: "center" });
  source(s, "Agriculture and Human Values (2026, West Bengal, 441 households); Public Eye; FSSAI 2022-25 via Punjab Kesari (Aug 2025); Lok Sabha answer (Mar 2025).");
  s.addNotes("A farmer decides what to spray based on a dealer he owes money to, cannot read or verify the label, mixes products blindly, sprays without protection and harvests without knowing the waiting period.");
}

// 4 Why nothing solves it
{
  const s = pres.addSlide();
  s.background = { color: C.white };
  title(s, "Every app stops at 'which disease?'");
  const cols = ["Scans the packet", "Crop + dose + PHI", "Brand-neutral"];
  const rows = [
    ["Plantix", "✗", "✗", "✓"], ["AgroStar, DeHaat", "✗", "✗", "✗"], ["FarmerChat, Kisan e-Mitra", "✗", "✗", "✓"],
    ["Bayer Safety Seal", "Bayer only", "✗", "✗"], ["DawaCheck", "✓", "✓", "✓"],
  ];
  const head = [{ text: "", options: {} }, ...cols.map((c) => ({ text: c, options: { bold: true, color: C.muted } }))];
  const body = rows.map((r) => r.map((cell, j) => ({
    text: cell,
    options: {
      bold: r[0] === "DawaCheck" || j === 0, align: j ? "center" : "left",
      color: cell === "✓" ? C.green : cell === "✗" ? C.red : C.ink,
      fill: { color: r[0] === "DawaCheck" ? C.mint : C.white },
    },
  })));
  s.addTable([head, ...body], { x: 0.5, y: 1.3, w: 9, colW: [3.3, 1.9, 1.9, 1.9], fontFace: BODY, fontSize: 15,
    rowH: 0.52, border: { type: "solid", color: C.line, pt: 0.75 }, valign: "middle" });
  source(s, "Khetiyaar (2026) comparison of farming apps; Bayer Safety Seal app. Re-run the competitor search on GitHub, Devfolio and Play Store before the pitch.");
  s.addNotes("Every existing app answers which disease. We answer the next eight questions: is this product real, is it allowed on this crop, how much, can I mix it, how do I stay safe, what if I get sick, when can I harvest, and will the buyer accept it.");
}

// 5 Solution
{
  const s = pres.addSlide();
  s.background = { color: C.paper };
  title(s, "Scan, verify, dose, harvest safely");
  const steps = [["📷", "Scan", "QR, label photo or dealer bill"], ["✔", "Verify", "Registry, ban list, crop and pest"],
    ["🥛", "Dose", "ml per tank and number of tanks"], ["📅", "Safe harvest", "Spray date + waiting period"],
    ["🔳", "Passport", "QR spray record for the buyer"]];
  steps.forEach(([ico, h, d], i) => {
    const x = 0.5 + i * 1.84;
    card(s, x, 1.4, 1.64, 2.6);
    dot(s, x + 0.52, 1.6, 0.6, i === 1 ? C.green : C.forest, ico, 18);
    text(s, h, { x: x + 0.1, y: 2.35, w: 1.44, h: 0.4, fontSize: 16, bold: true, align: "center", fontFace: HEAD });
    text(s, d, { x: x + 0.12, y: 2.8, w: 1.4, h: 1.0, fontSize: 12, color: C.muted, align: "center" });
  });
  text(s, "Three taps to a spoken verdict in Hindi, Marathi or Punjabi. Colour + icon + sound, never colour alone.",
    { x: 0.5, y: 4.3, w: 9, h: 0.5, fontSize: 15, color: C.forest, bold: true, align: "center" });
}

// 6 WOW features
{
  const s = pres.addSlide();
  s.background = { color: C.white };
  title(s, "Six features built on one engine");
  const tiles = [
    ["🧾", "Bill Scan", "Every item on the dealer's bill checked; same chemical for less"],
    ["🧪", "Cocktail Checker", "Double doses, same resistance group, stacked toxicity"],
    ["🔳", "MRL Passport", "Spray record + safe date the exporter can scan"],
    ["🩺", "Doctor Card + SOS", "Chemical, class and label antidote; NPIC 1800 116 117"],
    ["🔄", "Rotation Planner", "Next spray from a different IRAC/FRAC group"],
    ["🗺", "Fake-Batch Radar", "Same batch with different dates, cloned QR codes"],
  ];
  tiles.forEach(([ico, h, d], i) => {
    const x = 0.5 + (i % 3) * 3.05, y = 1.3 + Math.floor(i / 3) * 1.95;
    card(s, x, y, 2.85, 1.75, i === 3 ? C.redBg : C.paper);
    dot(s, x + 0.2, y + 0.2, 0.55, i === 3 ? C.red : C.green, ico, 16);
    text(s, h, { x: x + 0.9, y: y + 0.25, w: 1.85, h: 0.45, fontSize: 15, bold: true, fontFace: HEAD });
    text(s, d, { x: x + 0.2, y: y + 0.9, w: 2.5, h: 0.75, fontSize: 12, color: C.muted });
  });
  s.addNotes("Each scan protects one farmer. A million scans map every fake batch in the state.");
}

// 7 How it works
{
  const s = pres.addSlide();
  s.background = { color: C.white };
  title(s, "AI reads, rules decide");
  const box = (x, y, w, h, head, sub, fill = C.paper, ink = C.ink) => {
    card(s, x, y, w, h, fill);
    text(s, head, { x: x + 0.15, y: y + 0.1, w: w - 0.3, h: 0.35, fontSize: 13, bold: true, color: ink });
    text(s, sub, { x: x + 0.15, y: y + 0.45, w: w - 0.3, h: h - 0.5, fontSize: 10.5, color: C.muted });
  };
  box(0.5, 1.15, 2.9, 0.8, "Farmer app (PWA)", "Camera, voice, offline cache");
  box(3.55, 1.15, 2.9, 0.8, "Officer / FPO dashboard", "Radar map, passports");
  box(6.6, 1.15, 2.9, 0.8, "MRL Passport page", "Public link behind the QR");
  box(0.5, 2.15, 9, 0.6, "FastAPI backend", "/scan  /bill  /mix-check  /dose  /spray-log  /passport  /sos  /weather-window  /radar");
  box(0.5, 2.95, 2.9, 1.1, "AI reading layer", "QR decode, OCR, LLM text to strict JSON, fuzzy match");
  box(3.55, 2.95, 2.9, 1.1, "Rules engine R1 to R13", "Rules stored as data; worst colour wins; cites file + page", C.mint, C.forest);
  box(6.6, 2.95, 2.9, 1.1, "Supporting services", "Weather window, Doctor Card, batch-signal scorer");
  box(0.5, 4.25, 9, 0.75, "Knowledge base: PostgreSQL + PostGIS", "label_claims, products, bans, export_flags, scans, spray_log, batch_signals, prices  ·  built from CIB&RC PDFs by an offline pipeline");
  s.addNotes("What if the AI reads the label wrong? The AI only reads; the farmer confirms the product; rules decide; every verdict cites the CIB&RC page.");
}

// 8 Proof
{
  const s = pres.addSlide();
  s.background = { color: C.paper };
  title(s, "What is built and tested");
  const stats = [["79", "automated tests passing (rules, API, pipeline)"], ["30 / 30", "knowledge-base questions answered correctly"],
    ["13", "verdict rules, each citing its source"], ["4", "languages: English, Hindi, Marathi, Punjabi"]];
  stats.forEach(([n, l], i) => {
    const x = 0.5 + (i % 2) * 4.6, y = 1.25 + Math.floor(i / 2) * 1.45;
    card(s, x, y, 4.3, 1.25);
    text(s, n, { x: x + 0.25, y: y + 0.15, w: 1.9, h: 0.95, fontSize: 36, bold: true, color: C.green, fontFace: HEAD, valign: "middle" });
    text(s, l, { x: x + 2.15, y: y + 0.2, w: 2.0, h: 0.85, fontSize: 13, color: C.ink, valign: "middle" });
  });
  text(s, "To add before the pitch: OCR + extraction accuracy on 50 real packs, and counts of products and label claims loaded from the parsed CIB&RC PDFs (current label claims are sample data).",
    { x: 0.5, y: 4.2, w: 9, h: 0.7, fontSize: 12, color: C.amber, italic: true });
}

// 9 Impact + business
{
  const s = pres.addSlide();
  s.background = { color: C.white };
  title(s, "Farmers never pay");
  const rows = [
    ["Exporters and FPOs", "MRL Passport for every member plot", "per farmer per season"],
    ["Agrochemical brands", "Map of cloned QR codes and suspicious batches", "annual data subscription"],
    ["State agriculture departments", "Fake-Batch Radar and dealer-level statistics", "licence or grant-funded pilot"],
    ["Dealers", "Verified Dealer badge", "small monthly fee"],
  ];
  rows.forEach(([who, what, how], i) => {
    const y = 1.2 + i * 0.85;
    card(s, 0.5, y, 9, 0.72, i % 2 ? C.white : C.paper);
    dot(s, 0.65, y + 0.13, 0.46, C.green, "₹", 14);
    text(s, who, { x: 1.3, y: y + 0.1, w: 2.8, h: 0.52, fontSize: 14, bold: true, valign: "middle" });
    text(s, what, { x: 4.1, y: y + 0.1, w: 3.3, h: 0.52, fontSize: 12, color: C.ink, valign: "middle" });
    text(s, how, { x: 7.4, y: y + 0.1, w: 2.0, h: 0.52, fontSize: 11, color: C.muted, italic: true, valign: "middle" });
  });
  text(s, "Impact: farmer health, money saved at the shop, food safety, export income.", { x: 0.5, y: 4.7, w: 9, h: 0.35, fontSize: 13, color: C.forest, bold: true });
  source(s, "Pricing lines are hypotheses to validate with real customers, not researched figures.");
}

// 10 Roadmap + ask
{
  const s = pres.addSlide();
  s.background = { color: C.forest };
  title(s, "Roadmap and our ask", { color: C.white });
  const road = [["Next", "Packaging forensics (genuine vs suspicious pack photos)"], ["Next", "IVR / missed-call access for feature phones"],
    ["Later", "WhatsApp bot, diagnosis link, drone mode"], ["Later", "AgriStack and Kisan Call Centre integration"]];
  road.forEach(([when, what], i) => {
    const y = 1.25 + i * 0.72;
    text(s, when, { x: 0.5, y, w: 0.9, h: 0.5, fontSize: 12, bold: true, color: "B7D3BF", valign: "middle" });
    text(s, what, { x: 1.4, y, w: 4.4, h: 0.5, fontSize: 14, color: C.white, valign: "middle" });
  });
  s.addShape(pres.shapes.ROUNDED_RECTANGLE, { x: 6.2, y: 1.25, w: 3.3, h: 2.75, rectRadius: 0.15, fill: { color: C.white }, line: { color: C.white } });
  text(s, "The ask", { x: 6.45, y: 1.4, w: 2.8, h: 0.4, fontSize: 16, bold: true, color: C.forest, fontFace: HEAD });
  text(s, "A one-season pilot with one FPO or one district: 200 farmers growing basmati or cotton.",
    { x: 6.45, y: 1.85, w: 2.8, h: 1.2, fontSize: 13, color: C.ink });
  text(s, "Demo video: add QR here", { x: 6.45, y: 3.25, w: 2.8, h: 0.5, fontSize: 11, color: C.muted, italic: true });
  text(s, "DawaCheck helps farmers ask the right question at the shop. It does not replace the agriculture officer, the lab or the doctor.",
    { x: 0.5, y: 4.35, w: 9, h: 0.6, fontSize: 13, color: "E8F2EA", italic: true });
  s.addNotes("Plantix tells you the disease. DawaCheck takes responsibility for the dose, from the dealer's shop to the dinner plate.");
}

pres.writeFile({ fileName: "../DawaCheck_pitch.pptx" }).then((f) => console.log("wrote", f));
