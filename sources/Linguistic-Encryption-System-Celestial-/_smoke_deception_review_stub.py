
import json, subprocess, sys
from pathlib import Path

base = Path(__file__).resolve().parent

res1 = subprocess.run(
    [sys.executable, "deception_review_stub.py", "--classification", "CAUTION", "--session-id", "demo-session-1", "--json"],
    cwd=base, capture_output=True, text=True, check=True
)
payload1 = json.loads(res1.stdout)
assert payload1["reason"] == "threshold_not_met"
assert payload1["result"]["mode"] == "null_response"

res2 = subprocess.run(
    [sys.executable, "deception_review_stub.py", "--classification", "GRAVE", "--session-id", "demo-session-1", "--json"],
    cwd=base, capture_output=True, text=True, check=True
)
payload2 = json.loads(res2.stdout)
assert payload2["reason"] == "authorization_missing"
assert payload2["result"]["mode"] == "null_response"

res3 = subprocess.run(
    [
        sys.executable, "deception_review_stub.py",
        "--classification", "GRAVE",
        "--session-id", "demo-session-1",
        "--shadow-policy", "example_shadow_policy",
        "--authorization-ticket", "example_authorization_ticket",
        "--json",
    ],
    cwd=base, capture_output=True, text=True, check=True
)
payload3 = json.loads(res3.stdout)
assert payload3["result"]["status"] == "generated"
assert payload3["result"]["mode"] == "canned_decoy_response"
assert payload3["guardrails"]["non_production"] is True

print("deception simulator smoke test ok")
