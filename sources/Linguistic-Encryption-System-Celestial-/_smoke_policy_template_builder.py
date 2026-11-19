
import json, subprocess, sys, base64
from pathlib import Path

base = Path(__file__).resolve().parent

subprocess.run([sys.executable, "profile_manager.py", "--set", "cautious", "7"], cwd=base, check=True)

res = subprocess.run(
    [
        sys.executable,
        "policy_template_builder.py",
        "--use-case", "Sales operations lead triage",
        "--name", "sales_ops_template",
        "--risk-profile", "cautious",
        "--passphrase", "test-pass",
    ],
    cwd=base,
    capture_output=True,
    text=True,
    check=True,
)
payload = json.loads(res.stdout)

template_path = base / "policy_templates" / "sales_ops_template.json"
assert template_path.exists()
policy = json.loads(template_path.read_text(encoding="utf-8"))
assert policy["use_case"] == "Sales operations lead triage"
assert policy["governance"]["risk_profile"] == "cautious"
assert policy["governance"]["max_risk"] == 7

from celestial_agent.agent_spec_crypto import AgentSpecCrypto, EncryptedAgentPack

manifest = json.loads((base / "manifests" / "sales_ops_template.json").read_text(encoding="utf-8"))
ciphertext = (base / "vault" / "sales_ops_template.enc").read_bytes()
signature = (base / "manifests" / "sales_ops_template.sig").read_bytes()

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

print("policy template builder smoke test ok")
