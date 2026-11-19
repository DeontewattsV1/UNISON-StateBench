
import subprocess, sys, json
from pathlib import Path

base = Path(__file__).resolve().parent

subprocess.run(
    [sys.executable, "pack_builder.py", "--policy", "example_phaseform_policy.json", "--name", "verify_me", "--passphrase", "test-pass"],
    cwd=base,
    check=True,
)
res = subprocess.run(
    [sys.executable, "manifest_verifier.py", "--name", "verify_me", "--json"],
    cwd=base,
    check=True,
    capture_output=True,
    text=True,
)
data = json.loads(res.stdout)
assert data["signature_valid"] is True
assert data["ciphertext_hash_valid"] is True
assert data["creator"] == "TDD"
print("manifest verifier smoke test ok")
