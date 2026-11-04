
import json, subprocess, sys, base64
from pathlib import Path
base = Path(__file__).resolve().parent

subprocess.run([sys.executable, "pack_builder.py", "--policy", "example_phaseform_policy.json", "--name", "policy_a", "--passphrase", "test-pass"], cwd=base, check=True)
subprocess.run([sys.executable, "pack_builder.py", "--policy", "example_phaseform_policy_v2.json", "--name", "policy_b", "--passphrase", "test-pass"], cwd=base, check=True)

from celestial_agent.agent_spec_crypto import AgentSpecCrypto, EncryptedAgentPack

def restore(name):
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

restore("policy_a")
restore("policy_b")

subprocess.run([sys.executable, "policy_rotator.py", "--activate", "policy_a.json"], cwd=base, check=True)
subprocess.run([sys.executable, "policy_rotator.py", "--activate", "policy_b.json"], cwd=base, check=True)
subprocess.run([sys.executable, "policy_rotator.py", "--rollback-last"], cwd=base, check=True)

active = json.loads((base / "runtime_state" / "active_policy.json").read_text(encoding="utf-8"))
assert active["identity"]["role"] == "senior_ai_systems_architect"
print("policy rotator smoke test ok")
