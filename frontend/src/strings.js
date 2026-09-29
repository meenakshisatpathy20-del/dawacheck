// UI labels (verdict messages come from the backend's translation files).
// Hindi, Marathi and Punjabi are drafts: review with native speakers before the demo.
export const LANGS = { en: "English", hi: "हिंदी", mr: "मराठी", pa: "ਪੰਜਾਬੀ" };
export const TTS = { en: "en-IN", hi: "hi-IN", mr: "mr-IN", pa: "pa-IN" };

const S = {
  en: {
    scanPacket: "Scan packet", scanBill: "Scan bill", mixCheck: "Mix check", sos: "SOS",
    mySprays: "My sprays", nextSafe: "Next safe harvest", pickCrop: "Which crop?", pickPest: "Which pest or disease?",
    anyPest: "Not sure", takePhoto: "Take photo", orPick: "Or pick the product", typeQr: "Type code on pack",
    confirm: "Is this the product?", yes: "Yes", no: "No", why: "Why?", better: "Better option",
    dose: "How much to spray", area: "Land (acre)", pump: "Pump (L)", save: "Save spray", saved: "Saved",
    safeFrom: "Safe to harvest from", back: "Back", home: "Home", checking: "Checking…", listen: "Listen again",
    addProduct: "Add product", check: "Check", remove: "Remove", callNpic: "Call poison centre", call108: "Call 108",
    showCard: "Show Doctor Card", firstAid: "First aid (from label)", passport: "MRL Passport", plot: "Plot",
    state: "State", report: "Report this product", reported: "Reported. Thank you.", offline: "Offline: saved result",
    wearGear: "I have gloves and mask", weather: "Spray window", speak: "Speak", noOcr: "Scan the QR code or pick the product.",
    total: "Total", saving: "Possible saving", notApproved: "not approved", sampleData: "Sample data",
  },
  hi: {
    scanPacket: "पैकेट जाँचें", scanBill: "बिल जाँचें", mixCheck: "मिश्रण जाँच", sos: "SOS",
    mySprays: "मेरे छिड़काव", nextSafe: "अगली सुरक्षित कटाई", pickCrop: "कौन सी फसल?", pickPest: "कौन सा कीट या रोग?",
    anyPest: "पता नहीं", takePhoto: "फ़ोटो लें", orPick: "या दवा चुनें", typeQr: "पैकेट का कोड लिखें",
    confirm: "क्या यही दवा है?", yes: "हाँ", no: "नहीं", why: "क्यों?", better: "बेहतर विकल्प",
    dose: "कितना छिड़कें", area: "ज़मीन (एकड़)", pump: "पंप (लीटर)", save: "छिड़काव सहेजें", saved: "सहेजा गया",
    safeFrom: "कटाई सुरक्षित", back: "पीछे", home: "होम", checking: "जाँच हो रही है…", listen: "फिर सुनें",
    addProduct: "दवा जोड़ें", check: "जाँचें", remove: "हटाएँ", callNpic: "विष केंद्र को फ़ोन", call108: "108 पर फ़ोन",
    showCard: "डॉक्टर कार्ड दिखाएँ", firstAid: "प्राथमिक उपचार (लेबल से)", passport: "MRL पासपोर्ट", plot: "खेत",
    state: "राज्य", report: "इस दवा की शिकायत करें", reported: "शिकायत दर्ज। धन्यवाद।", offline: "ऑफ़लाइन: सहेजा परिणाम",
    wearGear: "मेरे पास दस्ताने और मास्क हैं", weather: "छिड़काव का समय", speak: "बोलें", noOcr: "QR कोड स्कैन करें या दवा चुनें।",
    total: "कुल", saving: "संभावित बचत", notApproved: "मंज़ूर नहीं", sampleData: "नमूना डेटा",
  },
  mr: {
    scanPacket: "पाकीट तपासा", scanBill: "बिल तपासा", mixCheck: "मिश्रण तपासणी", sos: "SOS",
    mySprays: "माझ्या फवारण्या", nextSafe: "पुढील सुरक्षित काढणी", pickCrop: "कोणते पीक?", pickPest: "कोणती कीड किंवा रोग?",
    anyPest: "माहीत नाही", takePhoto: "फोटो घ्या", orPick: "किंवा औषध निवडा", typeQr: "पाकिटावरील कोड लिहा",
    confirm: "हेच औषध आहे का?", yes: "हो", no: "नाही", why: "का?", better: "चांगला पर्याय",
    dose: "किती फवारावे", area: "जमीन (एकर)", pump: "पंप (लिटर)", save: "फवारणी जतन करा", saved: "जतन केले",
    safeFrom: "काढणी सुरक्षित", back: "मागे", home: "मुख्य", checking: "तपासत आहे…", listen: "पुन्हा ऐका",
    addProduct: "औषध जोडा", check: "तपासा", remove: "काढा", callNpic: "विष केंद्राला फोन", call108: "108 ला फोन",
    showCard: "डॉक्टर कार्ड दाखवा", firstAid: "प्रथमोपचार (लेबलवरून)", passport: "MRL पासपोर्ट", plot: "शेत",
    state: "राज्य", report: "या औषधाची तक्रार करा", reported: "तक्रार नोंदवली. धन्यवाद.", offline: "ऑफलाइन: जतन केलेला निकाल",
    wearGear: "माझ्याकडे हातमोजे आणि मास्क आहेत", weather: "फवारणीची वेळ", speak: "बोला", noOcr: "QR कोड स्कॅन करा किंवा औषध निवडा.",
    total: "एकूण", saving: "संभाव्य बचत", notApproved: "मंजूर नाही", sampleData: "नमुना माहिती",
  },
  pa: {
    scanPacket: "ਪੈਕਟ ਜਾਂਚੋ", scanBill: "ਬਿੱਲ ਜਾਂਚੋ", mixCheck: "ਮਿਸ਼ਰਣ ਜਾਂਚ", sos: "SOS",
    mySprays: "ਮੇਰੇ ਛਿੜਕਾਅ", nextSafe: "ਅਗਲੀ ਸੁਰੱਖਿਅਤ ਵਾਢੀ", pickCrop: "ਕਿਹੜੀ ਫ਼ਸਲ?", pickPest: "ਕਿਹੜਾ ਕੀੜਾ ਜਾਂ ਰੋਗ?",
    anyPest: "ਪਤਾ ਨਹੀਂ", takePhoto: "ਫ਼ੋਟੋ ਲਓ", orPick: "ਜਾਂ ਦਵਾਈ ਚੁਣੋ", typeQr: "ਪੈਕਟ ਦਾ ਕੋਡ ਲਿਖੋ",
    confirm: "ਕੀ ਇਹੀ ਦਵਾਈ ਹੈ?", yes: "ਹਾਂ", no: "ਨਹੀਂ", why: "ਕਿਉਂ?", better: "ਵਧੀਆ ਵਿਕਲਪ",
    dose: "ਕਿੰਨਾ ਛਿੜਕਣਾ", area: "ਜ਼ਮੀਨ (ਏਕੜ)", pump: "ਪੰਪ (ਲੀਟਰ)", save: "ਛਿੜਕਾਅ ਸੰਭਾਲੋ", saved: "ਸੰਭਾਲਿਆ",
    safeFrom: "ਵਾਢੀ ਸੁਰੱਖਿਅਤ", back: "ਪਿੱਛੇ", home: "ਮੁੱਖ", checking: "ਜਾਂਚ ਹੋ ਰਹੀ ਹੈ…", listen: "ਫਿਰ ਸੁਣੋ",
    addProduct: "ਦਵਾਈ ਜੋੜੋ", check: "ਜਾਂਚੋ", remove: "ਹਟਾਓ", callNpic: "ਜ਼ਹਿਰ ਕੇਂਦਰ ਨੂੰ ਫ਼ੋਨ", call108: "108 ਤੇ ਫ਼ੋਨ",
    showCard: "ਡਾਕਟਰ ਕਾਰਡ ਦਿਖਾਓ", firstAid: "ਮੁੱਢਲੀ ਸਹਾਇਤਾ (ਲੇਬਲ ਤੋਂ)", passport: "MRL ਪਾਸਪੋਰਟ", plot: "ਖੇਤ",
    state: "ਰਾਜ", report: "ਇਸ ਦਵਾਈ ਦੀ ਸ਼ਿਕਾਇਤ ਕਰੋ", reported: "ਸ਼ਿਕਾਇਤ ਦਰਜ। ਧੰਨਵਾਦ।", offline: "ਆਫ਼ਲਾਈਨ: ਸੰਭਾਲਿਆ ਨਤੀਜਾ",
    wearGear: "ਮੇਰੇ ਕੋਲ ਦਸਤਾਨੇ ਅਤੇ ਮਾਸਕ ਹਨ", weather: "ਛਿੜਕਾਅ ਦਾ ਸਮਾਂ", speak: "ਬੋਲੋ", noOcr: "QR ਕੋਡ ਸਕੈਨ ਕਰੋ ਜਾਂ ਦਵਾਈ ਚੁਣੋ।",
    total: "ਕੁੱਲ", saving: "ਸੰਭਾਵੀ ਬੱਚਤ", notApproved: "ਮਨਜ਼ੂਰ ਨਹੀਂ", sampleData: "ਨਮੂਨਾ ਡਾਟਾ",
  },
};

export const t = (lang, key) => (S[lang] && S[lang][key]) || S.en[key] || key;

// Placeholder pictures. Replace with real crop and pest photos (playbook: "photos, not words").
export const CROP_ICON = { rice: "🌾", basmati: "🍚", cotton: "☁️", tomato: "🍅", okra: "🫛" };
export const PEST_ICON = {
  bollworm: "🐛", "fruit borer": "🐛", "stem borer": "🐛", "leaf folder": "🍃", jassid: "🦗", "brown plant hopper": "🦗",
  aphid: "🐜", whitefly: "🪰", thrips: "🦟", blast: "🍂", "sheath blight": "🍂", "early blight": "🍂", "late blight": "🍂",
};
export const CROP_NAME = {
  en: {}, hi: { rice: "धान", basmati: "बासमती", cotton: "कपास", tomato: "टमाटर" },
  mr: { rice: "भात", basmati: "बासमती", cotton: "कापूस", tomato: "टोमॅटो" },
  pa: { rice: "ਝੋਨਾ", basmati: "ਬਾਸਮਤੀ", cotton: "ਨਰਮਾ", tomato: "ਟਮਾਟਰ" },
};
