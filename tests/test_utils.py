from app import flatten_approval, datetimeformat

def test_flatten_full_record():
    record = {"state": "open", "number": "CHG001"}
    flat = flatten_approval(record)
    assert flat["state"] == "open"
    assert flat["number"] == "CHG001"

def test_flatten_nested_display_value():
    record = {"details": {"state": {"display_value": "closed"}}}
    flat = flatten_approval(record)
    assert flat["state"] == "closed"

def test_flatten_non_dict():
    flat = flatten_approval("not a dict")
    assert all(v == "" for v in flat.values())

def test_datetimeformat_valid():
    assert datetimeformat("2025-09-01T12:00:00Z") == "01 Sep 2025, 12:00"

def test_datetimeformat_invalid():
    assert datetimeformat("not-a-date") == "not-a-date"