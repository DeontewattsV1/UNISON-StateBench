
import json, subprocess, sys
from pathlib import Path

base = Path(__file__).resolve().parent

# Ensure source template exists
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

# List
res_list = subprocess.run(
    [sys.executable, "template_catalog.py", "--list", "--json"],
    cwd=base, capture_output=True, text=True, check=True
)
payload_list = json.loads(res_list.stdout)
names = {item["name"] for item in payload_list["templates"]}
assert "sales_ops_template.json" in names

# Inspect
res_inspect = subprocess.run(
    [sys.executable, "template_catalog.py", "--inspect", "sales_ops_template", "--json"],
    cwd=base, capture_output=True, text=True, check=True
)
payload_inspect = json.loads(res_inspect.stdout)
assert payload_inspect["content"]["use_case"] == "Sales operations lead triage"

# Clone
subprocess.run(
    [sys.executable, "template_catalog.py", "--clone", "sales_ops_template", "sales_ops_template_v2"],
    cwd=base, check=True, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True
)

clone_path = base / "policy_templates" / "sales_ops_template_v2.json"
assert clone_path.exists()

# Modify clone for diff
clone = json.loads(clone_path.read_text(encoding="utf-8"))
clone["governance"]["risk_profile"] = "strict"
clone["governance"]["max_risk"] = 3
clone["identity"]["role"] = "principal_phaseform_operator"
clone_path.write_text(json.dumps(clone, indent=2), encoding="utf-8")

res_diff = subprocess.run(
    [sys.executable, "template_catalog.py", "--diff", "sales_ops_template", "sales_ops_template_v2", "--json"],
    cwd=base, capture_output=True, text=True, check=True
)
payload_diff = json.loads(res_diff.stdout)
assert payload_diff["difference_count"] > 0
paths = {d["path"] for d in payload_diff["differences"]}
assert "governance.risk_profile" in paths
assert "identity.role" in paths

print("template catalog smoke test ok")
