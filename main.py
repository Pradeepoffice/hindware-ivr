"""
Exotel Callback API
--------------------
Receives the callback Exotel sends (e.g. from a Passthru applet after a
Gather Digits step) when a customer presses a key during a call, logs the
details, and responds with HTTP 200 so Exotel's flow continues.

Run locally:
    uvicorn main:app --reload

Deploy on Render:
    Start command -> uvicorn main:app --host 0.0.0.0 --port $PORT
"""

from fastapi import FastAPI, Request
from fastapi.responses import PlainTextResponse
import logging
from datetime import datetime

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger("exotel-api")

app = FastAPI(title="Exotel Callback API")


@app.get("/")
def health_check():
    """Simple root route so you can confirm the service is live."""
    return {"status": "running", "message": "Exotel callback API is live"}


async def handle_exotel_event(request: Request):
    """
    Shared handler for GET and POST.
    Exotel may send data as query params (GET) or form-encoded body (POST).
    We capture both, plus a few commonly used fields for easy reading.
    """
    query_params = dict(request.query_params)

    form_params = {}
    if request.method == "POST":
        try:
            form = await request.form()
            form_params = dict(form)
        except Exception:
            # Body might be empty or not form-encoded; ignore safely
            form_params = {}

    # Merge everything Exotel sent (form data takes priority if both exist)
    all_params = {**query_params, **form_params}

    # Commonly sent Exotel fields (names can vary slightly by flow setup)
    call_sid = all_params.get("CallSid")
    from_number = all_params.get("From") or all_params.get("CallFrom")
    to_number = all_params.get("To") or all_params.get("CallTo")
    digits_pressed = all_params.get("digits") or all_params.get("Digits")
    call_status = all_params.get("CallStatus")
    direction = all_params.get("Direction")

    logger.info("----- Exotel callback received -----")
    logger.info("Timestamp: %s", datetime.utcnow().isoformat())
    logger.info("Method: %s", request.method)
    logger.info("CallSid: %s", call_sid)
    logger.info("From: %s", from_number)
    logger.info("To: %s", to_number)
    logger.info("Digits Pressed: %s", digits_pressed)
    logger.info("CallStatus: %s", call_status)
    logger.info("Direction: %s", direction)
    logger.info("All params: %s", all_params)
    logger.info("-------------------------------------")

    return all_params


@app.get("/exotel-callback")
async def exotel_callback_get(request: Request):
    await handle_exotel_event(request)
    # Exotel just needs a 200 OK to proceed; plain text keeps it simple
    return PlainTextResponse(content="OK", status_code=200)


@app.post("/exotel-callback")
async def exotel_callback_post(request: Request):
    await handle_exotel_event(request)
    return PlainTextResponse(content="OK", status_code=200)
