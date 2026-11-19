
import json, subprocess, sys, zipfile
from pathlib import Path

base = Path(__file__).resolve().parent

# Ensure template, pack, and signed release manifest exist
subprocess.run([sys.executable, "profile_manager.py", "--set", "cautious", "7"], cwd=base, check=True)
subprocess.run(
    [sys.executable, "policy_template_builder.py", "--use-case", "Sales operations lead triage", "--name", "sales_ops_template", "--risk-profile", "cautious", "--passphrase", "test-pass"],
    cwd=base, check=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True
)
subprocess.run(
    [sys.executable, "template_packager.py", "--template", "sales_ops_template", "--name", "sales_ops_release_1", "--passphrase", "test-pass"],
    cwd=base, check=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True
)
subprocess.run(
    [sys.executable, "release_manifest.py", "--template", "sales_ops_template", "--pack-name", "sales_ops_release_1", "--release-name", "sales_ops_release_1_handoff", "--release-notes", "Initial reviewed release for internal distribution"],
    cwd=base, check=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True
)

res = subprocess.run(
    [sys.executable, "handoff_bundle.py", "--pack-name", "sales_ops_release_1", "--release-name", "sales_ops_release_1_handoff", "--include-template", "--json"],
    cwd=base, capture_output=True, text=True, check=True
)
payload = json.loads(res.stdout)

bundle_dir = base / "handoff_bundles" / "sales_ops_release_1_handoff_bundle"
bundle_zip = base / "handoff_bundles" / "sales_ops_release_1_handoff_bundle.zip"

assert bundle_dir.exists()
assert bundle_zip.exists()

expected = {
    "sales_ops_release_1_handoff_bundle/vault/sales_ops_release_1.enc",
    "sales_ops_release_1_handoff_bundle/manifests/sales_ops_release_1.json",
    "sales_ops_release_1_handoff_bundle/manifests/sales_ops_release_1.sig",
    "sales_ops_release_1_handoff_bundle/release_manifests/sales_ops_release_1_handoff.json",
    "sales_ops_release_1_handoff_bundle/release_manifests/sales_ops_release_1_handoff.sig",
    "sales_ops_release_1_handoff_bundle/policy_templates/sales_ops_template.json",
    "sales_ops_release_1_handoff_bundle/bundle_index.json",
}

with zipfile.ZipFile(bundle_zip, "r") as zf:
    names = set(zf.namelist())

assert expected.issubset(names)
assert payload["pack_name"] == "sales_ops_release_1"
assert payload["release_name"] == "sales_ops_release_1_handoff"

print("handoff bundle smoke test ok")
