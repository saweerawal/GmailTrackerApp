import os
import base64
import re
from flask import Flask, redirect, request, session, jsonify
from flask_cors import CORS
from google.oauth2.credentials import Credentials
from google_auth_oauthlib.flow import Flow
from googleapiclient.discovery import build
from google.auth.transport.requests import Request
from flask import send_from_directory

app = Flask(__name__, static_folder="static", static_url_path="")

# FIXED: must be a stable string, not random — random resets on every restart
# and breaks the session between login and callback
app.secret_key = "mailtracker-fixed-secret-2024"
app.config["SESSION_COOKIE_SAMESITE"] = "Lax"
app.config["SESSION_COOKIE_SECURE"] = False  # localhost only

CORS(app, supports_credentials=True)
os.environ["OAUTHLIB_INSECURE_TRANSPORT"] = "1"

GMAIL_SCOPES = ["https://www.googleapis.com/auth/gmail.readonly"]
CLIENT_SECRETS_FILE = os.path.join(os.path.dirname(__file__), "credentials.json")
REDIRECT_URI = "http://127.0.0.1:5000/oauth/callback"


@app.route("/auth/login")
def login():
    flow = Flow.from_client_secrets_file(CLIENT_SECRETS_FILE, scopes=GMAIL_SCOPES)
    flow.redirect_uri = REDIRECT_URI
    auth_url, state = flow.authorization_url(
        access_type="offline",
        include_granted_scopes="true",
        prompt="consent"
    )
    session["oauth_state"] = state
    session.modified = True
    # FIXED: redirect directly instead of returning JSON + opening popup
    # Popup windows don't share session cookies reliably on Mac/Chrome
    return redirect(auth_url)


@app.route("/oauth/callback")
def callback():
    state = session.get("oauth_state")
    if not state:
        # Fallback: proceed without state check if session was lost
        flow = Flow.from_client_secrets_file(CLIENT_SECRETS_FILE, scopes=GMAIL_SCOPES)
    else:
        flow = Flow.from_client_secrets_file(
            CLIENT_SECRETS_FILE,
            scopes=GMAIL_SCOPES,
            state=state
        )

    flow.redirect_uri = REDIRECT_URI

    try:
        flow.fetch_token(authorization_response=request.url)
    except Exception as e:
        return f"<h2>Auth error: {e}</h2><p><a href='/'>Go back</a></p>", 400

    creds = flow.credentials
    session["credentials"] = {
        "token": creds.token,
        "refresh_token": creds.refresh_token,
        "token_uri": creds.token_uri,
        "client_id": creds.client_id,
        "client_secret": creds.client_secret,
        "scopes": list(creds.scopes),
    }
    session.modified = True
    return redirect("http://127.0.0.1:5000?connected=1")


@app.route("/auth/status")
def auth_status():
    return jsonify({"connected": "credentials" in session})


@app.route("/auth/logout")
def logout():
    session.clear()
    return jsonify({"ok": True})


def get_gmail_service():
    creds_data = session.get("credentials")
    if not creds_data:
        return None
    creds = Credentials(**creds_data)
    if creds.expired and creds.refresh_token:
        creds.refresh(Request())
        session["credentials"]["token"] = creds.token
    return build("gmail", "v1", credentials=creds)


def parse_date(date_str):
    import email.utils, time, datetime
    try:
        parsed = email.utils.parsedate(date_str)
        if parsed:
            t = time.mktime(parsed)
            return datetime.datetime.fromtimestamp(t).strftime("%b %d")
    except Exception:
        pass
    return date_str[:10] if date_str else ""


@app.route("/api/emails")
def fetch_emails():
    service = get_gmail_service()
    if not service:
        return jsonify({"error": "not_connected"}), 401

    max_results = int(request.args.get("max", 20))
    query = request.args.get("q", "is:unread")

    results = service.users().messages().list(
        userId="me", maxResults=max_results, q=query
    ).execute()
    messages = results.get("messages", [])

    emails = []
    for msg in messages:
        full = service.users().messages().get(
            userId="me", id=msg["id"], format="full"
        ).execute()
        headers = {h["name"]: h["value"] for h in full["payload"].get("headers", [])}

        raw_from = headers.get("From", "")
        from_name = re.sub(r"<[^>]+>", "", raw_from).strip().strip('"')
        from_email_match = re.search(r"<([^>]+)>", raw_from)
        from_email = from_email_match.group(1) if from_email_match else raw_from

        emails.append({
            "id": msg["id"],
            "subject": headers.get("Subject", "(no subject)"),
            "from_name": from_name or from_email,
            "from_email": from_email,
            "date": parse_date(headers.get("Date", "")),
            "snippet": full.get("snippet", "")[:200],
        })

    return jsonify({"emails": emails})


@app.route("/", defaults={"path": ""})
@app.route("/<path:path>")
def serve(path):
    if path != "" and os.path.exists(os.path.join(app.static_folder, path)):
        return send_from_directory(app.static_folder, path)
    return send_from_directory(app.static_folder, "index.html")


if __name__ == "__main__":
    app.run(debug=True, port=5000)
