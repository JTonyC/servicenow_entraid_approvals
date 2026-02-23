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


SN_INSTANCE = "https://dev291784.service-now.com"
SN_API_PATH = "/api/1680431/approvals_dashboard/user"

def build_msal_app(cache=None):
    return msal.ConfidentialClientApplication(
        client_id=CLIENT_ID,
        client_credential=CLIENT_SECRET,
        authority=AUTHORITY,
        token_cache=cache
    )

@app.route("/")
def index():
    if "user" not in session:
        return render_template("index.html", user=None, approvals_by_type={})

    token = session.get("access_token")
    approvals_by_type = fetch_servicenow_approvals(token) or {}
    return render_template(
        "index.html",
        user=session["user"],
        approvals_by_type=approvals_by_type
    )

@app.route("/refresh")
def refresh():
    if "user" not in session:
        return redirect(url_for("login"))

    token = session.get("access_token")
    approvals_by_type = fetch_servicenow_approvals(token) or {}
    return render_template(
        "index.html",
        user=session["user"],
        approvals_by_type=approvals_by_type
    )

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

TYPE_LABELS = {
    "change_request": "Change Requests",
    "sc_req_item": "Requests"
}

def _extract_display_value(value):
    """Extract display_value from dict or return non-empty value."""
    if isinstance(value, dict) and "display_value" in value:
        return value["display_value"]
    if value not in (None, ""):
        return value
    return None

def flatten_approval(record):
    """Flatten approval record to ensure target fields are at top level."""
    target_fields = [
        "state", "number", "short_description", "opened_by",
        "assignment_group", "assigned_to", "start_date", "end_date"
    ]

    if not isinstance(record, dict):
        return {field: "" for field in target_fields}

    flat = {}

    # Extract from top-level fields
    for field in target_fields:
        extracted = _extract_display_value(record.get(field))
        if extracted is not None:
            flat[field] = extracted

    # Fill missing fields from nested dicts
    for nested_value in record.values():
        if not isinstance(nested_value, dict):
            continue

        for field in target_fields:
            if field in flat and flat[field] not in (None, ""):
                continue

            extracted = _extract_display_value(nested_value.get(field))
            if extracted is not None:
                flat[field] = extracted

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

    approvals_by_type = {}

    if resp.status_code == 200:
        approvals = data.get("result", {}).get("approvals", {})
        # Comment code EPIC SCRUM-24
        """for record_type, records in approvals.items():
            if isinstance(records, list):
                 friendly_label = TYPE_LABELS.get(
                    record_type, record_type.replace('_', ' ').title()
                )
            approvals_by_type[friendly_label] = [
                flatten_approval(r) for r in records
            ]"""
        for record_type, records in approvals.items():

            # Always compute the friendly label
            friendly_label = TYPE_LABELS.get(
                record_type,
                record_type.replace('_', ' ').title()
            )

            # Normalise records to a list
            # SN may return {}, None, or a single object depending on ACLs or plugins
            if not isinstance(records, list):
                records = [records] if records else []

            # Flatten each approval record
            approvals_by_type[friendly_label] = [
                flatten_approval(r) for r in records
            ]

    else:
        approvals_by_type["error"] = [
            {"error": resp.status_code, "details": data}
        ]

    return approvals_by_type

@app.template_filter('datetimeformat')
def datetimeformat(value, format='%d %b %Y, %H:%M'):
    try:
        return datetime.fromisoformat(value.replace('Z', '+00:00')).strftime(format)
    except Exception:
        return value

if __name__ == "__main__":
    # The below will flag a security issue in SonarQube, which is communicated too DevOps Change Velocity
    # Resulting in the change being rejected!
    #app.run(host="0.0.0.0", port=int(os.getenv("PORT", 5000)), debug=True)
    app.run(host="127.0.0.1", port=int(os.getenv("PORT", 5000)), debug=False)