def test_index_no_user(client):
    resp = client.get("/")
    assert resp.status_code == 200
    assert b"Approvals" in resp.data or b"Requests" in resp.data

def test_index_with_user(client, monkeypatch):
    # Mock data shaped like production output
    mock_approvals = [
        {"number": "CHG001", "state": "New"},
        {"number": "CHG002", "state": "In Progress"},
        {"number": "CHG003", "state": "Closed"},
    ]
    mock_approvals_by_type = {
        "Change Requests": mock_approvals
    }

    # Monkeypatch to return the correct shape
    monkeypatch.setattr(
        "app.fetch_servicenow_approvals",
        lambda token: {
            "approvals": mock_approvals,
            "approvals_by_type": mock_approvals_by_type
        }
    )

    with client.session_transaction() as sess:
        sess["user"] = {"name": "Test User"}
        sess["access_token"] = "fake"

    resp = client.get("/")
    assert resp.status_code == 200
    # Optional: check that one of the mock numbers appears in the rendered HTML
    assert b"CHG001" in resp.data

def test_refresh_no_user(client):
    resp = client.get("/refresh")
    assert resp.status_code in (301, 302)  # redirect to login

def test_refresh_with_user(client, monkeypatch):
    monkeypatch.setattr("app.fetch_servicenow_approvals", lambda token: {"approvals_by_type": {"Change Requests": []}})
    with client.session_transaction() as sess:
        sess["user"] = {"name": "Test User"}
        sess["access_token"] = "fake"
    resp = client.get("/refresh")
    assert resp.status_code == 200