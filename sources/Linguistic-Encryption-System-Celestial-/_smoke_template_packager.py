
import json, subprocess, sys, base64
from pathlib import Path

base = Path(__file__).resolve().parent

# Ensure a template exists
subprocess.run([sys.executable, "profile_manager.py", "--set", "cautious", "7"], cwd=base, check=True)
subprocess.run(
    [
        sys.executable,
        "policy_template_builder.py",
        "--use-case", "Sales operations lead triage",
        "--name", "sales_ops_template",
        "--risk-profile", "cautious",
        "--passphrase", "test-pass",
    ],
    cwd=base,
    check=True,
    stdout=subprocess.PIPE,
    stderr=subprocess.STDOUT,
    text=True,
)

# Package the existing template under a new pack name
res = subprocess.run(
    [
        sys.executable,
        "template_packager.py",
        "--template", "sales_ops_template",
        "--name", "sales_ops_release_1",
        "--passphrase", "test-pass",
        "--json",
    ],
    cwd=base,
    capture_output=True,
    text=True,
    check=True,
)
payload = json.loads(res.stdout)

assert (base / "vault" / "sales_ops_release_1.enc").exists()
assert (base / "manifests" / "sales_ops_release_1.json").exists()
assert (base / "manifests" / "sales_ops_release_1.sig").exists()

from celestial_agent.agent_spec_crypto import AgentSpecCrypto, EncryptedAgentPack

manifest = json.loads((base / "manifests" / "sales_ops_release_1.json").read_text(encoding="utf-8"))
ciphertext = (base / "vault" / "sales_ops_release_1.enc").read_bytes()
signature = (base / "manifests" / "sales_ops_release_1.sig").read_bytes()

pack = EncryptedAgentPack(
    manifest=manifest,
    ciphertext_b64=base64.b64encode(ciphertext).decode("utf-8"),
    nonce_b64=manifest["nonce_b64"],
    salt_b64=manifest["salt_b64"],
    signature_b64=base64.b64encode(signature).decode("utf-8"),
)

restored = AgentSpecCrypto.verify_and_decrypt(pack, "test-pass")
assert restored["use_case"] == "Sales operations lead triage"
assert restored["governance"]["risk_profile"] == "cautious"

print("template packager smoke test ok")
