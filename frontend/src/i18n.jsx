import { createContext, useContext, useEffect, useState } from "react";

// Every UI sentence in English and Hindi. Case advice and status text come from the API in both languages.
const T = {
  en: {
    nav_map: "Map", nav_officials: "Officials", nav_impact: "Impact", lang_switch: "हिंदी",
    hero_kicker: "Lab-confirmed drinking-water alerts",
    hero_title: "Clear water can still make a child sick.",
    hero_body: "JalSaathi turns failed government lab tests into village alerts in Hindi and English, with the right precaution for each contaminant, and keeps every case open until a re-test proves the water safe.",
    hero_cta_map: "See the live map", hero_cta_impact: "What it found",
    stat_villages: "villages with a failed test", stat_open: "open cases", stat_chemical: "of them are chemicals boiling can't fix",
    stat_repeat: "villages failed again the next year",
    live_from: "Live from JJM-WQMIS, Uttar Pradesh and Rajasthan",
    search: "Search a village, block or district", no_match: "No village matches.",
    legend_unsafe: "Unsafe", legend_provisional: "Field test clean", legend_safe: "Safe again", legend_approx: "Approximate location",
    how_title: "How a case closes",
    how_1_t: "A lab test fails", how_1_b: "We read JJM-WQMIS, the government's own water-test portal. No crowd reports, no guessing.",
    how_2_t: "The village is warned", how_2_b: "A Hindi or English alert with a voice note, on Telegram and in this app, with the right advice: boil for bacteria, never boil for nitrate.",
    how_3_t: "The engineer logs the fix", how_3_b: "One tap from the block engineer. Deadlines escalate to the district automatically.",
    how_4_t: "Only a re-test closes it", how_4_b: "A field kit marks it provisionally safe; only a passing lab re-test can close the case. A Cedar policy enforces it, even against the engineer.",
    why_title: "Why 'just boil it' is dangerous advice",
    why_body: "Boiling kills bacteria, but it concentrates nitrate and does nothing for fluoride or arsenic. Most of the failures we track are chemical, so a one-size alert would do harm.",
    village_open_cases: "Open cases", village_what_to_do: "What to do now", village_listen: "Listen",
    village_measured: "Measured", village_limit: "Safe limit", village_times: "× the limit", village_any: "Any amount is unsafe",
    village_lab: "Lab test", village_sample: "Sample", village_source: "Water source", village_scheme: "Scheme",
    village_timeline: "Case timeline", village_join: "Get alerts for this village",
    village_telegram: "Alerts on Telegram", village_app_alerts: "Alerts in this app", village_print: "Print the village poster",
    village_data: "Data", village_not_found: "We couldn't find this village.",
    village_no_cases: "No failed test on record for this village.",
    push_on: "App alerts are on", push_enable: "Turn on app alerts", push_unsupported: "This browser can't show app alerts. Use Telegram.",
    push_denied: "Notifications are blocked in this browser.",
    status_AWAITING_FIX: "Waiting for the fix", status_ESCALATED: "Overdue, escalated", status_AWAITING_RETEST: "Waiting for field re-test",
    status_PROVISIONALLY_SAFE: "Field test clean, lab pending", status_CLOSED: "Closed: lab re-test passed",
    status_WARNED: "Village warned", status_DETECTED: "Detected",
    severity_red: "Act today", severity_amber: "Act this week", severity_yellow: "Monitor", severity_review: "Review",
    deadline_in: "Deadline in", deadline_passed: "Deadline passed", no_deadline: "Escalated to the district; no further deadline",
    eng_title: "Block engineer", eng_readonly: "View only. Engineers open this page from their signed link to log work.",
    eng_link_ok: "Signed in by your block link", eng_suggested: "Suggested fix", eng_log: "Log the work you did",
    eng_close: "Close case", eng_logged: "Logged. The village will now re-test the water.",
    eng_denied_title: "Close refused by policy", eng_denied_body: "Only a passing lab re-test can close a case. This rule is a Cedar policy, checked on every action and logged on the timeline.",
    eng_not_waiting: "This case isn't waiting for a fix right now.",
    fix_chlorination: "Chlorinated", fix_repair: "Repaired", fix_source_changed: "Changed source", fix_need_help: "Need help",
    eng_open: "open", eng_overdue: "overdue", eng_cases: "Cases in this block",
    relay_title: "Village relay", relay_readonly: "View only. Relays open this page from their signed village link.",
    relay_step_photo: "1. Photograph the H2S vial", relay_step_hint: "2. Check the AI suggestion", relay_step_result: "3. Choose what you see",
    relay_take_photo: "Take or choose a photo", relay_uploading: "Uploading…", relay_reading: "Reading the vial…",
    relay_ai: "AI suggestion", relay_ai_note: "Only a suggestion. Look at the vial yourself and choose.",
    relay_black: "Black: contaminated", relay_yellow: "Yellow: clean", relay_done: "Result recorded.",
    relay_nothing: "Nothing to test right now. When the engineer logs a fix, the field-kit test appears here.",
    off_title: "Officials' overview", off_body: "Every open case by district and block, worst first. Overdue means a deadline passed and the case escalated.",
    off_district: "District", off_open: "Open", off_overdue: "Overdue", off_villages: "Villages", off_chemical: "Chemical",
    off_activity: "Live activity", off_blocks: "Blocks", off_view_block: "Open block view",
    act_detected: "Case opened", act_warned: "Village warned", act_awaiting_fix: "Engineer asked", act_escalated: "Escalated",
    act_fix_logged: "Fix logged", act_awaiting_retest: "Field re-test requested", act_kit_result: "Field-kit result",
    act_reopened: "Reopened", act_awaiting_lab: "Lab re-test requested", act_lab_result: "Lab result", act_closed: "Closed",
    act_policy: "Cedar decision", act_restarted: "Restarted",
    impact_title: "What JalSaathi found, and how well it works",
    impact_body: "Every number comes from the live system or the committed WQMIS snapshot. The weak numbers are here too.",
    footer: "Data: JJM-WQMIS, Department of Drinking Water and Sanitation, Ministry of Jal Shakti. Built on AWS for WeMakeDevs × AWS Environmental Hacks 2026. Not an official government service.",
    loading: "Loading…", error: "Something went wrong", retry: "Try again",
    class_microbial: "bacteria", class_chemical: "chemical", class_physical: "physical", class_aesthetic: "taste", relay_link_ok: "Signed in by your village link",
  },
  hi: {
    nav_map: "नक्शा", nav_officials: "अधिकारी", nav_impact: "असर", lang_switch: "English",
    hero_kicker: "लैब से पक्की पानी की सूचना",
    hero_title: "साफ़ दिखने वाला पानी भी बच्चे को बीमार कर सकता है।",
    hero_body: "JalSaathi सरकारी लैब जांच में फेल हुए पानी की सूचना गाँव तक हिंदी और English में पहुंचाता है, हर दूषक के लिए सही सावधानी के साथ, और दोबारा जांच पास होने तक मामला खुला रखता है।",
    hero_cta_map: "लाइव नक्शा देखें", hero_cta_impact: "क्या मिला",
    stat_villages: "गाँव जहाँ जांच फेल हुई", stat_open: "खुले मामले", stat_chemical: "रसायन, जिन्हें उबालने से ठीक नहीं किया जा सकता",
    stat_repeat: "गाँव अगले साल फिर फेल हुए",
    live_from: "JJM-WQMIS से लाइव, उत्तर प्रदेश और राजस्थान",
    search: "गाँव, ब्लॉक या ज़िला खोजें", no_match: "कोई गाँव नहीं मिला।",
    legend_unsafe: "असुरक्षित", legend_provisional: "फील्ड जांच साफ़", legend_safe: "फिर सुरक्षित", legend_approx: "अनुमानित जगह",
    how_title: "मामला कैसे बंद होता है",
    how_1_t: "लैब जांच फेल होती है", how_1_b: "हम सरकार का अपना पोर्टल JJM-WQMIS पढ़ते हैं। कोई अंदाज़ा नहीं।",
    how_2_t: "गाँव को सूचना मिलती है", how_2_b: "हिंदी या English में सूचना और आवाज़ वाला संदेश, Telegram और इस ऐप पर, सही सलाह के साथ: बैक्टीरिया हो तो उबालें, नाइट्रेट हो तो कभी नहीं।",
    how_3_t: "इंजीनियर काम दर्ज करता है", how_3_b: "ब्लॉक इंजीनियर का एक टैप। समय सीमा निकलने पर मामला अपने आप ज़िले तक जाता है।",
    how_4_t: "सिर्फ़ दोबारा जांच से बंद", how_4_b: "फील्ड किट से अस्थायी रूप से सुरक्षित; केस सिर्फ़ लैब की पास जांच से बंद होता है। यह नियम Cedar पॉलिसी लागू करती है।",
    why_title: "'बस उबाल लो' खतरनाक सलाह क्यों है",
    why_body: "उबालने से बैक्टीरिया मरते हैं, पर नाइट्रेट बढ़ जाता है और फ्लोराइड या आर्सेनिक पर कोई असर नहीं होता। हमारे ज़्यादातर मामले रसायन के हैं।",
    village_open_cases: "खुले मामले", village_what_to_do: "अभी क्या करें", village_listen: "सुनें",
    village_measured: "मात्रा", village_limit: "सुरक्षित सीमा", village_times: "गुना सीमा से", village_any: "थोड़ी मात्रा भी असुरक्षित",
    village_lab: "लैब जांच", village_sample: "सैंपल", village_source: "पानी का स्रोत", village_scheme: "योजना",
    village_timeline: "मामले की समयरेखा", village_join: "इस गाँव की सूचनाएं पाएं",
    village_telegram: "Telegram पर सूचना", village_app_alerts: "इस ऐप में सूचना", village_print: "गाँव का पोस्टर छापें",
    village_data: "डेटा", village_not_found: "यह गाँव नहीं मिला।",
    village_no_cases: "इस गाँव की कोई फेल जांच दर्ज नहीं है।",
    push_on: "ऐप सूचनाएं चालू हैं", push_enable: "ऐप सूचनाएं चालू करें", push_unsupported: "यह ब्राउज़र ऐप सूचनाएं नहीं दिखा सकता। Telegram इस्तेमाल करें।",
    push_denied: "इस ब्राउज़र में सूचनाएं बंद हैं।",
    status_AWAITING_FIX: "मरम्मत का इंतज़ार", status_ESCALATED: "देर हुई, ज़िले को भेजा", status_AWAITING_RETEST: "फील्ड जांच का इंतज़ार",
    status_PROVISIONALLY_SAFE: "फील्ड जांच साफ़, लैब बाकी", status_CLOSED: "बंद: लैब जांच पास",
    status_WARNED: "गाँव को सूचना दी", status_DETECTED: "पता चला",
    severity_red: "आज ही", severity_amber: "इस हफ़्ते", severity_yellow: "निगरानी", severity_review: "जांच",
    deadline_in: "समय सीमा", deadline_passed: "समय सीमा निकल गई", no_deadline: "ज़िले को भेजा गया; आगे कोई समय सीमा नहीं",
    eng_title: "ब्लॉक इंजीनियर", eng_readonly: "सिर्फ़ देखने के लिए। इंजीनियर अपने लिंक से काम दर्ज करते हैं।",
    eng_link_ok: "आपके ब्लॉक लिंक से", eng_suggested: "सुझाया गया काम", eng_log: "किया गया काम दर्ज करें",
    eng_close: "केस बंद करें", eng_logged: "दर्ज हो गया। अब गाँव में दोबारा जांच होगी।",
    eng_denied_title: "पॉलिसी ने बंद करने से रोका", eng_denied_body: "केस सिर्फ़ लैब की पास जांच से बंद होता है। यह Cedar पॉलिसी हर कदम पर जांचती है और समयरेखा में दर्ज करती है।",
    eng_not_waiting: "यह मामला अभी मरम्मत का इंतज़ार नहीं कर रहा।",
    fix_chlorination: "क्लोरीनेशन किया", fix_repair: "मरम्मत की", fix_source_changed: "स्रोत बदला", fix_need_help: "मदद चाहिए",
    eng_open: "खुले", eng_overdue: "देर से", eng_cases: "इस ब्लॉक के मामले",
    relay_title: "गाँव का संपर्क", relay_readonly: "सिर्फ़ देखने के लिए। संपर्क व्यक्ति अपने गाँव लिंक से खोलते हैं।",
    relay_step_photo: "1. H2S शीशी की फ़ोटो लें", relay_step_hint: "2. AI सुझाव देखें", relay_step_result: "3. जो दिखे वह चुनें",
    relay_take_photo: "फ़ोटो लें या चुनें", relay_uploading: "भेज रहे हैं…", relay_reading: "शीशी पढ़ रहे हैं…",
    relay_ai: "AI सुझाव", relay_ai_note: "सिर्फ़ सुझाव है। शीशी खुद देखकर चुनें।",
    relay_black: "काली: दूषित", relay_yellow: "पीली: साफ़", relay_done: "नतीजा दर्ज हो गया।",
    relay_nothing: "अभी कोई जांच नहीं। इंजीनियर के काम दर्ज करने के बाद फील्ड किट जांच यहाँ दिखेगी।",
    off_title: "अधिकारियों के लिए", off_body: "हर खुला मामला ज़िले और ब्लॉक के हिसाब से। 'देर से' यानी समय सीमा निकल गई।",
    off_district: "ज़िला", off_open: "खुले", off_overdue: "देर से", off_villages: "गाँव", off_chemical: "रसायन",
    off_activity: "लाइव गतिविधि", off_blocks: "ब्लॉक", off_view_block: "ब्लॉक देखें",
    act_detected: "मामला खुला", act_warned: "गाँव को सूचना", act_awaiting_fix: "इंजीनियर से कहा", act_escalated: "ज़िले को भेजा",
    act_fix_logged: "काम दर्ज", act_awaiting_retest: "फील्ड जांच मांगी", act_kit_result: "फील्ड किट नतीजा",
    act_reopened: "फिर खुला", act_awaiting_lab: "लैब जांच मांगी", act_lab_result: "लैब नतीजा", act_closed: "बंद",
    act_policy: "Cedar फैसला", act_restarted: "फिर शुरू",
    impact_title: "JalSaathi को क्या मिला, और यह कितना काम करता है",
    impact_body: "हर संख्या लाइव सिस्टम या WQMIS स्नैपशॉट से है। कमज़ोर संख्याएं भी यहीं हैं।",
    footer: "डेटा: JJM-WQMIS, पेयजल एवं स्वच्छता विभाग, जल शक्ति मंत्रालय। AWS पर बना, WeMakeDevs × AWS Environmental Hacks 2026 के लिए। यह सरकारी सेवा नहीं है।",
    loading: "लोड हो रहा है…", error: "कुछ गड़बड़ हुई", retry: "फिर कोशिश करें",
    class_microbial: "बैक्टीरिया", class_chemical: "रसायन", class_physical: "भौतिक", class_aesthetic: "स्वाद", relay_link_ok: "आपके गाँव लिंक से",
  },
};

const LangContext = createContext({ lang: "en", t: (k) => k, setLang: () => {} });

function initialLang() {
  try {
    const saved = localStorage.getItem("jalsaathi-lang");
    if (saved === "hi" || saved === "en") return saved;
  } catch { /* private mode */ }
  return (navigator.language || "").startsWith("hi") ? "hi" : "en";
}

export function LangProvider({ children }) {
  const [lang, setLangState] = useState(initialLang);
  useEffect(() => { document.documentElement.lang = lang; }, [lang]);
  const setLang = (l) => {
    setLangState(l);
    try { localStorage.setItem("jalsaathi-lang", l); } catch { /* private mode */ }
  };
  const t = (key) => (T[lang] && T[lang][key]) || T.en[key] || key;
  return <LangContext.Provider value={{ lang, t, setLang }}>{children}</LangContext.Provider>;
}

export const useLang = () => useContext(LangContext);
