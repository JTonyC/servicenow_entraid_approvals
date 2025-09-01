def test_index_no_user(client):
    resp = client.get("/")
    assert resp.status_code == 200
    assert b"Approvals" in resp.data or b"Requests" in resp.data

def test_index_with_user(client, monkeypatch):
    mock_approvals = [
        {
            "state": "New",
            "number": "CHG001",
            "short_description": "Test change 1",
            "opened_by": "User A",
            "assignment_group": "Group 1",
            "assigned_to": "Assignee 1",
            "start_date": "2025-09-01",
            "end_date": "2025-09-02"
        },
        {
            "state": "In Progress",
            "number": "CHG002",
            "short_description": "Test change 2",
            "opened_by": "User B",
            "assignment_group": "Group 2",
            "assigned_to": "Assignee 2",
            "start_date": "2025-09-03",
            "end_date": "2025-09-04"
        }
    ]

    monkeypatch.setattr(
        "app.fetch_servicenow_approvals",
        lambda token: {
            "approvals_by_type": {
                "Change Requests": mock_approvals
            }
        }
    )

    with client.session_transaction() as sess:
        sess["user"] = {"name": "Test User"}
        sess["access_token"] = "fake"

    resp = client.get("/")
    assert resp.status_code == 200
    assert b"CHG001" in resp.data

def test_refresh_no_user(client):
    resp = client.get("/refresh")
    assert resp.status_code in (301, 302)  # redirect to login

def test_refresh_with_user(client, monkeypatch):
    # Mock approvals list with all fields the template expects
    mock_approvals = [
        {
            "state": "New",
            "number": "CHG001",
            "short_description": "Test change 1",
            "opened_by": "User A",
            "assignment_group": "Group 1",
            "assigned_to": "Assignee 1",
            "start_date": "2025-09-01",
            "end_date": "2025-09-02"
        },
        {
            "state": "In Progress",
            "number": "CHG002",
            "short_description": "Test change 2",
            "opened_by": "User B",
            "assignment_group": "Group 2",
            "assigned_to": "Assignee 2",
            "start_date": "2025-09-03",
            "end_date": "2025-09-04"
        }
    ]

    # approvals_by_type maps type → list of approvals
    mock_approvals_by_type = {
        "Change Requests": mock_approvals
    }

    # Monkeypatch to return the dict shape your /refresh route passes to the template
    monkeypatch.setattr(
        "app.fetch_servicenow_approvals",
        lambda token: {
            "approvals_by_type": mock_approvals_by_type
        }
    )

    with client.session_transaction() as sess:
        sess["user"] = {"name": "Test User"}
        sess["access_token"] = "fake"

    resp = client.get("/refresh")
    assert resp.status_code == 200
    assert b"CHG001" in resp.data