from __future__ import annotations

import argparse
import json
import shutil
import zipfile
from pathlib import Path


BASE_DIR = Path(__file__).resolve().parent
VAULT_DIR = BASE_DIR / "vault"
MANIFESTS_DIR = BASE_DIR / "manifests"
RELEASE_DIR = BASE_DIR / "release_manifests"
BUNDLES_DIR = BASE_DIR / "handoff_bundles"


def _copy(src: Path, dst: Path) -> None:
    dst.parent.mkdir(parents=True, exist_ok=True)
    shutil.copy2(src, dst)


def build_bundle(
    *,
    pack_name: str,
    release_name: str,
    bundle_name: str,
    include_template: bool = False,
) -> dict:
    pack_enc = VAULT_DIR / f"{pack_name}.enc"
    pack_manifest = MANIFESTS_DIR / f"{pack_name}.json"
    pack_sig = MANIFESTS_DIR / f"{pack_name}.sig"
    release_manifest = RELEASE_DIR / f"{release_name}.json"
    release_sig = RELEASE_DIR / f"{release_name}.sig"

    required = [pack_enc, pack_manifest, pack_sig, release_manifest, release_sig]
    missing = [str(p) for p in required if not p.exists()]
    if missing:
        raise FileNotFoundError(f"Missing required files: {missing}")

    bundle_dir = BUNDLES_DIR / bundle_name
    if bundle_dir.exists():
        shutil.rmtree(bundle_dir)
    bundle_dir.mkdir(parents=True, exist_ok=True)

    copied = []
    mapping = [
        (pack_enc, bundle_dir / "vault" / pack_enc.name),
        (pack_manifest, bundle_dir / "manifests" / pack_manifest.name),
        (pack_sig, bundle_dir / "manifests" / pack_sig.name),
        (release_manifest, bundle_dir / "release_manifests" / release_manifest.name),
        (release_sig, bundle_dir / "release_manifests" / release_sig.name),
    ]

    release_record = json.loads(release_manifest.read_text(encoding="utf-8"))
    if include_template:
        template_file = Path(release_record["template"]["file"])
        if template_file.exists():
            mapping.append((template_file, bundle_dir / "policy_templates" / template_file.name))

    for src, dst in mapping:
        _copy(src, dst)
        copied.append(str(dst))

    bundle_index = {
        "schema_version": "1.0.0",
        "content_type": "phaseform_handoff_bundle",
        "bundle_name": bundle_name,
        "pack_name": pack_name,
        "release_name": release_name,
        "included_files": copied,
    }
    (bundle_dir / "bundle_index.json").write_text(json.dumps(bundle_index, indent=2), encoding="utf-8")

    return {
        "bundle_dir": str(bundle_dir),
        "bundle_index_file": str(bundle_dir / "bundle_index.json"),
        "pack_name": pack_name,
        "release_name": release_name,
        "included_files": copied,
    }


def zip_bundle(bundle_dir: Path) -> Path:
    zip_path = bundle_dir.with_suffix(".zip")
    if zip_path.exists():
        zip_path.unlink()
    with zipfile.ZipFile(zip_path, "w", zipfile.ZIP_DEFLATED) as zf:
        for path in bundle_dir.rglob("*"):
            zf.write(path, arcname=str(path.relative_to(bundle_dir.parent)))
    return zip_path


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Export a split pack plus signed release manifest together as one distribution-ready directory or zip."
    )
    parser.add_argument("--pack-name", required=True, help="Existing split pack base name")
    parser.add_argument("--release-name", required=True, help="Existing signed release manifest base name")
    parser.add_argument("--bundle-name", default=None, help="Optional bundle base name. Defaults to <release-name>_bundle")
    parser.add_argument("--format", choices=["dir", "zip"], default="zip", help="Export as a directory or zip")
    parser.add_argument("--include-template", action="store_true", help="Also copy the referenced template into the bundle")
    parser.add_argument("--json", action="store_true", help="Emit JSON output")
    args = parser.parse_args()

    bundle_name = args.bundle_name or f"{args.release_name}_bundle"
    BUNDLES_DIR.mkdir(parents=True, exist_ok=True)

    payload = build_bundle(
        pack_name=args.pack_name,
        release_name=args.release_name,
        bundle_name=bundle_name,
        include_template=args.include_template,
    )

    if args.format == "zip":
        zip_path = zip_bundle(Path(payload["bundle_dir"]))
        payload["bundle_zip"] = str(zip_path)

    if args.json:
        print(json.dumps(payload, indent=2))
        return

    print("== HANDOFF BUNDLE ==")
    for key, value in payload.items():
        if key == "included_files":
            print(f"{key}:")
            for item in value:
                print(f"  - {item}")
        else:
            print(f"{key}: {value}")


if __name__ == "__main__":
    main()
