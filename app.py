from flask import Flask, request, Response

app = Flask(__name__)

BASE_URL = "https://hindware-ivr.onrender.com"
MAX_RETRIES = 3

LANGUAGES = {
    "1": {"name": "English",   "greet": "Welcome to Hindware. Please press 1 for Service, press 2 for Dealer Help Desk."},
    "2": {"name": "Hindi",     "greet": "Hindware mein aapka swagat hai. Seva ke liye 1 dabayen, Dealer Help Desk ke liye 2 dabayen."},
    "3": {"name": "Tamil",     "greet": "Hindware-il ungalai varaverkirom. Sevaikku 1 anukavum, Dealer Help Desk-ku 2 anukavum."},
    "4": {"name": "Telugu",    "greet": "Hindware ki swaagatam. Seva kosam 1 nokkandi, Dealer Help Desk kosam 2 nokkandi."},
    "5": {"name": "Kannada",   "greet": "Hindware ge swagata. Sevege 1 ottiri, Dealer Help Desk ge 2 ottiri."},
    "6": {"name": "Bengali",   "greet": "Hindware e apnake swagat. Seva r jonno 1 chapon, Dealer Help Desk r jonno 2 chapon."},
    "7": {"name": "Marathi",   "greet": "Hindware madhe aapale swagat. Seva sathi 1 daba, Dealer Help Desk sathi 2 daba."},
    "8": {"name": "Gujarati",  "greet": "Hindware ma aapnu swagat. Seva mate 1 dabavo, Dealer Help Desk mate 2 dabavo."},
    "9": {"name": "Malayalam", "greet": "Hindware-il swaagatham. Sevaykkay 1 amarthuka, Dealer Help Desk-kkay 2 amarthuka."},
}

SIP_TRUNK = "sip:trmum1f6b810c5a7c3e6d122197n@sip.exotel.com"


def make_xml(body):
    return Response(
        '<?xml version="1.0" encoding="UTF-8"?><Response>' + body + '</Response>',
        mimetype="application/xml"
    )


def say(text):
    safe = text.replace("&", "and").replace("<", "").replace(">", "")
    return '<Say voice="female">' + safe + '</Say>'


def gather(action, digits, timeout, body):
    return '<Gather action="' + action + '" numDigits="' + str(digits) + '" timeout="' + str(timeout) + '">' + body + '</Gather>'


def dial(sip):
    return '<Dial><Number>' + sip + '</Number></Dial>'


def url(path, params):
    parts = []
    for k, v in params.items():
        parts.append(str(k) + "=" + str(v))
    return BASE_URL + path + "?" + "&amp;".join(parts)


@app.route("/ivr/welcome", methods=["GET", "POST"])
def welcome():
    action = url("/ivr/language", {"retry": "0"})
    prompts = (
        say("For English press 1.") +
        say("Hindi ke liye 2 dabayen.") +
        say("Tamil il 3 anukkavum.") +
        say("Telugu lo 4 nakkandi.") +
        say("Kannada ge 5 ottiri.") +
        say("Bangla te 6 chaapon.") +
        say("Marathi sathi 7 daba.") +
        say("Gujarati mate 8 dabavo.") +
        say("Malayalam il 9 arakkuka.")
    )
    return make_xml(gather(action, 1, 15, prompts))


@app.route("/ivr/language", methods=["GET", "POST"])
def language():
    digit = request.values.get("digits", "").strip()
    retry = int(request.values.get("retry", "0"))

    if digit not in LANGUAGES:
        if retry >= MAX_RETRIES:
            return make_xml(say("Transferring you now.") + dial(SIP_TRUNK))
        action = url("/ivr/language", {"retry": str(retry + 1)})
        prompts = (
            say("Invalid input. Please try again.") +
            say("For English press 1.") +
            say("Hindi ke liye 2 dabayen.")
        )
        return make_xml(gather(action, 1, 15, prompts))

    lang = LANGUAGES[digit]
    action = url("/ivr/department", {"lang": digit, "retry": "0"})
    return make_xml(gather(action, 1, 10, say(lang["greet"])))


@app.route("/ivr/department", methods=["GET", "POST"])
def department():
    digit    = request.values.get("digits", "").strip()
    lang_key = request.values.get("lang", "1")
    retry    = int(request.values.get("retry", "0"))
    lang     = LANGUAGES.get(lang_key, LANGUAGES["1"])

    if digit not in ("1", "2"):
        if retry >= MAX_RETRIES:
            return make_xml(say("Transferring you now.") + dial(SIP_TRUNK))
        action = url("/ivr/department", {"lang": lang_key, "retry": str(retry + 1)})
        return make_xml(gather(action, 1, 10, say(lang["greet"])))

    dept = "Service team" if digit == "1" else "Dealer Help Desk"
    return make_xml(say("Please hold, connecting you to our " + dept + ".") + dial(SIP_TRUNK))


@app.route("/ivr/fallback", methods=["GET", "POST"])
def fallback():
    return make_xml(say("Please hold while we connect you.") + dial(SIP_TRUNK))


@app.route("/health", methods=["GET"])
def health():
    return {"status": "ok"}, 200


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
