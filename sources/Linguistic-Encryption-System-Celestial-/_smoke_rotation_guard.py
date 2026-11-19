
import json, subprocess, sys, base64
from pathlib import Path

base = Path(__file__).resolve().parent

subprocess.run([sys.executable, "pack_builder.py", "--policy", "example_phaseform_policy.json", "--name", "guard_a", "--passphrase", "test-pass"], cwd=base, check=True)
subprocess.run([sys.executable, "pack_builder.py", "--policy", "example_phaseform_policy_v2.json", "--name", "guard_b", "--passphrase", "test-pass"], cwd=base, check=True)

from celestial_agent.agent_spec_crypto import AgentSpecCrypto, EncryptedAgentPack

def restore(name: str):
    manifest = json.loads((base / "manifests" / f"{name}.json").read_text(encoding="utf-8"))
    ciphertext = (base / "vault" / f"{name}.enc").read_bytes()
    signature = (base / "manifests" / f"{name}.sig").read_bytes()
    pack = EncryptedAgentPack(
        manifest=manifest,
        ciphertext_b64=base64.b64encode(ciphertext).decode("utf-8"),
        nonce_b64=manifest["nonce_b64"],
        salt_b64=manifest["salt_b64"],
        signature_b64=base64.b64encode(signature).decode("utf-8"),
    )
    spec = AgentSpecCrypto.verify_and_decrypt(pack, "test-pass")
    (base / "decrypted" / f"{name}.json").write_text(json.dumps(spec, indent=2), encoding="utf-8")

restore("guard_a")
restore("guard_b")

subprocess.run([sys.executable, "policy_rotator.py", "--activate", "guard_a.json"], cwd=base, check=True)

res_block = subprocess.run(
    [sys.executable, "rotation_guard.py", "--pack-name", "guard_b", "--max-risk", "1", "--json"],
    cwd=base, capture_output=True, text=True, check=True
)
payload_block = json.loads(res_block.stdout)
assert payload_block["manifest_ok"] is True
assert payload_block["risk_ok"] is False
assert payload_block["activation_allowed"] is False
assert payload_block["activated"] is False

res_allow = subprocess.run(
    [sys.executable, "rotation_guard.py", "--pack-name", "guard_b", "--max-risk", "20", "--activate", "--json"],
    cwd=base, capture_output=True, text=True, check=True
)
payload_allow = json.loads(res_allow.stdout)
assert payload_allow["activation_allowed"] is True
assert payload_allow["activated"] is True

active = json.loads((base / "runtime_state" / "active_policy.json").read_text(encoding="utf-8"))
assert active["identity"]["role"] == "principal_phaseform_operator"
print("rotation guard smoke test ok")
