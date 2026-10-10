"""Every bot sentence in Hindi and English. People choose their language; Hindi is the default."""

from __future__ import annotations

LANGS = ("hi", "en")

MESSAGES: dict[str, dict[str, str]] = {
    "help": {
        "hi": "💧 <b>JalSaathi</b>\nसरकारी लैब जांच में गाँव का पानी असुरक्षित पाया जाए, तो हम सूचना और सही सावधानी बताते हैं, "
              "और ठीक होने तक मामले पर नज़र रखते हैं।\n\nजुड़ने के लिए गाँव के पोस्टर का QR कोड स्कैन करें, या नीचे गाँव चुनें।\n"
              "/status पानी की स्थिति · /english English · /stop सदस्यता बंद करें",
        "en": "💧 <b>JalSaathi</b>\nWhen a government lab test finds a village's water unsafe, we send the alert and the right "
              "precautions, and follow the case until a re-test passes.\n\nScan the QR code on the village poster to join, "
              "or pick a village below.\n/status water status · /hindi हिंदी · /stop unsubscribe",
    },
    "consent": {
        "hi": "<b>{label}</b> {who} की सूचनाएं पाने के लिए आपकी अनुमति चाहिए।\n"
              "हम सिर्फ़ आपकी Telegram चैट आईडी और चुना गया गाँव या ब्लॉक रखेंगे। /stop से कभी भी हटा सकते हैं।",
        "en": "We need your permission to send you alerts for <b>{label}</b> {who}.\n"
              "We keep only your Telegram chat ID and the village or block you chose. Remove it any time with /stop.",
    },
    "who_village": {"hi": "गाँव", "en": "village"},
    "who_block": {"hi": "ब्लॉक (इंजीनियर)", "en": "block (engineer)"},
    "block_label": {"hi": "{name} ब्लॉक", "en": "{name} block"},
    "yes": {"hi": "✅ हाँ", "en": "✅ Yes"},
    "no": {"hi": "❌ नहीं", "en": "❌ No"},
    "switch_to": {"hi": "🇬🇧 Read in English", "en": "🇮🇳 हिंदी में पढ़ें"},
    "lang_set": {"hi": "अब संदेश हिंदी में आएंगे। English के लिए /english भेजें।",
                 "en": "Messages will now come in English. Send /hindi for Hindi."},
    "not_joined": {"hi": "आप अभी किसी गाँव से नहीं जुड़े हैं। /start से जुड़ें।",
                   "en": "You haven't joined a village yet. Send /start to join."},
    "village_not_found": {"hi": "यह गाँव हमारे रिकॉर्ड में नहीं मिला।", "en": "We couldn't find this village in our records."},
    "stopped": {"hi": "आपकी {n} सदस्यता और जानकारी हटा दी गई। धन्यवाद।",
                "en": "Removed {n} subscription(s) and your details. Thank you."},
    "declined": {"hi": "ठीक है, कुछ भी सेव नहीं किया गया।", "en": "OK, nothing was saved."},
    "joined_toast": {"hi": "जुड़ गए ✅", "en": "Joined ✅"},
    "joined_village": {"hi": "✅ आप <b>{name}</b> से जुड़ गए।\nअभी की स्थिति: {status}",
                       "en": "✅ You joined <b>{name}</b>.\nStatus now: {status}"},
    "joined_engineer": {"hi": "✅ आप {block} के इंजीनियर के रूप में जुड़ गए। खुले मामलों के कार्ड नीचे हैं; नए मामले भी यहीं आएंगे।",
                        "en": "✅ You joined as the engineer for {block}. Open cases are below; new ones will come here too."},
    "no_open_cases": {"hi": "इस ब्लॉक में अभी कोई खुला मामला नहीं है।", "en": "There are no open cases in this block right now."},
    "more_cases": {"hi": "इस ब्लॉक में {n} और खुले मामले हैं। /status से गिनती देखें।",
                   "en": "{n} more open cases in this block. Send /status for the count."},
    "status_block": {"hi": "• {block}: {n} खुले मामले", "en": "• {block}: {n} open cases"},
    "logged_toast": {"hi": "दर्ज हो गया ✅", "en": "Logged ✅"},
    "fix_logged": {"hi": "✅ दर्ज: {action}। अब गाँव में दोबारा जांच होगी।",
                   "en": "✅ Logged: {action}. The village will now re-test the water."},
    "close_denied": {"hi": "केस बंद नहीं हो सकता: सिर्फ़ लैब की पास जांच से ही केस बंद होता है।",
                     "en": "This case can't be closed: only a passing lab re-test closes it."},
    "close_allowed": {"hi": "केस बंद करने की अनुमति है।", "en": "Closing is allowed."},
    "photo_first": {"hi": "पहले शीशी की फ़ोटो भेजें, फिर बटन दबाएं।", "en": "Send a photo of the vial first, then tap the button."},
    "result_logged": {"hi": "नतीजा दर्ज ✅", "en": "Result logged ✅"},
    "fix_chlorination": {"hi": "🧪 क्लोरीनेशन किया", "en": "🧪 Chlorinated"},
    "fix_repair": {"hi": "🔧 मरम्मत की", "en": "🔧 Repaired"},
    "fix_source_changed": {"hi": "🔁 स्रोत बदला", "en": "🔁 Changed source"},
    "fix_need_help": {"hi": "🆘 मदद चाहिए", "en": "🆘 Need help"},
    "close_case": {"hi": "✅ केस बंद करें", "en": "✅ Close case"},
    "kit_request": {"hi": "🧪 <b>{village}</b>: मरम्मत दर्ज हो गई है।\n"
                          "H2S शीशी से पानी की जांच करें। 24 से 48 घंटे बाद शीशी की फ़ोटो भेजें, फिर नतीजा चुनें।",
                    "en": "🧪 <b>{village}</b>: the fix has been logged.\n"
                          "Test the water with an H2S vial. After 24 to 48 hours, send a photo of the vial, then choose the result."},
    "kit_black": {"hi": "⚫ काली (दूषित)", "en": "⚫ Black (contaminated)"},
    "kit_yellow": {"hi": "🟡 पीली (साफ़)", "en": "🟡 Yellow (clean)"},
    "escalation_fix": {"hi": "⏰ <b>{village}</b>: काम की समय सीमा निकल गई। मामला ज़िले को भेजा गया।",
                       "en": "⏰ <b>{village}</b>: the fix deadline has passed. The case has gone to the district."},
    "escalation_retest": {"hi": "⏰ <b>{village}</b>: दोबारा जांच की समय सीमा निकल गई। कृपया शीशी से जांच करें।",
                          "en": "⏰ <b>{village}</b>: the re-test is overdue. Please test with the vial."},
    "escalation_lab": {"hi": "⏰ <b>{village}</b>: लैब की दोबारा जांच का इंतज़ार है। मामला ज़िले को भेजा गया।",
                       "en": "⏰ <b>{village}</b>: still waiting for the lab re-test. The case has gone to the district."},
    "reopened": {"hi": "⚠️ <b>{village}</b>: दोबारा जांच साफ़ नहीं आई। पहले बताई गई सावधानियां जारी रखें।",
                 "en": "⚠️ <b>{village}</b>: the re-test was not clean. Keep following the precautions."},
    "provisional": {"hi": "🟡 <b>{village}</b>: फील्ड जांच साफ़ आई। लैब जांच की पुष्टि तक सावधानी जारी रखें।",
                    "en": "🟡 <b>{village}</b>: the field test was clean. Keep the precautions until the lab confirms."},
    "closed": {"hi": "✅ <b>{village}</b>: लैब की दोबारा जांच में पानी सुरक्षित पाया गया।",
               "en": "✅ <b>{village}</b>: the lab re-test found the water safe."},
    "push_alert": {"hi": "{village}: पानी की जांच में {found} मिला। क्या करें, देखें।",
                   "en": "{village}: the water test found {found}. See what to do."},
    "push_new_case": {"hi": "{village}: नया मामला ({found})। काम दर्ज करें।",
                      "en": "{village}: new case ({found}). Log the fix."},
    "audio_title": {"hi": "JalSaathi सूचना", "en": "JalSaathi alert"},
    "photo_received": {"hi": "📷 फ़ोटो मिल गई। अब जांच वाले संदेश में नतीजा चुनें।",
                       "en": "📷 Photo received. Now choose the result in the test message."},
    "hint": {"hi": "📷 फ़ोटो मिल गई।\n🤖 <i>AI सुझाव</i>: {hint}\nयह सिर्फ़ सुझाव है। शीशी को खुद देखकर जांच वाले संदेश में सही नतीजा चुनें।",
             "en": "📷 Photo received.\n🤖 <i>AI suggestion</i>: {hint}\nThis is only a suggestion. Look at the vial yourself and "
                   "choose the result in the test message."},
    "hint_black": {"hi": "शीशी <b>काली</b> दिखती है, यानी पानी दूषित हो सकता है।",
                   "en": "the vial looks <b>black</b>, so the water may be contaminated."},
    "hint_yellow": {"hi": "शीशी <b>पीली</b> दिखती है, यानी पानी साफ़ हो सकता है।",
                    "en": "the vial looks <b>yellow</b>, so the water may be clean."},
    "hint_unclear": {"hi": "फ़ोटो से रंग साफ़ नहीं दिख रहा।", "en": "the colour isn't clear from the photo."},
}


def norm(lang: str | None) -> str:
    return lang if lang in LANGS else "hi"


def t(key: str, lang: str | None = "hi", **kw) -> str:
    return MESSAGES[key][norm(lang)].format(**kw)


def other(lang: str | None) -> str:
    return "en" if norm(lang) == "hi" else "hi"
