from __future__ import annotations

import argparse
import json
import subprocess
import sys
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent
TEMPLATE_DIR = BASE_DIR / "policy_templates"


def resolve_template(name: str) -> Path:
    candidate = Path(name)
    if candidate.exists():
        return candidate.resolve()
    p = TEMPLATE_DIR / (name if name.endswith(".json") else f"{name}.json")
    if p.exists():
        return p.resolve()
    raise FileNotFoundError(f"Could not resolve template: {name}")


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Package an existing policy template into a signed split pack without regenerating the template."
    )
    parser.add_argument("--template", required=True, help="Template name or path from policy_templates/")
    parser.add_argument("--passphrase", required=True, help="Passphrase used when packaging the split pack")
    parser.add_argument("--name", default=None, help="Optional output pack base name. Defaults to the template stem.")
    parser.add_argument("--json", action="store_true", help="Emit JSON output")
    args = parser.parse_args()

    template_path = resolve_template(args.template)
    pack_name = args.name or template_path.stem

    result = subprocess.run(
        [
            sys.executable,
            str(BASE_DIR / "pack_builder.py"),
            "--policy",
            str(template_path),
            "--name",
            pack_name,
            "--passphrase",
            args.passphrase,
        ],
        cwd=BASE_DIR,
        capture_output=True,
        text=True,
        check=True,
    )

    payload = {
        "template_file": str(template_path),
        "pack_name": pack_name,
        "vault_file": str(BASE_DIR / "vault" / f"{pack_name}.enc"),
        "manifest_file": str(BASE_DIR / "manifests" / f"{pack_name}.json"),
        "signature_file": str(BASE_DIR / "manifests" / f"{pack_name}.sig"),
        "pack_builder_output": result.stdout.splitlines(),
    }

    if args.json:
        print(json.dumps(payload, indent=2))
        return

    print("== TEMPLATE PACKAGER ==")
    print(f"template_file: {payload['template_file']}")
    print(f"pack_name: {payload['pack_name']}")
    print(f"vault_file: {payload['vault_file']}")
    print(f"manifest_file: {payload['manifest_file']}")
    print(f"signature_file: {payload['signature_file']}")


if __name__ == "__main__":
    main()
