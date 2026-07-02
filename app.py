"""
=============================================================
  Exotel IVR Webhook — Multi-Language + Department + SIP Transfer
  Framework : Flask (Python)
  Responds   : ExoML (Exotel's XML dialect)
=============================================================
CALL FLOW:
  1. Customer calls Exotel number
  2. Exotel hits /ivr/welcome  → play welcome + gather language
  3. Exotel hits /ivr/language → store language, play dept menu
  4. Exotel hits /ivr/department → determine SIP trunk, transfer
  5. On no-input / wrong-input → retry up to 3 times then transfer
=============================================================
"""

from flask import Flask, request, Response
from urllib.parse import urlencode

app = Flask(__name__)

# ─────────────────────────────────────────────────────────────
# CONFIGURATION — update BASE_URL after Render deploy
# ─────────────────────────────────────────────────────────────

BASE_URL    = "https://hindware-ivr.onrender.com"
MAX_RETRIES = 3

LANGUAGES = {
    "1": {"name": "English",   "code": "en-IN", "greet": "Welcome to Hindware. Please press 1 for Service, press 2 for Dealer Help Desk."},
    "2": {"name": "Hindi",     "code": "hi-IN", "greet": "हिंदवेयर में आपका स्वागत है। सेवा के लिए 1 दबाएं, डीलर हेल्प डेस्क के लिए 2 दबाएं।"},
    "3": {"name": "Tamil",     "code": "ta-IN", "greet": "ஹிந்த்வேரில் உங்களை வரவேற்கிறோம். சேவைக்கு 1 அழுத்தவும், டீலர் உதவிக்கு 2 அழுத்தவும்."},
    "4": {"name": "Telugu",    "code": "te-IN", "greet": "హిందువేర్ కు స్వాగతం. సేవ కోసం 1 నొక్కండి, డీలర్ హెల్ప్ డెస్క్ కోసం 2 నొక్కండి."},
    "5": {"name": "Kannada",   "code": "kn-IN", "greet": "ಹಿಂದ್ ವೇರ್ ಗೆ ಸ್ವಾಗತ. ಸೇವೆಗಾಗಿ 1 ಒತ್ತಿರಿ, ಡೀಲರ್ ಸಹಾಯ ಡೆಸ್ಕ್ ಗಾಗಿ 2 ಒತ್ತಿರಿ."},
    "6": {"name": "Bengali",   "code": "bn-IN", "greet": "হিন্দওয়্যারে আপনাকে স্বাগতম। সেবার জন্য 1 চাপুন, ডিলার হেল্প ডেস্কের জন্য 2 চাপুন।"},
    "7": {"name": "Marathi",   "code": "mr-IN", "greet": "हिंदवेअरमध्ये आपले स्वागत आहे. सेवेसाठी 1 दाबा, डीलर हेल्प डेस्कसाठी 2 दाबा."},
    "8": {"name": "Gujarati",  "code": "gu-IN", "greet": "હિન્દ્વેરમાં આપનું સ્વાગત છે. સેવા માટે 1 દબાવો, ડીલર હેલ્પ ડેસ્ક માટે 2 દબાવો."},
    "9": {"name": "Malayalam", "code": "ml-IN", "greet": "ഹിന്ദ്‌വെയറിലേക്ക് സ്വാഗതം. സേവനത്തിനായി 1 അമർത്തുക, ഡീലർ ഹെൽപ് ഡെസ്‌കിനായി 2 അമർത്തുക."},
}

SIP_TRUNKS = {
    "1_1": "sip:trmum1f6b810c5a7c3e6d122197n@sip.exotel.com",
    "2_1": "sip:trmum1f6b810c5a7c3e6d122197n@sip.exotel.com",
    "3_1": "sip:trmum1f6b810c5a7c3e6d122197n@sip.exotel.com",
    "4_1": "sip:trmum1f6b810c5a7c3e6d122197n@sip.exotel.com",
    "5_1": "sip:trmum1f6b810c5a7c3e6d122197n@sip.exotel.com",
    "6_1": "sip:trmum1f6b810c5a7c3e6d122197n@sip.exotel.com",
    "7_1": "sip:trmum1f6b810c5a7c3e6d122197n@sip.exotel.com",
    "8_1": "sip:trmum1f6b810c5a7c3e6d122197n@sip.exotel.com",
    "9_1": "sip:trmum1f6b810c5a7c3e6d122197n@sip.exotel.com",
    "1_2": "sip:trmum1f6b810c5a7c3e6d122197n@sip.exotel.com",
    "2_2": "sip:trmum1f6b810c5a7c3e6d122197n@sip.exotel.com",
    "3_2": "sip:trmum1f6b810c5a7c3e6d122197n@sip.exotel.com",
    "4_2": "sip:trmum1f6b810c5a7c3e6d122197n@sip.exotel.com",
    "5_2": "sip:trmum1f6b810c5a7c3e6d122197n@sip.exotel.com",
    "6_2": "sip:trmum1f6b810c5a7c3e6d122197n@sip.exotel.com",
    "7_2": "sip:trmum1f6b810c5a7c3e6d122197n@sip.exotel.com",
    "8_2": "sip:trmum1f6b810c5a7c3e6d122197n@sip.exotel.com",
    "9_2": "sip:trmum1f6b810c5a7c3e6d122197n@sip.exotel.com",
}

DEFAULT_SIP = "sip:trmum1f6b810c5a7c3e6d122197n@sip.exotel.com"


# ─────────────────────────────────────────────────────────────
# HELPERS
# ─────────────────────────────────────────────────────────────

def xml_escape(text):
    """Escape XML special characters in text content and attributes."""
    return (text
            .replace("&", "&amp;")
            .replace("<", "&lt;")
            .replace(">", "&gt;")
            .replace('"', "&quot;"))

def exoml(content):
    xml = "<?xml version=\"1.0\" encoding=\"UTF-8\"?>\n<Response>\n" + content + "\n</Response>"
    return Response(xml, mimetype="application/xml")

def say(text, voice="female"):
    """<Say> tag — auto escapes special characters."""
    return '  <Say voice="{}">{}</Say>'.format(voice, xml_escape(text))

def build_url(path, params):
    """Build URL — & in query string is escaped as &amp; for XML attributes."""
    query = urlencode(params).replace("&", "&amp;")
    return "{}{}?{}".format(BASE_URL, path, query)

def gather(action_url, num_digits=1, timeout=10, content=""):
    """<Gather> tag — action URL already has &amp; from build_url."""
    return '  <Gather action="{}" numDigits="{}" timeout="{}">\n{}\n  </Gather>'.format(
        action_url, num_digits, timeout, content)

def transfer_sip(sip_uri):
    return '  <Dial>\n    <Number>{}</Number>\n  </Dial>'.format(sip_uri)


# ─────────────────────────────────────────────────────────────
# STEP 1 — Welcome + Language Selection
# ─────────────────────────────────────────────────────────────

@app.route("/ivr/welcome", methods=["GET", "POST"])
def welcome():
    action_url = build_url("/ivr/language", {"retry": 0})
    lang_prompts = "\n".join([
        say("For English, press 1."),
        say("Hindi ke liye 2 dabayen."),
        say("Tamil-il 3 anukkavum."),
        say("Telugu lo 4 nakkandi."),
        say("Kannada ge 5 ottiri."),
        say("Bangla te 6 chaapon."),
        say("Marathi sathi 7 daba."),
        say("Gujarati mate 8 dabavo."),
        say("Malayalam il 9 arakkuka."),
    ])
    return exoml(gather(action_url, num_digits=1, timeout=15, content=lang_prompts))


# ─────────────────────────────────────────────────────────────
# STEP 2 — Receive Language, Play Department Menu
# ─────────────────────────────────────────────────────────────

@app.route("/ivr/language", methods=["GET", "POST"])
def language():
    digit = request.values.get("digits", "").strip()
    retry = int(request.values.get("retry", 0))

    if digit not in LANGUAGES:
        if retry >= MAX_RETRIES:
            return exoml(
                say("We could not understand your input. Transferring you now.") +
                "\n" + transfer_sip(DEFAULT_SIP)
            )
        retry_url = build_url("/ivr/language", {"retry": retry + 1})
        lang_prompts = "\n".join([
            say("Sorry, invalid input. Please try again."),
            say("For English, press 1."),
            say("Hindi ke liye 2 dabayen."),
            say("Tamil-il 3 anukkavum."),
            say("Telugu lo 4 nakkandi."),
            say("Kannada ge 5 ottiri."),
            say("Bangla te 6 chaapon."),
            say("Marathi sathi 7 daba."),
            say("Gujarati mate 8 dabavo."),
            say("Malayalam il 9 arakkuka."),
        ])
        return exoml(gather(retry_url, num_digits=1, timeout=15, content=lang_prompts))

    lang     = LANGUAGES[digit]
    dept_url = build_url("/ivr/department", {"lang": digit, "retry": 0})
    return exoml(gather(dept_url, num_digits=1, timeout=10, content=say(lang["greet"])))


# ─────────────────────────────────────────────────────────────
# STEP 3 — Receive Department, Transfer to SIP Trunk
# ─────────────────────────────────────────────────────────────

@app.route("/ivr/department", methods=["GET", "POST"])
def department():
    digit    = request.values.get("digits", "").strip()
    lang_key = request.values.get("lang", "1")
    retry    = int(request.values.get("retry", 0))
    lang     = LANGUAGES.get(lang_key, LANGUAGES["1"])

    if digit not in ("1", "2"):
        if retry >= MAX_RETRIES:
            return exoml(
                say("We could not understand your input. Transferring you now.") +
                "\n" + transfer_sip(DEFAULT_SIP)
            )
        retry_url = build_url("/ivr/department", {"lang": lang_key, "retry": retry + 1})
        return exoml(gather(retry_url, num_digits=1, timeout=10, content=say(lang["greet"])))

    sip_uri   = SIP_TRUNKS.get("{}_{}".format(lang_key, digit), DEFAULT_SIP)
    dept_name = "Service" if digit == "1" else "Dealer Help Desk"
    print("[IVR] Lang: {} | Dept: {} | SIP: {}".format(lang["name"], dept_name, sip_uri))

    transfer_msgs = {
        "1": {
            "en-IN": "Please hold, transferring you to our Service team.",
            "hi-IN": "कृपया प्रतीक्षा करें, हम आपको सेवा टीम से जोड़ रहे हैं।",
            "ta-IN": "தயவுசெய்து காத்திருங்கள், உங்களை சேவை குழுவிடம் இணைக்கிறோம்.",
            "te-IN": "దయచేసి వేచి ఉండండి, మీరు సేవా బృందానికి బదిలీ అవుతున్నారు.",
            "kn-IN": "ದಯವಿಟ್ಟು ನಿರೀಕ್ಷಿಸಿ, ನಿಮ್ಮನ್ನು ಸೇವಾ ತಂಡಕ್ಕೆ ವರ್ಗಾಯಿಸಲಾಗುತ್ತಿದೆ.",
            "bn-IN": "অনুগ্রহ করে অপেক্ষা করুন, আপনাকে সেবা দলের কাছে স্থানান্তরিত করা হচ্ছে।",
            "mr-IN": "कृपया थांबा, आपल्याला सेवा संघाकडे हस्तांतरित केले जात आहे.",
            "gu-IN": "કૃપા કરીને રાહ જુઓ, તમને સેવા ટીમ સાથે જોડવામાં આવી રહ્યા છો.",
            "ml-IN": "ദയവായി കാത്തിരിക്കൂ, നിങ്ങളെ സേവന ടീമിലേക്ക് കൈമാറ്റം ചെയ്യുന്നു.",
        },
        "2": {
            "en-IN": "Please hold, transferring you to our Dealer Help Desk.",
            "hi-IN": "कृपया प्रतीक्षा करें, हम आपको डीलर हेल्प डेस्क से जोड़ रहे हैं।",
            "ta-IN": "தயவுசெய்து காத்திருங்கள், உங்களை டீலர் உதவி மையத்துடன் இணைக்கிறோம்.",
            "te-IN": "దయచేసి వేచి ఉండండి, మీరు డీలర్ హెల్ప్ డెస్క్ కు బదిలీ అవుతున్నారు.",
            "kn-IN": "ದಯವಿಟ್ಟು ನಿರೀಕ್ಷಿಸಿ, ನಿಮ್ಮನ್ನು ಡೀಲರ್ ಹೆಲ್ಪ್ ಡೆಸ್ಕ್ ಗೆ ವರ್ಗಾಯಿಸಲಾಗುತ್ತಿದೆ.",
            "bn-IN": "অনুগ্রহ করে অপেক্ষা করুন, আপনাকে ডিলার হেল্প ডেস্কে স্থানান্তরিত করা হচ্ছে।",
            "mr-IN": "कृपया थांबा, आपल्याला डीलर हेल्प डेस्ककडे हस्तांतरित केले जात आहे.",
            "gu-IN": "કૃપા કરીને રાહ જુઓ, તમને ડીલર હેલ્પ ડેસ્ક સાથે જોડવામાં આવી રહ્યા છો.",
            "ml-IN": "ദയവായി കാത്തിരിക്കൂ, നിങ്ങളെ ഡീലർ ഹെൽപ് ഡെസ്‌കിലേക്ക് കൈമാറ്റം ചെയ്യുന്നു.",
        }
    }

    msg = transfer_msgs[digit].get(lang["code"], transfer_msgs[digit]["en-IN"])
    return exoml(say(msg) + "\n" + transfer_sip(sip_uri))


# ─────────────────────────────────────────────────────────────
# FALLBACK
# ─────────────────────────────────────────────────────────────

@app.route("/ivr/fallback", methods=["GET", "POST"])
def fallback():
    return exoml(
        say("We are sorry. Please hold while we connect you.") +
        "\n" + transfer_sip(DEFAULT_SIP)
    )


# ─────────────────────────────────────────────────────────────
# HEALTH CHECK
# ─────────────────────────────────────────────────────────────

@app.route("/health", methods=["GET"])
def health():
    return {"status": "ok", "service": "Hindware IVR Webhook"}, 200


if __name__ == "__main__":
    print("Hindware IVR Webhook running on http://0.0.0.0:5000")
    app.run(host="0.0.0.0", port=5000, debug=True)
