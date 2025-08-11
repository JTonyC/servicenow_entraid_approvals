from flask import Flask, render_template, redirect, request, session, jsonify
import msal
import requests
import os

app = Flask(__name__)
app.secret_key = os.environ.get("FLASK_SECRET", "dev-secret")

CLIENT_ID = "db86ab2d-7ee6-4148-995e-ee2ab772c5f0"
TENANT_ID = "597098e4-5859-4c13-87bf-a9c2b3b130ba"
AUTHORITY = f"https://login.microsoftonline.com/{TENANT_ID}"
SCOPE = ["api://db86ab2d-7ee6-4148-995e-ee2ab772c5f0/approvals.read"]
REDIRECT_URI = "http://localhost:5000/getAToken"

SERVICE_NOW_API = "https://dev217486.service-now.com/api/x_1680431_apis/bupahome_approvals_api/approvals"

@app.route("/")
def index():
    return render_template("index.html", user=session.get("user"))

@app.route("/login")
def login():
    msal_app = msal.ConfidentialClientApplication(
        CLIENT_ID,
        authority=AUTHORITY,
        client_credential=os.environ.get("CLIENT_SECRET")
    )
    auth_url = msal_app.get_authorization_request_url(
        scopes=SCOPE,
        redirect_uri=REDIRECT_URI
    )
    return redirect(auth_url)

@app.route("/getAToken")
def authorized():
    code = request.args.get("code")
    msal_app = msal.ConfidentialClientApplication(
        CLIENT_ID,
        authority=AUTHORITY,
        client_credential=os.environ.get("CLIENT_SECRET")
    )
    token_response = msal_app.acquire_token_by_authorization_code(
        code,
        scopes=SCOPE,
        redirect_uri=REDIRECT_URI
    )
    session["access_token"] = token_response.get("access_token")
    session["user"] = token_response.get("id_token_claims")
    return redirect("/")

@app.route("/approvals")
def approvals():
    token = session.get("access_token")
    if not token:
        return redirect("/login")

    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/json"
    }
    resp = requests.get(SERVICE_NOW_API, headers=headers)
    return jsonify(resp.json())

if __name__ == "__main__":
    app.run(debug=True)

