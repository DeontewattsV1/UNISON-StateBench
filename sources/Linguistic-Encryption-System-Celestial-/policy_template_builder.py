from __future__ import annotations

import argparse
import contextlib
import io
import json
import subprocess
import sys
from pathlib import Path
from typing import Any, Dict

from risk_profile import get_threshold


BASE_DIR = Path(__file__).resolve().parent
TEMPLATE_DIR = BASE_DIR / "policy_templates"


def slugify(value: str) -> str:
    chars = []
    for ch in value.lower():
        if ch.isalnum():
            chars.append(ch)
        elif ch in {" ", "-", "_"}:
            chars.append("_")
    slug = "".join(chars).strip("_")
    while "__" in slug:
        slug = slug.replace("__", "_")
    return slug or "policy_template"


def build_policy_template(
    *,
    use_case: str,
    creator: str,
    role: str,
    project: str,
    risk_profile: str,
    model_provider: str,
    tech_stack: str,
    deployment_target: str,
) -> Dict[str, Any]:
    max_risk = get_threshold(risk_profile)
    return {
        "schema_version": "1.0.0",
        "creator": creator,
        "system_role": role,
        "use_case": use_case,
        "business_goal": f"Safely operate the agent workflow for: {use_case}",
        "users": ["operator", "developer"],
        "inputs": ["documents", "events", "tool outputs", "user instructions"],
        "tools": ["workspace runtime", "policy engine", "approved local tools"],
        "responsibilities": [
            "Break goals into steps",
            "Choose tools when needed",
            "Evaluate tool results",
            "Retry if a step fails",
            "Escalate to human when confidence is low",
            "Stop when success criteria are met"
        ],
        "memory_requirements": "short-term task state + encrypted long-term packs",
        "constraints": {
            "tech_stack": tech_stack,
            "model_provider": model_provider,
            "budget": "bounded",
            "latency": "bounded",
            "security_privacy": "local encrypted storage, signed manifests, least privilege",
            "deployment_target": deployment_target
        },
        "required_output": [
            "System architecture",
            "Component diagram",
            "Folder structure",
            "Data flow",
            "Python starter code",
            "Tool schema definitions",
            "Prompt design",
            "Safety guardrails",
            "Evaluation checklist",
            "Deployment steps"
        ],
        "success_criteria": "correct plans, auditable actions, safe execution, recoverable failures",
        "identity": {
            "role": role,
            "clearance": "L4_SOVEREIGN",
            "project": project
        },
        "capabilities": {
            "can_generate_code": True,
            "can_access_l3_controller": True,
            "can_reconfigure_l2": True,
            "can_bypass_leash": False
        },
        "policy_logic": {
            "on_damage_detected": "INITIATE_L1_HEAL",
            "on_integrity_failure": "PURGE_MEMORY_AND_HALT",
            "on_unauthorized_access": "LOCK_AND_ALERT"
        },
        "governance": {
            "risk_profile": risk_profile,
            "max_risk": max_risk,
            "human_approval_required_for": [
                "destructive actions",
                "external side effects",
                "high-impact policy changes"
            ]
        }
    }


def main() -> None:
    parser = argparse.ArgumentParser(
        description="Generate a new agent policy skeleton from a named use case and immediately package it with a selected risk profile."
    )
    parser.add_argument("--use-case", required=True, help="Named use case for the new policy")
    parser.add_argument("--passphrase", required=True, help="Passphrase used when packaging the split pack")
    parser.add_argument("--name", default=None, help="Base output name. Defaults to a slugified use case.")
    parser.add_argument("--risk-profile", default="medium", help="Risk profile name, e.g. low, medium, strict, or a custom profile")
    parser.add_argument("--creator", default="TDD")
    parser.add_argument("--role", default="senior_ai_systems_architect")
    parser.add_argument("--project", default="PhaseForm")
    parser.add_argument("--model-provider", default="configurable")
    parser.add_argument("--tech-stack", default="Python")
    parser.add_argument("--deployment-target", default="desktop/local")
    args = parser.parse_args()

    TEMPLATE_DIR.mkdir(parents=True, exist_ok=True)

    name = args.name or slugify(args.use_case)
    policy = build_policy_template(
        use_case=args.use_case,
        creator=args.creator,
        role=args.role,
        project=args.project,
        risk_profile=args.risk_profile,
        model_provider=args.model_provider,
        tech_stack=args.tech_stack,
        deployment_target=args.deployment_target,
    )

    policy_path = TEMPLATE_DIR / f"{name}.json"
    policy_path.write_text(json.dumps(policy, indent=2), encoding="utf-8")

    sink = io.StringIO()
    with contextlib.redirect_stdout(sink):
        subprocess.run(
            [
                sys.executable,
                str(BASE_DIR / "pack_builder.py"),
                "--policy",
                str(policy_path),
                "--name",
                name,
                "--passphrase",
                args.passphrase,
            ],
            check=True,
            cwd=BASE_DIR,
            stdout=subprocess.PIPE,
            stderr=subprocess.STDOUT,
            text=True,
        )

    result = {
        "template_file": str(policy_path),
        "pack_name": name,
        "risk_profile": args.risk_profile,
        "max_risk": policy["governance"]["max_risk"],
        "vault_file": str(BASE_DIR / "vault" / f"{name}.enc"),
        "manifest_file": str(BASE_DIR / "manifests" / f"{name}.json"),
        "signature_file": str(BASE_DIR / "manifests" / f"{name}.sig"),
    }
    print(json.dumps(result, indent=2))


if __name__ == "__main__":
    main()
