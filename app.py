from flask import Flask, render_template, redirect, request, session, jsonify, url_for
import msal
import requests
import os
import jwt
import base64
import hashlib
import secrets
from werkzeug.middleware.proxy_fix import ProxyFix

app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET", "dev-secret")

app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1)
app.config['PREFERRED_URL_SCHEME'] = 'https'

# --- Config via Environment ---
CLIENT_ID = os.getenv("AZURE_CLIENT_ID")
TENANT_ID = os.getenv("AZURE_TENANT_ID")
AUTHORITY = f"https://login.microsoftonline.com/{TENANT_ID}"
SCOPE = [os.getenv("AZURE_SCOPE", f"api://{CLIENT_ID}/approvals.read")]
SERVICE_NOW_API = os.getenv("SERVICE_NOW_API")
REDIRECT_URI = "https://tcazr-test-webapp-duejaaf5f2dbacgu.uksouth-01.azurewebsites.net/getAToken"

# --- MSAL App Factory ---
def get_msal_app():
    return msal.PublicClientApplication(
        client_id=CLIENT_ID,
        authority=AUTHORITY
    )

# --- PKCE helpers ---
def generate_pkce_pair():
    code_verifier = base64.urlsafe_b64encode(secrets.token_bytes(64)).rstrip(b'=').decode('utf-8')
    code_challenge = base64.urlsafe_b64encode(
        hashlib.sha256(code_verifier.encode("utf-8")).digest()
    ).rstrip(b'=').decode('utf-8')
    return code_verifier, code_challenge

# --- JWT decoder ---
def decode_jwt(token: str):
    try:
        return jwt.decode(token, options={"verify_signature": False})
    except Exception as ex:
        return {"error": f"Failed to decode token: {ex}"}

@app.route("/")
def index():
    user = session.get("user")
    if user:
        return render_template("dashboard.html", user=user)
    return render_template("signin.html")

@app.route("/login")
def login():
    msal_app = get_msal_app()
    code_verifier, code_challenge = generate_pkce_pair()
    session["code_verifier"] = code_verifier

    state = secrets.token_urlsafe(32)
    session["state"] = state

    auth_url = msal_app.get_authorization_request_url(
        scopes=SCOPE,
        redirect_uri=REDIRECT_URI,
        state=state,
        code_challenge=code_challenge,
        code_challenge_method="S256",
    )
    return redirect(auth_url)

@app.route("/getAToken")
def authorized():
    state = request.args.get("state")
    if state != session.get("state"):
        return "Invalid state parameter", 400

    code = request.args.get("code")
    if not code:
        return "Missing authorization code", 400

    code_verifier = session.pop("code_verifier", None)
    if not code_verifier:
        return "Missing PKCE code_verifier", 400

    msal_app = get_msal_app()
    result = msal_app.acquire_token_by_authorization_code(
        code=code,
        scopes=SCOPE,
        redirect_uri=REDIRECT_URI,
        code_verifier=code_verifier
    )

    session.pop("state", None)

    if "access_token" not in result:
        return f"Token acquisition failed: {result}", 400

    session["access_token"] = result["access_token"]
    session["id_token"] = result.get("id_token")

    id_claims = decode_jwt(session["id_token"]) if session.get("id_token") else {}
    at_claims = decode_jwt(session["access_token"]) if session.get("access_token") else {}

    session["user"] = {
        "preferred_username": id_claims.get("preferred_username") or at_claims.get("upn"),
        "name": id_claims.get("name") or at_claims.get("name"),
        "oid": id_claims.get("oid") or at_claims.get("oid"),
    }

    return redirect(url_for("welcome"))

@app.route("/token")
def token_view():
    id_token = session.get("id_token")
    access_token = session.get("access_token")

    if not (id_token or access_token):
        return redirect(url_for("login"))

    return jsonify({
        "id_token_claims": decode_jwt(id_token),
        "access_token_claims": decode_jwt(access_token)
    })

@app.route("/approvals")
def approvals():
    token = session.get("access_token")
    if not token:
        return redirect(url_for("login"))

    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/json"
    }
    resp = requests.get(SERVICE_NOW_API, headers=headers)

    try:
        body = resp.json()
    except Exception:
        body = {"raw": resp.text}

    return jsonify({
        "status_code": resp.status_code,
        "body": body
    })

@app.route("/welcome")
def welcome():
    token = session.get("access_token")
    if not token:
        return redirect(url_for("login"))
    decoded = decode_jwt(token)
    return render_template("welcome.html", token=decoded)

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("index"))

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", 5000)), debug=False)