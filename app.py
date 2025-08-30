from flask import Flask, redirect, request, session, url_for, jsonify
import msal
import os
from werkzeug.middleware.proxy_fix import ProxyFix

app = Flask(__name__)
app.secret_key = os.getenv("FLASK_SECRET", "dev-secret")

# Ensure Flask sees correct scheme/host behind Azure proxy
app.wsgi_app = ProxyFix(app.wsgi_app, x_proto=1, x_host=1)
app.config['PREFERRED_URL_SCHEME'] = 'https'

# Azure AD config
CLIENT_ID = os.getenv("AZURE_CLIENT_ID")
CLIENT_SECRET = os.getenv("AZURE_CLIENT_SECRET")
TENANT_ID = os.getenv("AZURE_TENANT_ID")
AUTHORITY = f"https://login.microsoftonline.com/{TENANT_ID}"
SCOPE = [os.getenv("AZURE_SCOPE", "api://db86ab2d-7ee6-4148-995e-ee2ab772c5f0/approvals.read")]
REDIRECT_URI = os.getenv(
    "REDIRECT_URI",
    "https://tcazr-test-webapp-duejaaf5f2dbacgu.uksouth-01.azurewebsites.net/getAToken"
)
# Comment for push
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
        return f"Hello {session['user']['name']}! <a href='/logout'>Logout</a>"
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
    if "error" in request.args:
        return f"Error: {request.args['error']} - {request.args.get('error_description')}", 400

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
        # Decode ID token claims for user info
        id_claims = result.get("id_token_claims", {})
        session["user"] = {
            "name": id_claims.get("name"),
            "preferred_username": id_claims.get("preferred_username"),
            "oid": id_claims.get("oid")
        }
        session["access_token"] = result["access_token"]
        return redirect(url_for("index"))
    else:
        return jsonify(result), 400

@app.route("/logout")
def logout():
    session.clear()
    return redirect(url_for("index"))

if __name__ == "__main__":
    app.run(host="0.0.0.0", port=int(os.getenv("PORT", 5000)), debug=True)