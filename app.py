"""
=============================================================
  Exotel IVR Webhook — Multi-Language + Department + SIP Transfer
  Framework : Flask (Python)
  Responds   : ExoML (Exotel's XML dialect)
=============================================================

CALL FLOW:
  1. Customer calls Exotel number
  2. Exotel hits POST /ivr/welcome  → play welcome + gather language
  3. Exotel hits POST /ivr/language → store language, play dept menu + gather dept
  4. Exotel hits POST /ivr/department → determine SIP trunk, transfer call
  5. On no-input / wrong-input → retry up to 3 times, then transfer to default

HOW TO RUN:
  pip install flask
  python app.py

  Then expose via ngrok:
  ngrok http 5000
  Use the ngrok URL as your Exotel Passthru App URL.
=============================================================
"""

from flask import Flask, request, Response
from urllib.parse import urlencode

app = Flask(__name__)

# ─────────────────────────────────────────────────────────────
# CONFIGURATION
# ─────────────────────────────────────────────────────────────

# Your server's public base URL (replace with your ngrok/server URL)
BASE_URL = "https://hindware-ivr.onrender.com"

# ── Language map ──
# Key   = digit pressed by caller
# name  = display name
# code  = BCP-47 language code for TTS
# greet = greeting text in that language
LANGUAGES = {
    "1": {"name": "English",    "code": "en-IN", "greet": "Welcome to Hindware. Please press 1 for Service, press 2 for Dealer Help Desk."},
    "2": {"name": "Hindi",      "code": "hi-IN", "greet": "हिंदवेयर में आपका स्वागत है। सेवा के लिए 1 दबाएं, डीलर हेल्प डेस्क के लिए 2 दबाएं।"},
    "3": {"name": "Tamil",      "code": "ta-IN", "greet": "ஹிந்த்வேரில் உங்களை வரவேற்கிறோம். சேவைக்கு 1 அழுத்தவும், டீலர் உதவிக்கு 2 அழுத்தவும்."},
    "4": {"name": "Telugu",     "code": "te-IN", "greet": "హిందువేర్‌కు స్వాగతం. సేవ కోసం 1 నొక్కండి, డీలర్ హెల్ప్ డెస్క్ కోసం 2 నొక్కండి."},
    "5": {"name": "Kannada",    "code": "kn-IN", "greet": "ಹಿಂದ್‌ವೇರ್‌ಗೆ ಸ್ುಸ್ವಾಗತ. ಸೇವೆಗಾಗಿ 1 ಒತ್ತಿರಿ, ಡೀಲರ್ ಸಹಾಯ ಡೆಸ್ಕ್‌ಗಾಗಿ 2 ಒತ್ತಿರಿ."},
    "6": {"name": "Bengali",    "code": "bn-IN", "greet": "হিন্দওয়্যারে আপনাকে স্বাগতম। সেবার জন্য ১ চাপুন, ডিলার হেল্প ডেস্কের জন্য ২ চাপুন।"},
    "7": {"name": "Marathi",    "code": "mr-IN", "greet": "हिंदवेअरमध्ये आपले स्वागत आहे. सेवेसाठी 1 दाबा, डीलर हेल्प डेस्कसाठी 2 दाबा."},
    "8": {"name": "Gujarati",   "code": "gu-IN", "greet": "હિન્દ્વેરમાં આપનું સ્વાગત છે. સેવા માટે 1 દબાવો, ડીલર હેલ્પ ડેસ્ક માટે 2 દબાવો."},
    "9": {"name": "Malayalam",  "code": "ml-IN", "greet": "ഹിന്ദ്‌വെയറിലേക്ക് സ്വാഗതം. സേവനത്തിനായി 1 അമർത്തുക, ഡീലർ ഹെൽപ് ഡെസ്‌കിനായി 2 അമർത്തുക."},
}

# ── SIP Trunk map ──
# Key format: "{language_digit}_{department_digit}"
# department 1 = Service  |  department 2 = Dealer Help Desk
#
# Replace the sip: URIs below with your actual SIP trunk addresses
SIP_TRUNKS = {
    # ── Service trunks (dept=1) ──
    "1_1": "sip:trmum1f6b810c5a7c3e6d122197n@sip.exotel.com",   # English  - Service
    "2_1": "sip:trmum1f6b810c5a7c3e6d122197n@sip.exotel.com",   # Hindi    - Service
    "3_1": "sip:trmum1f6b810c5a7c3e6d122197n@sip.exotel.com",   # Tamil    - Service
    "4_1": "sip:trmum1f6b810c5a7c3e6d122197n@sip.exotel.com",   # Telugu   - Service
    "5_1": "sip:trmum1f6b810c5a7c3e6d122197n@sip.exotel.com",   # Kannada  - Service
    "6_1": "sip:trmum1f6b810c5a7c3e6d122197n@sip.exotel.com",   # Bengali  - Service
    "7_1": "sip:trmum1f6b810c5a7c3e6d122197n@sip.exotel.com",   # Marathi  - Service
    "8_1": "sip:trmum1f6b810c5a7c3e6d122197n@sip.exotel.com",   # Gujarati - Service
    "9_1": "sip:trmum1f6b810c5a7c3e6d122197n@sip.exotel.com",   # Malayalam- Service
    # ── Dealer Help Desk trunks (dept=2) ──
    "1_2": "sip:trmum1f6b810c5a7c3e6d122197n@sip.exotel.com",   # English  - Dealer
    "2_2": "sip:trmum1f6b810c5a7c3e6d122197n@sip.exotel.com",   # Hindi    - Dealer
    "3_2": "sip:trmum1f6b810c5a7c3e6d122197n@sip.exotel.com",   # Tamil    - Dealer
    "4_2": "sip:trmum1f6b810c5a7c3e6d122197n@sip.exotel.com",   # Telugu   - Dealer
    "5_2": "sip:trmum1f6b810c5a7c3e6d122197n@sip.exotel.com",   # Kannada  - Dealer
    "6_2": "sip:trmum1f6b810c5a7c3e6d122197n@sip.exotel.com",   # Bengali  - Dealer
    "7_2": "sip:trmum1f6b810c5a7c3e6d122197n@sip.exotel.com",   # Marathi  - Dealer
    "8_2": "sip:trmum1f6b810c5a7c3e6d122197n@sip.exotel.com",   # Gujarati - Dealer
    "9_2": "sip:trmum1f6b810c5a7c3e6d122197n@sip.exotel.com",   # Malayalam- Dealer
}

# Default SIP trunk if something goes wrong
DEFAULT_SIP = "sip:trmum1f6b810c5a7c3e6d122197n@sip.exotel.com"

# Max retries before transferring to default
MAX_RETRIES = 3


# ─────────────────────────────────────────────────────────────
# HELPER — build ExoML response
# ─────────────────────────────────────────────────────────────

def exoml(content: str) -> Response:
    """Wrap content in ExoML <Response> and return as XML response."""
    xml = f"""<?xml version="1.0" encoding="UTF-8"?>
<Response>
{content}
</Response>"""
    return Response(xml, mimetype="application/xml")


def say(text: str, lang: str = "en-IN", voice: str = "female") -> str:
    """Generate a <Say> ExoML tag."""
    return f'  <Say voice="{voice}">{text}</Say>'


def gather(action_url: str, num_digits: int = 1, timeout: int = 5, content: str = "") -> str:
    return f"""  <Gather action="{action_url}" numDigits="{num_digits}" timeout="{timeout}">
{content}
  </Gather>"""


def redirect(url: str) -> str:
    """Generate a <Redirect> ExoML tag."""
    return f'  <Redirect method="POST">{url}</Redirect>'


def transfer_sip(sip_uri: str) -> str:
    return f"""  <Dial>
    <Number>{sip_uri}</Number>
  </Dial>"""


def build_url(path: str, params: dict) -> str:
    """Build a full URL with query parameters."""
    return f"{BASE_URL}{path}?{urlencode(params)}"


# ─────────────────────────────────────────────────────────────
# STEP 1 — Welcome + Language Selection
# ─────────────────────────────────────────────────────────────

@app.route("/ivr/welcome", methods=["GET", "POST"])
def welcome():
    """
    Entry point. Called by Exotel when a call comes in.
    Plays a multilingual welcome prompt and asks caller to select language.
    """
    action_url = build_url("/ivr/language", {"retry": 0})

    # Build language menu using <Say> for each language
    lang_prompts = "\n".join([
        say("For English, press 1.", "en-IN"),
        say("Hindi ke liye 2 dabayen.", "hi-IN"),
        say("Tamil-il 3 anukkavum.", "ta-IN"),
        say("Telugu lo 4 nakkandi.", "te-IN"),
        say("Kannada ge 5 ottiri.", "kn-IN"),
        say("Bangla te 6 chaapon.", "bn-IN"),
        say("Marathi sathi 7 daba.", "mr-IN"),
        say("Gujarati mate 8 dabavo.", "gu-IN"),
        say("Malayalam il 9 arakkuka.", "ml-IN"),
    ])

    content = gather(
        action_url=action_url,
        num_digits=1,
        timeout=5,
        content=lang_prompts
    )

    return exoml(content)


# ─────────────────────────────────────────────────────────────
# STEP 2 — Receive Language, Play Department Menu
# ─────────────────────────────────────────────────────────────

@app.route("/ivr/language", methods=["GET", "POST"])
def language():
    """
    Receives the language digit pressed by the caller.
    Plays the department menu in the selected language.
    """
    digit   = request.values.get("digits", "").strip()
    retry   = int(request.values.get("retry", 0))

    # ── Validate language input ──
    if digit not in LANGUAGES:
        if retry >= MAX_RETRIES:
            # Too many wrong inputs → transfer to default
            return exoml(
                say("We could not understand your input. Transferring you now.", "en-IN") +
                "\n" + transfer_sip(DEFAULT_SIP)
            )
        # Retry — replay language menu
        retry_url = build_url("/ivr/language", {"retry": retry + 1})
        lang_prompts = "\n".join([
            say("Sorry, invalid input. Please try again.", "en-IN"),
            say("For English, press 1.", "en-IN"),
            say("Hindi ke liye 2 dabayen.", "hi-IN"),
            say("Tamil-il 3 anukkavum.", "ta-IN"),
            say("Telugu lo 4 nakkandi.", "te-IN"),
            say("Kannada ge 5 ottiri.", "kn-IN"),
            say("Bangla te 6 chaapon.", "bn-IN"),
            say("Marathi sathi 7 daba.", "mr-IN"),
            say("Gujarati mate 8 dabavo.", "gu-IN"),
            say("Malayalam il 9 arakkuka.", "ml-IN"),
        ])
        return exoml(gather(
            action_url=retry_url,
            num_digits=1,
            timeout=5,
            content=lang_prompts
        ))

    # ── Valid language selected ──
    lang      = LANGUAGES[digit]
    dept_url  = build_url("/ivr/department", {"lang": digit, "retry": 0})

    # Play department menu in selected language
    dept_say = say(lang["greet"], lang["code"])
    content  = gather(
        action_url=dept_url,
        num_digits=1,
        timeout=5,
        content=dept_say
    )

    return exoml(content)


# ─────────────────────────────────────────────────────────────
# STEP 3 — Receive Department, Transfer to SIP Trunk
# ─────────────────────────────────────────────────────────────

@app.route("/ivr/department", methods=["GET", "POST"])
def department():
    """
    Receives the department digit (1=Service, 2=Dealer Help Desk).
    Determines the correct SIP trunk and transfers the call.
    """
    digit     = request.values.get("digits", "").strip()
    lang_key  = request.values.get("lang", "1")
    retry     = int(request.values.get("retry", 0))

    lang = LANGUAGES.get(lang_key, LANGUAGES["1"])

    # ── Validate department input ──
    if digit not in ("1", "2"):
        if retry >= MAX_RETRIES:
            return exoml(
                say("We could not understand your input. Transferring you now.", lang["code"]) +
                "\n" + transfer_sip(DEFAULT_SIP)
            )
        # Retry department menu
        retry_url = build_url("/ivr/department", {"lang": lang_key, "retry": retry + 1})
        return exoml(gather(
            action_url=retry_url,
            num_digits=1,
            timeout=5,
            content=say(lang["greet"], lang["code"])
        ))

    # ── Determine SIP trunk ──
    trunk_key = f"{lang_key}_{digit}"
    sip_uri   = SIP_TRUNKS.get(trunk_key, DEFAULT_SIP)

    dept_name = "Service" if digit == "1" else "Dealer Help Desk"
    print(f"[IVR] Caller → Lang: {lang['name']} | Dept: {dept_name} | SIP: {sip_uri}")

    # ── Transfer announcement ──
    if digit == "1":
        transfer_msg = {
            "en-IN": "Please hold, transferring you to our Service team.",
            "hi-IN": "कृपया प्रतीक्षा करें, हम आपको सेवा टीम से जोड़ रहे हैं।",
            "ta-IN": "தயவுசெய்து காத்திருங்கள், உங்களை சேவை குழுவிடம் இணைக்கிறோம்.",
            "te-IN": "దయచేసి వేచి ఉండండి, మీరు సేవా బృందానికి బదిలీ అవుతున్నారు.",
            "kn-IN": "ದಯವಿಟ್ಟು ನಿರೀಕ್ಷಿಸಿ, ನಿಮ್ಮನ್ನು ಸೇವಾ ತಂಡಕ್ಕೆ ವರ್ಗಾಯಿಸಲಾಗುತ್ತಿದೆ.",
            "bn-IN": "অনুগ্রহ করে অপেক্ষা করুন, আপনাকে সেবা দলের কাছে স্থানান্তরিত করা হচ্ছে।",
            "mr-IN": "कृपया थांबा, आपल्याला सेवा संघाकडे हस्तांतरित केले जात आहे.",
            "gu-IN": "કૃપા કરીને રાહ જુઓ, તમને સેવા ટીમ સાથે જોડવામાં આવી રહ્યા છો.",
            "ml-IN": "ദയവായി കാത്തിരിക്കൂ, നിങ്ങളെ സേവന ടീമിലേക്ക് കൈമാറ്റം ചെയ്യുന്നു.",
        }
    else:
        transfer_msg = {
            "en-IN": "Please hold, transferring you to our Dealer Help Desk.",
            "hi-IN": "कृपया प्रतीक्षा करें, हम आपको डीलर हेल्प डेस्क से जोड़ रहे हैं।",
            "ta-IN": "தயவுசெய்து காத்திருங்கள், உங்களை டீலர் உதவி மையத்துடன் இணைக்கிறோம்.",
            "te-IN": "దయచేసి వేచి ఉండండి, మీరు డీలర్ హెల్ప్ డెస్క్‌కు బదిలీ అవుతున్నారు.",
            "kn-IN": "ದಯವಿಟ್ಟು ನಿರೀಕ್ಷಿಸಿ, ನಿಮ್ಮನ್ನು ಡೀಲರ್ ಹೆಲ್ಪ್ ಡೆಸ್ಕ್‌ಗೆ ವರ್ಗಾಯಿಸಲಾಗುತ್ತಿದೆ.",
            "bn-IN": "অনুগ্রহ করে অপেক্ষা করুন, আপনাকে ডিলার হেল্প ডেস্কে স্থানান্তরিত করা হচ্ছে।",
            "mr-IN": "कृपया थांबा, आपल्याला डीलर हेल्प डेस्ककडे हस्तांतरित केले जात आहे.",
            "gu-IN": "કૃપા કરીને રાહ જુઓ, તમને ડીલર હેલ્પ ડેસ્ક સાથે જોડવામાં આવી રહ્યા છો.",
            "ml-IN": "ദയവായി കാത്തിരിക്കൂ, നിങ്ങളെ ഡീലർ ഹെൽപ് ഡെസ്‌കിലേക്ക് കൈമാറ്റം ചെയ്യുന്നു.",
        }

    announcement = say(
        transfer_msg.get(lang["code"], transfer_msg["en-IN"]),
        lang["code"]
    )

    return exoml(announcement + "\n" + transfer_sip(sip_uri))


# ─────────────────────────────────────────────────────────────
# STEP 4 — Fallback (no input / call dropped mid-flow)
# ─────────────────────────────────────────────────────────────

@app.route("/ivr/fallback", methods=["GET", "POST"])
def fallback():
    """Called if anything goes wrong. Transfers to default SIP trunk."""
    return exoml(
        say("We are sorry for the inconvenience. Please hold while we connect you.", "en-IN") +
        "\n" + transfer_sip(DEFAULT_SIP)
    )


# ─────────────────────────────────────────────────────────────
# HEALTH CHECK
# ─────────────────────────────────────────────────────────────

@app.route("/health", methods=["GET"])
def health():
    return {"status": "ok", "service": "Hindware IVR Webhook"}, 200


# ─────────────────────────────────────────────────────────────
# MAIN
# ─────────────────────────────────────────────────────────────

if __name__ == "__main__":
    print("=" * 60)
    print("  Hindware IVR Webhook starting on http://0.0.0.0:5000")
    print("=" * 60)
    print("  Endpoints:")
    print("   POST /ivr/welcome     ← Set this as your Exotel Passthru URL")
    print("   POST /ivr/language    ← Called after language selection")
    print("   POST /ivr/department  ← Called after department selection")
    print("   POST /ivr/fallback    ← Set this as your Exotel fallback URL")
    print("   GET  /health          ← Health check")
    print("=" * 60)
    app.run(host="0.0.0.0", port=5000, debug=True)
