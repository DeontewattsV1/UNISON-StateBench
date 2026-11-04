
import json, subprocess, sys, os
from pathlib import Path

base = Path(__file__).resolve().parent

subprocess.run(
    [sys.executable, "pack_builder.py", "--policy", "example_phaseform_policy.json", "--name", "tamper_me", "--passphrase", "test-pass"],
    cwd=base,
    check=True,
)

subprocess.run(
    [sys.executable, "tamper_tester.py", "--name", "tamper_me", "--target", "sig"],
    cwd=base,
    check=True,
)

res = subprocess.run(
    [sys.executable, "manifest_verifier.py", "--name", "tamper_me_tampered_sig", "--json"],
    cwd=base,
    capture_output=True,
    text=True,
    check=True,
)
data = json.loads(res.stdout)
assert data["signature_valid"] is False

os.environ["PHASEFORM_PASSPHRASE"] = "test-pass"
from vault_watcher import VaultHandler

handler = VaultHandler(passphrase="test-pass")
tampered_path = base / "vault" / "tamper_me_tampered_sig.enc"
handler._process(tampered_path)

quarantined = base / "quarantine" / "tamper_me_tampered_sig.enc"
assert quarantined.exists(), "Tampered .enc was not quarantined"

print("tamper tester smoke test ok")
