
import json, subprocess, sys, base64, zipfile
from pathlib import Path
from cryptography.hazmat.primitives.asymmetric import ed25519

base = Path(__file__).resolve().parent

subprocess.run(
    [sys.executable, "template_packager.py", "--template", "aletheia_lattice_operational_prompt_v1", "--name", "aletheia_lattice_operational_prompt_v1_pack", "--passphrase", "test-pass"],
    cwd=base, check=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True
)

subprocess.run(
    [
        sys.executable, "release_manifest.py",
        "--template", "aletheia_lattice_operational_prompt_v1",
        "--pack-name", "aletheia_lattice_operational_prompt_v1_pack",
        "--release-name", "aletheia_lattice_operational_prompt_v1_release",
        "--release-notes", "Operational prompt v1.0 instantiated as a prompt-aligned evidence-bounded policy package."
    ],
    cwd=base, check=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True
)

res = subprocess.run(
    [
        sys.executable, "handoff_bundle.py",
        "--pack-name", "aletheia_lattice_operational_prompt_v1_pack",
        "--release-name", "aletheia_lattice_operational_prompt_v1_release",
        "--include-template",
        "--json",
    ],
    cwd=base, capture_output=True, text=True, check=True
)
payload = json.loads(res.stdout)

assert (base / "prompts" / "aletheia_lattice_operational_system_prompt_v1.md").exists()
assert (base / "prompts" / "aletheia_lattice_operational_system_prompt_v1.json").exists()
assert (base / "policy_templates" / "aletheia_lattice_operational_prompt_v1.json").exists()
assert (base / "vault" / "aletheia_lattice_operational_prompt_v1_pack.enc").exists()
assert (base / "manifests" / "aletheia_lattice_operational_prompt_v1_pack.json").exists()
assert (base / "manifests" / "aletheia_lattice_operational_prompt_v1_pack.sig").exists()

record_path = base / "release_manifests" / "aletheia_lattice_operational_prompt_v1_release.json"
sig_path = base / "release_manifests" / "aletheia_lattice_operational_prompt_v1_release.sig"
record = json.loads(record_path.read_text(encoding="utf-8"))
signature = sig_path.read_bytes()
pub = ed25519.Ed25519PublicKey.from_public_bytes(base64.b64decode(record["public_key_b64"]))
from celestial_agent.agent_spec_crypto import canonical_json
pub.verify(signature, canonical_json(record))

bundle_zip = base / "handoff_bundles" / "aletheia_lattice_operational_prompt_v1_release_bundle.zip"
assert bundle_zip.exists()
with zipfile.ZipFile(bundle_zip, "r") as zf:
    names = set(zf.namelist())
expected = {
    "aletheia_lattice_operational_prompt_v1_release_bundle/vault/aletheia_lattice_operational_prompt_v1_pack.enc",
    "aletheia_lattice_operational_prompt_v1_release_bundle/manifests/aletheia_lattice_operational_prompt_v1_pack.json",
    "aletheia_lattice_operational_prompt_v1_release_bundle/manifests/aletheia_lattice_operational_prompt_v1_pack.sig",
    "aletheia_lattice_operational_prompt_v1_release_bundle/release_manifests/aletheia_lattice_operational_prompt_v1_release.json",
    "aletheia_lattice_operational_prompt_v1_release_bundle/release_manifests/aletheia_lattice_operational_prompt_v1_release.sig",
    "aletheia_lattice_operational_prompt_v1_release_bundle/policy_templates/aletheia_lattice_operational_prompt_v1.json",
}
assert expected.issubset(names)

template = json.loads((base / "policy_templates" / "aletheia_lattice_operational_prompt_v1.json").read_text(encoding="utf-8"))
assert template["governance"]["defensive_only"] is True
assert template["channels"]["forecast"].startswith("scenario outputs")
assert "Context and Scope" in template["required_output"]
assert payload["pack_name"] == "aletheia_lattice_operational_prompt_v1_pack"

print("aletheia lattice operational prompt implementation smoke test ok")
