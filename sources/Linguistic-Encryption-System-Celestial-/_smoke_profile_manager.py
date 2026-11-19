
import json, subprocess, sys, base64
from pathlib import Path

base = Path(__file__).resolve().parent

# Add a custom risk profile
subprocess.run([sys.executable, "profile_manager.py", "--set", "cautious", "7"], cwd=base, check=True)

# Build two packs
subprocess.run([sys.executable, "pack_builder.py", "--policy", "example_phaseform_policy.json", "--name", "guard_a", "--passphrase", "test-pass"], cwd=base, check=True)
subprocess.run([sys.executable, "pack_builder.py", "--policy", "example_phaseform_policy_v2.json", "--name", "guard_b", "--passphrase", "test-pass"], cwd=base, check=True)

from celestial_agent.agent_spec_crypto import AgentSpecCrypto, EncryptedAgentPack
from celestial_agent.celestial_language import CelestialLanguage

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

# Activate baseline
subprocess.run([sys.executable, "policy_rotator.py", "--activate", "guard_a.json"], cwd=base, check=True)

# Custom profile should behave like threshold 7
res = subprocess.run(
    [sys.executable, "rotation_guard.py", "--pack-name", "guard_b", "--risk-profile", "cautious", "--json"],
    cwd=base, capture_output=True, text=True, check=True
)
payload = json.loads(res.stdout)
assert payload["risk_profile"] == "cautious"
assert payload["max_risk"] == 7
assert payload["manifest_ok"] is True

# Celestial language deterministic roundtrip
cl1 = CelestialLanguage(seed="phaseform-seed")
cl2 = CelestialLanguage(seed="phaseform-seed")
assert cl1.glyph_map == cl2.glyph_map
encoded = cl1.encode_message("Hello, PhaseForm!")
ciphertext, key = cl1.encrypt_bytes(encoded.encode("utf-8"))
decoded = cl1.decrypt_bytes(ciphertext, key).decode("utf-8")
assert decoded == encoded

print("profile manager smoke test ok")
