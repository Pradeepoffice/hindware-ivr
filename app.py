from flask import Flask, request, Response

app = Flask(__name__)

BASE_URL = "https://hindware-ivr.onrender.com"

LANGUAGES = {
    "1": "Welcome to Hindware. Please press 1 for Service, press 2 for Dealer Help Desk.",
    "2": "Hindware mein aapka swagat hai. Seva ke liye 1 dabayen, Dealer ke liye 2 dabayen.",
    "3": "Hindware il ungalai varaverkirom. Sevaikku 1 anukavum, Dealer ku 2 anukavum.",
    "4": "Hindware ki swaagatam. Seva kosam 1 nokkandi, Dealer kosam 2 nokkandi.",
    "5": "Hindware ge swagata. Sevege 1 ottiri, Dealer ge 2 ottiri.",
    "6": "Hindware e apnake swagat. Seva r jonno 1 chapon, Dealer jonno 2 chapon.",
    "7": "Hindware madhe swagat. Seva sathi 1 daba, Dealer sathi 2 daba.",
    "8": "Hindware ma swagat. Seva mate 1 dabavo, Dealer mate 2 dabavo.",
    "9": "Hindware il swaagatham. Sevaykkay 1 amarthuka, Dealer kkay 2 amarthuka.",
}

SIP = "sip:trmum1f6b810c5a7c3e6d122197n@sip.exotel.com"


def xml(body):
    return Response(
        '<?xml version="1.0" encoding="UTF-8"?><Response>' + body + '</Response>',
        mimetype="application/xml"
    )

def say(text):
    return '<Say voice="female">' + text + '</Say>'

def dial():
    return '<Dial><Number>' + SIP + '</Number></Dial>'


@app.route("/ivr/welcome", methods=["GET", "POST"])
def welcome():
    body = (
        '<Gather action="' + BASE_URL + '/ivr/language" numDigits="1" timeout="15">'
        + say("For English press 1.")
        + say("Hindi ke liye 2 dabayen.")
        + say("Tamil il 3 anukkavum.")
        + say("Telugu lo 4 nakkandi.")
        + say("Kannada ge 5 ottiri.")
        + say("Bangla te 6 chaapon.")
        + say("Marathi sathi 7 daba.")
        + say("Gujarati mate 8 dabavo.")
        + say("Malayalam il 9 arakkuka.")
        + '</Gather>'
    )
    return xml(body)


@app.route("/ivr/language", methods=["GET", "POST"])
def language():
    digit = request.values.get("digits", "").strip()

    if digit not in LANGUAGES:
        body = (
            '<Gather action="' + BASE_URL + '/ivr/language" numDigits="1" timeout="15">'
            + say("Invalid input. Please try again.")
            + say("For English press 1.")
            + say("Hindi ke liye 2 dabayen.")
            + '</Gather>'
        )
        return xml(body)

    greet = LANGUAGES[digit]
    body = (
        '<Gather action="' + BASE_URL + '/ivr/department/' + digit + '" numDigits="1" timeout="10">'
        + say(greet)
        + '</Gather>'
    )
    return xml(body)


@app.route("/ivr/department/<lang>", methods=["GET", "POST"])
def department(lang):
    digit = request.values.get("digits", "").strip()
    greet = LANGUAGES.get(lang, LANGUAGES["1"])

    if digit == "1":
        return xml(say("Please hold, connecting you to our Service team.") + dial())
    elif digit == "2":
        return xml(say("Please hold, connecting you to our Dealer Help Desk.") + dial())
    else:
        body = (
            '<Gather action="' + BASE_URL + '/ivr/department/' + lang + '" numDigits="1" timeout="10">'
            + say(greet)
            + '</Gather>'
        )
        return xml(body)


@app.route("/ivr/fallback", methods=["GET", "POST"])
def fallback():
    return xml(say("Please hold while we connect you.") + dial())


@app.route("/health", methods=["GET"])
def health():
    return {"status": "ok", "version": "3"}, 200


if __name__ == "__main__":
    app.run(host="0.0.0.0", port=5000, debug=True)
