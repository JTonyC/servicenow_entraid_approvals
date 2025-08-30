from flask import Flask, render_template, redirect, request, session, url_for, jsonify
from datetime import datetime
import msal
import os
import requests

from werkzeug.middleware.proxy_fix import ProxyFix

app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET", "dev-secret")
app.config.update(
    SESSION_COOKIE_SECURE=True,       # Only send cookie over HTTPS
    SESSION_COOKIE_SAMESITE="Lax",    # Allow redirect back from Azure AD
    SESSION_COOKIE_HTTPONLY=True      # Mitigate XSS
)

# Ensure Flask sees correct scheme/host behind Azure proxy
app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)
app.config['PREFERRED_URL_SCHEME'] = 'https'

# Azure AD config
CLIENT_ID = os.getenv("AZURE_CLIENT_ID")
CLIENT_SECRET = os.getenv("AZURE_CLIENT_SECRET")
TENANT_ID = os.getenv("AZURE_TENANT_ID")
AUTHORITY = f"https://login.microsoftonline.com/{TENANT_ID}"
SCOPE = [os.getenv("AZURE_SCOPE", "api://db86ab2d-7ee6-4148-995e-ee2ab772c5f0/approvals.read")]


SN_INSTANCE = "https://dev217486.service-now.com"
SN_API_PATH = "/api/x_1680431_apis/bupahome_approvals_api/approvals"

def build_msal_app(cache=None):
    return msal.ConfidentialClientApplication(
        client_id=CLIENT_ID,
        client_credential=CLIENT_SECRET,
        authority=AUTHORITY,
        token_cache=cache
    )

@app.route("/")
def index():
    if "user" in session:
        token = session.get("access_token")
        approvals = fetch_servicenow_approvals(token) if token else []
        return render_template("index.html", user=session["user"], approvals=approvals)
    return render_template("index.html", user=None, approvals=None)

@app.route("/refresh")
def refresh():
    if "user" in session:
        token = session.get("access_token")
        approvals = fetch_servicenow_approvals(token) if token else []
        return render_template("index.html", user=session["user"], approvals=approvals)
    return redirect(url_for("login"))

@app.route("/login")
def login():
    redirect_uri = url_for("authorized", _external=True, _scheme="https")
    msal_app = build_msal_app()
    auth_url = msal_app.get_authorization_request_url(
        scopes=SCOPE,
        redirect_uri=redirect_uri
    )
    return redirect(auth_url)

@app.route("/getAToken")
def authorized():
    redirect_uri = url_for("authorized", _external=True, _scheme="https")
    code = request.args.get("code")
    if not code:
        return "No code returned", 400

    msal_app = build_msal_app()
    result = msal_app.acquire_token_by_authorization_code(
        code=code,
        scopes=SCOPE,
        redirect_uri=redirect_uri
    )

    if "access_token" in result:
        id_claims = result.get("id_token_claims", {})
        session["user"] = {
            "name": id_claims.get("name"),
            "preferred_username": id_claims.get("preferred_username"),
            "oid": id_claims.get("oid")
        }
        session["access_token"] = result["access_token"]
        return redirect(url_for("index"))
    else:
        return result, 400

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("index"))

def flatten_approval(record):

    #Flatten an approval record so the five desired fields are always at the top level.
    #Looks in the top level first, then in the first nested dict if needed.
    target_fields = ["approval_state", "short_description", "requested_by", "opened_at", "urgency"]
    flat = {}

    if not isinstance(record, dict):
        return {field: "" for field in target_fields}

    # Look at top-level first
    for field in target_fields:
        val = record.get(field)
        if isinstance(val, dict) and "display_value" in val:
            flat[field] = val["display_value"]
        elif val not in (None, ""):
            flat[field] = val

    # If missing, look inside first nested dict
    for val in record.values():
        if isinstance(val, dict):
            for field in target_fields:
                if field not in flat or flat[field] in (None, ""):
                    subval = val.get(field)
                    if isinstance(subval, dict) and "display_value" in subval:
                        flat[field] = subval["display_value"]
                    elif subval not in (None, ""):
                        flat[field] = subval
    # Ensure all keys exist
    for field in target_fields:
        flat.setdefault(field, "")

    print("Flattened approval:", flat)
    return flat

def fetch_servicenow_approvals(access_token):
    if not access_token:
        return []

    url = f"{SN_INSTANCE}{SN_API_PATH}"
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Accept": "application/json"
    }
    resp = requests.get(url, headers=headers)
    print("SN status:", resp.status_code)
    print("SN raw:", resp.text)

    try:
        data = resp.json()
    except ValueError:
        return [{"error": resp.status_code, "details": resp.text}]

    if resp.status_code == 200:
        approvals = data.get("result", {}).get("approvals", {})
       # Combine all approval lists across types
        all_records = []
        for record_type, records in approvals.items():
            if isinstance(records, list):
                all_records.extend(records)
        return [flatten_approval(r) for r in all_records]
    else:
        return [{"error": resp.status_code, "details": data}]

@app.template_filter('datetimeformat')
def datetimeformat(value, format='%d %b %Y, %H:%M'):
    try:
        return datetime.fromisoformat(value.replace('Z', '+00:00')).strftime(format)
    except Exception:
        return value

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", 5000)), debug=True)