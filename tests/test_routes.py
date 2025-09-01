def test_index_no_user(client):
    resp = client.get("/")
    assert resp.status_code == 200
    assert b"Approvals" in resp.data or b"Requests" in resp.data

def test_index_with_user(client, monkeypatch):
    monkeypatch.setattr("app.fetch_servicenow_approvals", lambda token: {"Change Requests": []})
    with client.session_transaction() as sess:
        sess["user"] = {"name": "Test User"}
        sess["access_token"] = "fake"
    resp = client.get("/")
    assert resp.status_code == 200

def test_refresh_no_user(client):
    resp = client.get("/refresh")
    assert resp.status_code in (301, 302)  # redirect to login

def test_refresh_with_user(client, monkeypatch):
    monkeypatch.setattr("app.fetch_servicenow_approvals", lambda token: {"Change Requests": []})
    with client.session_transaction() as sess:
        sess["user"] = {"name": "Test User"}
        sess["access_token"] = "fake"
    resp = client.get("/refresh")
    assert resp.status_code == 200