
import base64, json, subprocess, sys
from pathlib import Path
from cryptography.hazmat.primitives.asymmetric import ed25519

base = Path(__file__).resolve().parent

subprocess.run([sys.executable, "profile_manager.py", "--set", "cautious", "7"], cwd=base, check=True)
subprocess.run(
    [sys.executable, "policy_template_builder.py", "--use-case", "Sales operations lead triage", "--name", "sales_ops_template", "--risk-profile", "cautious", "--passphrase", "test-pass"],
    cwd=base, check=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True
)
subprocess.run(
    [sys.executable, "template_packager.py", "--template", "sales_ops_template", "--name", "sales_ops_release_1", "--passphrase", "test-pass"],
    cwd=base, check=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True
)

res = subprocess.run(
    [sys.executable, "release_manifest.py", "--template", "sales_ops_template", "--pack-name", "sales_ops_release_1", "--release-name", "sales_ops_release_1_handoff", "--release-notes", "Initial reviewed release for internal distribution", "--json"],
    cwd=base, capture_output=True, text=True
)
print("INNER STDOUT:", res.stdout)
print("INNER STDERR:", res.stderr)
if res.returncode != 0:
    raise SystemExit(res.returncode)

payload = json.loads(res.stdout)
record_path = base / "release_manifests" / "sales_ops_release_1_handoff.json"
sig_path = base / "release_manifests" / "sales_ops_release_1_handoff.sig"
assert record_path.exists()
assert sig_path.exists()

record = json.loads(record_path.read_text(encoding="utf-8"))
signature = sig_path.read_bytes()

pub = ed25519.Ed25519PublicKey.from_public_bytes(base64.b64decode(record["public_key_b64"]))
from celestial_agent.agent_spec_crypto import canonical_json
pub.verify(signature, canonical_json(record))

assert record["template"]["use_case"] == "Sales operations lead triage"
assert record["governance"]["risk_profile"] == "cautious"
assert record["pack"]["hashes"]["ciphertext_sha256"]
assert record["release_notes"] == "Initial reviewed release for internal distribution"

print("release manifest smoke test ok")
