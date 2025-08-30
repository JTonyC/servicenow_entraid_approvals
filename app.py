from flask import Flask, redirect, request, session, url_for, render_template_string, jsonify
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
redirect_uri = url_for("authorized", _external=True, _scheme="https")


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
        approvals = fetch_servicenow_approvals(session["access_token"])
        # Simple HTML table rendering
        html = """
        <h2>Hello {{ user.name }}!</h2>
        <h3>Your Approvals</h3>
        {% if approvals %}
        <table border="1" cellpadding="5">
            <tr>
                {% for key in approvals[0].keys() %}
                <th>{{ key }}</th>
                {% endfor %}
            </tr>
            {% for row in approvals %}
            <tr>
                {% for val in row.values() %}
                <td>{{ val }}</td>
                {% endfor %}
            </tr>
            {% endfor %}
        </table>
        {% else %}
        <p>No approvals found.</p>
        {% endif %}
        <p><a href="{{ url_for('logout') }}">Logout</a></p>
        """
        return render_template_string(html, user=session["user"], approvals=approvals)
    return '<a href="/login">Sign in</a>'

@app.route("/login")
def login():
    msal_app = build_msal_app()
    auth_url = msal_app.get_authorization_request_url(
        scopes=SCOPE,
        redirect_uri=REDIRECT_URI
    )
    return redirect(auth_url)

@app.route("/getAToken")
def authorized():
    code = request.args.get("code")
    if not code:
        return "No code returned", 400

    msal_app = build_msal_app()
    result = msal_app.acquire_token_by_authorization_code(
        code=code,
        scopes=SCOPE,
        redirect_uri=REDIRECT_URI
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

def fetch_servicenow_approvals(access_token):
    url = f"{SN_INSTANCE}{SN_API_PATH}"
    headers = {
        "Authorization": f"Bearer {access_token}",
        "Accept": "application/json"
    }
    resp = requests.get(url, headers=headers)
    try:
        data = resp.json()
    except ValueError:
        return [{"error": resp.status_code, "details": resp.text}]

    if resp.status_code == 200:
        result = data.get("result", [])
        return result if isinstance(result, list) else [result]
    else:
        return [{"error": resp.status_code, "details": data}]

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", 5000)), debug=True)