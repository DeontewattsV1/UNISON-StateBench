
import json, subprocess, sys, base64, zipfile
from pathlib import Path
from cryptography.hazmat.primitives.asymmetric import ed25519

base = Path(__file__).resolve().parent

# package the new template
subprocess.run(
    [sys.executable, "template_packager.py", "--template", "aletheia_lattice_dia_r2", "--name", "aletheia_lattice_dia_r2_pack", "--passphrase", "test-pass"],
    cwd=base, check=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True
)

# create release manifest
subprocess.run(
    [
        sys.executable, "release_manifest.py",
        "--template", "aletheia_lattice_dia_r2",
        "--pack-name", "aletheia_lattice_dia_r2_pack",
        "--release-name", "aletheia_lattice_dia_r2_review_board",
        "--release-notes", "Revision 2.0 package with measurable-security framing, governed deception constraints, and explicit temporal channel separation."
    ],
    cwd=base, check=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True
)

# create handoff bundle
res = subprocess.run(
    [
        sys.executable, "handoff_bundle.py",
        "--pack-name", "aletheia_lattice_dia_r2_pack",
        "--release-name", "aletheia_lattice_dia_r2_review_board",
        "--include-template",
        "--json",
    ],
    cwd=base, capture_output=True, text=True, check=True
)
payload = json.loads(res.stdout)

# verify key files
assert (base / "docs" / "aletheia_lattice_dia_deployment_architecture_r2.md").exists()
assert (base / "docs" / "aletheia_lattice_threat_control_matrix.json").exists()
assert (base / "policy_templates" / "aletheia_lattice_dia_r2.json").exists()
assert (base / "vault" / "aletheia_lattice_dia_r2_pack.enc").exists()
assert (base / "manifests" / "aletheia_lattice_dia_r2_pack.json").exists()
assert (base / "manifests" / "aletheia_lattice_dia_r2_pack.sig").exists()

# verify release manifest signature
record_path = base / "release_manifests" / "aletheia_lattice_dia_r2_review_board.json"
sig_path = base / "release_manifests" / "aletheia_lattice_dia_r2_review_board.sig"
record = json.loads(record_path.read_text(encoding="utf-8"))
signature = sig_path.read_bytes()
pub = ed25519.Ed25519PublicKey.from_public_bytes(base64.b64decode(record["public_key_b64"]))
from celestial_agent.agent_spec_crypto import canonical_json
pub.verify(signature, canonical_json(record))

# verify bundle zip exists and has key members
bundle_zip = base / "handoff_bundles" / "aletheia_lattice_dia_r2_review_board_bundle.zip"
assert bundle_zip.exists()
with zipfile.ZipFile(bundle_zip, "r") as zf:
    names = set(zf.namelist())
expected = {
    "aletheia_lattice_dia_r2_review_board_bundle/vault/aletheia_lattice_dia_r2_pack.enc",
    "aletheia_lattice_dia_r2_review_board_bundle/manifests/aletheia_lattice_dia_r2_pack.json",
    "aletheia_lattice_dia_r2_review_board_bundle/manifests/aletheia_lattice_dia_r2_pack.sig",
    "aletheia_lattice_dia_r2_review_board_bundle/release_manifests/aletheia_lattice_dia_r2_review_board.json",
    "aletheia_lattice_dia_r2_review_board_bundle/release_manifests/aletheia_lattice_dia_r2_review_board.sig",
    "aletheia_lattice_dia_r2_review_board_bundle/policy_templates/aletheia_lattice_dia_r2.json",
}
assert expected.issubset(names)

# inspect policy content
template = json.loads((base / "policy_templates" / "aletheia_lattice_dia_r2.json").read_text(encoding="utf-8"))
assert template["security_posture"]["absolute_security_language_forbidden"] is True
assert template["deception_governance"]["authorization_window_seconds"] == 90
assert template["multimodal_temporal_separation"]["output_format"] == ["Observed Facts", "Assessed Interpretation", "Scenario Projection"]
assert payload["pack_name"] == "aletheia_lattice_dia_r2_pack"

print("aletheia lattice revision 2.0 implementation smoke test ok")
