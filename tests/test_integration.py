from unittest.mock import patch, MagicMock
from app import fetch_servicenow_approvals

@patch("app.requests.get")
def test_fetch_servicenow_approvals_success(mock_get):
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "result": {"approvals": {"change_request": [{}]}}
    }
    mock_get.return_value = mock_resp
    result = fetch_servicenow_approvals("token")
    assert "Change Requests" in result

@patch("app.requests.get")
def test_fetch_servicenow_approvals_no_token(mock_get):
    result = fetch_servicenow_approvals("")
    assert result == []
    mock_get.assert_not_called()