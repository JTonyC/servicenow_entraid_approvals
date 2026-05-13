import json
import os
import subprocess
from datetime import datetime, timedelta
from pathlib import Path


def write_json(path, data):
    with open(path, "w") as f:
        json.dump(data, f)


def test_perf_payload_full(tmp_path, monkeypatch):
    # --- Arrange ---
    # Create fake input file
    input_file = tmp_path / "sn-devops-results.json"
    write_json(input_file, {
        "metrics": {
            "iterations": {"count": 120},
            "http_reqs": {"rate": 2},
            "vus_max": {"max": 50},
            "http_req_duration": {"stddev": 0.123},
            "http_req_duration{expected_response:true}": {
                "max": 0.5,
                "min": 0.1,
                "avg": 0.2,
                "p(90)": 0.4
            }
        }
    })

    # Patch working directory so script reads our file
    monkeypatch.chdir(tmp_path)

    # Patch environment variables
    monkeypatch.setenv("SN_TOOL_ID", "tool-123")
    monkeypatch.setenv("GITHUB_WORKFLOW", "CI")
    monkeypatch.setenv("GITHUB_REPOSITORY", "my/repo")
    monkeypatch.setenv("GITHUB_RUN_NUMBER", "42")
    monkeypatch.setenv("GITHUB_RUN_ID", "999")
    monkeypatch.setenv("GITHUB_RUN_ATTEMPT", "1")

    # Freeze time by patching the system clock
    fixed_time = datetime(2024, 1, 1, 12, 0, 0)
    monkeypatch.setenv("FAKE_NOW", fixed_time.isoformat())

    # --- Act ---
    # Run the JS script
    script_path = Path(__file__).resolve().parents[1] / "scripts" / "transform-k6-summary.js"

    result = subprocess.run(
        ["node", str(script_path)],
        capture_output=True,
        text=True
    )

    # --- Assert ---
    assert result.returncode == 0
    assert "Performance Test Summary payload written" in result.stdout

    # Load output file
    output_file = tmp_path / "sn-devops-perf.json"
    assert output_file.exists()

    payload = json.loads(output_file.read_text())

    # Duration: 120 iterations / 2 rps = 60 seconds
    assert payload["duration"] == 60
    assert payload["maximumVirtualUsers"] == 50
    assert payload["throughput"] == "120/min"

    assert payload["maximumTime"] == 500
    assert payload["minimumTime"] == 100
    assert payload["averageTime"] == 200
    assert payload["ninetyPercent"] == 400
    assert payload["standardDeviation"] == 123

    # Timestamps: start = finish - 60 seconds
    finish = datetime.fromisoformat(payload["finishTime"].replace("Z", ""))
    start = datetime.fromisoformat(payload["startTime"].replace("Z", ""))

    assert finish - start == timedelta(seconds=60)