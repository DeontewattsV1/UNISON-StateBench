
import json, subprocess, sys, base64
from pathlib import Path

base = Path(__file__).resolve().parent

# Build two packs
subprocess.run([sys.executable, "pack_builder.py", "--policy", "example_phaseform_policy.json", "--name", "diff_a", "--passphrase", "test-pass"], cwd=base, check=True)
subprocess.run([sys.executable, "pack_builder.py", "--policy", "example_phaseform_policy_v2.json", "--name", "diff_b", "--passphrase", "test-pass"], cwd=base, check=True)

# Restore decrypted policies
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

restore("diff_a")
restore("diff_b")

res = subprocess.run(
    [sys.executable, "pack_diff.py", "--kind", "policy", "--left", "diff_a", "--right", "diff_b", "--json"],
    cwd=base,
    capture_output=True,
    text=True,
    check=True,
)
payload = json.loads(res.stdout)
assert payload["difference_count"] > 0
paths = {d["path"] for d in payload["differences"]}
assert "identity.role" in paths
assert "policy_logic.on_damage_detected" in paths
print("pack diff smoke test ok")
