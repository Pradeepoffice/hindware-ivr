# Exotel Callback API — Setup & Deployment Guide

A minimal FastAPI service that receives Exotel's callback (e.g. when a
customer presses a key during a call) and responds with `200 OK`.

## Files
- `main.py` — the API
- `requirements.txt` — dependencies

## 1. Push to GitHub
```bash
cd exotel-api
git init
git add .
git commit -m "Exotel callback API"
git branch -M main
git remote add origin https://github.com/<your-username>/<your-repo>.git
git push -u origin main
```

## 2. Deploy on Render
1. Go to https://render.com → **New +** → **Web Service**
2. Connect your GitHub repo
3. Settings:
   - **Environment**: Python 3
   - **Build Command**: `pip install -r requirements.txt`
   - **Start Command**: `uvicorn main:app --host 0.0.0.0 --port $PORT`
4. Click **Create Web Service**. Render gives you a public URL like:
   `https://your-app-name.onrender.com`

## 3. Test it's live
Visit `https://your-app-name.onrender.com/` in a browser — you should see:
```json
{"status": "running", "message": "Exotel callback API is live"}
```

## 4. Configure in Exotel
1. Log into Exotel dashboard → **App Bazaar / Studio**
2. Build your flow: **Start → Gather (collect digits) → Passthru/Custom URL**
3. In the Passthru/Custom URL applet, set the URL to:
   `https://your-app-name.onrender.com/exotel-callback`
4. Choose **GET** or **POST** as the method (this API supports both)
5. Save and publish the flow, then test by calling your Exotel number and pressing a key

## 5. Check the logs
On Render, go to your service → **Logs** tab. You'll see each incoming
callback logged with `CallSid`, `From`, `To`, `Digits Pressed`, etc.

## Notes for testing
- Render's free tier spins down when idle — the first request after
  inactivity can take 20–30 seconds to respond. If your Exotel flow has a
  short timeout, this could cause issues in production (fine for testing).
- Field names like `Digits`/`digits`, `From`/`CallFrom` can vary slightly
  depending on how your Exotel flow is configured — check the logged
  `all_params` line to see the exact keys Exotel is sending you, then adjust
  `main.py` if needed.
