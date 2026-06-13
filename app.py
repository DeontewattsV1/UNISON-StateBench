from __future__ import annotations

import json
import tkinter as tk
from pathlib import Path
from tkinter import filedialog, messagebox, ttk

from celestial_core import AgentRuntime, AgentSpecCrypto, SignedAgentPack

DEFAULT_AGENT_SPEC = {
    "title": "Celestial Agent Spec",
    "creator": "TDD",
    "system_role": "senior_ai_systems_architect",
    "use_case": "Encrypted agent builder",
    "business_goal": "Design and implement controlled agentic systems inside an encrypted workspace.",
    "users": ["founder", "operator", "developer"],
    "inputs": ["documents", "events", "tool outputs", "user instructions"],
    "tools": ["workspace runtime", "file tools", "code generator", "policy engine"],
    "responsibilities": [
        "Break goals into steps",
        "Choose tools when needed",
        "Evaluate tool results",
        "Retry if a step fails",
        "Escalate to human when confidence is low",
        "Stop when success criteria are met",
    ],
    "memory_requirements": "short-term task state + encrypted long-term packs",
    "constraints": {
        "tech_stack": "Python",
        "model_provider": "configurable",
        "budget": "bounded",
        "latency": "bounded",
        "security_privacy": "local encrypted storage, signed manifests, no hidden access",
        "deployment_target": "desktop/local",
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
        "Deployment steps",
    ],
    "success_criteria": "Correct plans, auditable actions, safe execution, recoverable failures.",
}

DEMO_COMMANDS = '''MAKE FILE "spell.txt"
WRITE "The orbit opens." TO "spell.txt"
APPEND " The archive remembers." TO "spell.txt"
MAKE FUNCTION "sum_two" LANG "python" ARGS "a, b" BODY "return a + b" TO "sum_two.py"
READ FILE "spell.txt"
LIST FILES
HASH "TDD celestial prototype"
'''


class LabeledEntry(ttk.Frame):
    def __init__(self, master: tk.Widget, label: str, width: int = 60) -> None:
        super().__init__(master)
        ttk.Label(self, text=label).pack(anchor="w")
        self.var = tk.StringVar()
        self.entry = ttk.Entry(self, textvariable=self.var, width=width)
        self.entry.pack(fill="x")


class CelestialDesktopApp:
    def __init__(self, root: tk.Tk) -> None:
        self.root = root
        self.root.title("Celestial Desktop Prototype — Agent Spec Editor")
        self.root.geometry("1300x900")

        self.crypto = AgentSpecCrypto()
        self.current_pack: SignedAgentPack | None = None
        self.current_spec: dict | None = None
        self.runtime: AgentRuntime | None = None

        self._build_ui()
        self._load_default_spec()
        self.command_input.insert("1.0", DEMO_COMMANDS)
        self.workspace_entry.var.set(str((Path.cwd() / "workspace").resolve()))
        self.seed_entry.var.set("tdd-celestial-seed")

    def _build_ui(self) -> None:
        notebook = ttk.Notebook(self.root)
        notebook.pack(fill="both", expand=True)

        self.runtime_tab = ttk.Frame(notebook)
        self.spec_tab = ttk.Frame(notebook)
        notebook.add(self.runtime_tab, text="Runtime")
        notebook.add(self.spec_tab, text="Agent Spec Editor")

        self._build_runtime_tab()
        self._build_spec_tab()

    def _build_runtime_tab(self) -> None:
        top = ttk.Frame(self.runtime_tab, padding=10)
        top.pack(fill="x")

        self.workspace_entry = LabeledEntry(top, "Workspace")
        self.workspace_entry.pack(fill="x", pady=4)
        ttk.Button(top, text="Choose Workspace", command=self.choose_workspace).pack(anchor="w", pady=(0, 6))

        self.seed_entry = LabeledEntry(top, "Celestial Seed")
        self.seed_entry.pack(fill="x", pady=4)

        runtime_actions = ttk.Frame(top)
        runtime_actions.pack(fill="x", pady=6)
        ttk.Button(runtime_actions, text="Initialize Runtime", command=self.initialize_runtime).pack(side="left", padx=4)
        ttk.Button(runtime_actions, text="Load Demo", command=self.load_demo).pack(side="left", padx=4)
        ttk.Button(runtime_actions, text="Compile to Celestial", command=self.compile_commands).pack(side="left", padx=4)
        ttk.Button(runtime_actions, text="Run Plain Commands", command=lambda: self.run_commands(False)).pack(side="left", padx=4)
        ttk.Button(runtime_actions, text="Run Celestial", command=lambda: self.run_commands(True)).pack(side="left", padx=4)

        self.runtime_status = tk.StringVar(value="Runtime not initialized. No agent spec loaded.")
        ttk.Label(top, textvariable=self.runtime_status).pack(anchor="w", pady=(4, 0))

        panes = ttk.Panedwindow(self.runtime_tab, orient="horizontal")
        panes.pack(fill="both", expand=True, padx=10, pady=10)

        left = ttk.Frame(panes)
        right = ttk.Frame(panes)
        panes.add(left, weight=1)
        panes.add(right, weight=1)

        ttk.Label(left, text="Plain Commands").pack(anchor="w")
        self.command_input = tk.Text(left, wrap="word")
        self.command_input.pack(fill="both", expand=True)

        ttk.Label(right, text="Celestial / Output").pack(anchor="w")
        self.celestial_output = tk.Text(right, wrap="word", height=12)
        self.celestial_output.pack(fill="both", expand=True)
        self.execution_output = tk.Text(right, wrap="word", height=12)
        self.execution_output.pack(fill="both", expand=True, pady=(10, 0))

    def _build_spec_tab(self) -> None:
        container = ttk.Frame(self.spec_tab, padding=10)
        container.pack(fill="both", expand=True)

        left = ttk.Frame(container)
        right = ttk.Frame(container)
        left.pack(side="left", fill="both", expand=True)
        right.pack(side="left", fill="both", expand=True, padx=(10, 0))

        fields_top = ttk.Frame(left)
        fields_top.pack(fill="x")

        self.title_entry = LabeledEntry(fields_top, "Title")
        self.title_entry.pack(fill="x", pady=3)
        self.creator_entry = LabeledEntry(fields_top, "Creator")
        self.creator_entry.pack(fill="x", pady=3)
        self.role_entry = LabeledEntry(fields_top, "System Role")
        self.role_entry.pack(fill="x", pady=3)
        self.use_case_entry = LabeledEntry(fields_top, "Use Case")
        self.use_case_entry.pack(fill="x", pady=3)
        self.goal_entry = LabeledEntry(fields_top, "Business Goal")
        self.goal_entry.pack(fill="x", pady=3)
        self.memory_entry = LabeledEntry(fields_top, "Memory Requirements")
        self.memory_entry.pack(fill="x", pady=3)
        self.success_entry = LabeledEntry(fields_top, "Success Criteria")
        self.success_entry.pack(fill="x", pady=3)

        text_grid = ttk.Frame(left)
        text_grid.pack(fill="both", expand=True, pady=(8, 0))

        self.users_text = self._make_labeled_text(text_grid, "Users (one per line)")
        self.inputs_text = self._make_labeled_text(text_grid, "Inputs (one per line)")
        self.tools_text = self._make_labeled_text(text_grid, "Tools (one per line)")
        self.responsibilities_text = self._make_labeled_text(text_grid, "Responsibilities (one per line)")
        self.outputs_text = self._make_labeled_text(text_grid, "Required Output (one per line)")
        self.constraints_text = self._make_labeled_text(
            text_grid,
            "Constraints JSON",
            default='''{\n  "tech_stack": "Python",\n  "model_provider": "configurable",\n  "budget": "bounded",\n  "latency": "bounded",\n  "security_privacy": "local encrypted storage",\n  "deployment_target": "desktop/local"\n}''',
        )

        controls = ttk.Frame(right)
        controls.pack(fill="x")

        self.passphrase_entry = LabeledEntry(controls, "Passphrase")
        self.passphrase_entry.pack(fill="x", pady=3)

        key_row = ttk.Frame(controls)
        key_row.pack(fill="x", pady=6)
        ttk.Button(key_row, text="New Signing Key", command=self.rotate_keys).pack(side="left", padx=4)
        ttk.Button(key_row, text="Encrypt + Sign", command=self.encrypt_and_sign).pack(side="left", padx=4)
        ttk.Button(key_row, text="Verify + Decrypt", command=self.verify_and_decrypt).pack(side="left", padx=4)
        ttk.Button(key_row, text="Load into Runtime", command=self.load_spec_into_runtime).pack(side="left", padx=4)
        ttk.Button(key_row, text="Export Signed Pack", command=self.export_pack).pack(side="left", padx=4)
        ttk.Button(key_row, text="Import Signed Pack", command=self.import_pack).pack(side="left", padx=4)

        self.spec_status = tk.StringVar(value="No signed pack loaded.")
        ttk.Label(controls, textvariable=self.spec_status).pack(anchor="w", pady=(2, 8))

        ttk.Label(right, text="Manifest / Pack Preview").pack(anchor="w")
        self.pack_preview = tk.Text(right, wrap="word", height=20)
        self.pack_preview.pack(fill="both", expand=True)

        ttk.Label(right, text="Decrypted Spec Preview").pack(anchor="w", pady=(10, 0))
        self.decrypted_preview = tk.Text(right, wrap="word", height=20)
        self.decrypted_preview.pack(fill="both", expand=True)

    def _make_labeled_text(self, parent: ttk.Frame, label: str, default: str = "") -> tk.Text:
        frame = ttk.Frame(parent)
        frame.pack(fill="both", expand=True, pady=4)
        ttk.Label(frame, text=label).pack(anchor="w")
        text = tk.Text(frame, wrap="word", height=5)
        text.pack(fill="both", expand=True)
        if default:
            text.insert("1.0", default)
        return text

    def _load_default_spec(self) -> None:
        self.title_entry.var.set(DEFAULT_AGENT_SPEC["title"])
        self.creator_entry.var.set(DEFAULT_AGENT_SPEC["creator"])
        self.role_entry.var.set(DEFAULT_AGENT_SPEC["system_role"])
        self.use_case_entry.var.set(DEFAULT_AGENT_SPEC["use_case"])
        self.goal_entry.var.set(DEFAULT_AGENT_SPEC["business_goal"])
        self.memory_entry.var.set(DEFAULT_AGENT_SPEC["memory_requirements"])
        self.success_entry.var.set(DEFAULT_AGENT_SPEC["success_criteria"])

        self._replace_text(self.users_text, "\n".join(DEFAULT_AGENT_SPEC["users"]))
        self._replace_text(self.inputs_text, "\n".join(DEFAULT_AGENT_SPEC["inputs"]))
        self._replace_text(self.tools_text, "\n".join(DEFAULT_AGENT_SPEC["tools"]))
        self._replace_text(self.responsibilities_text, "\n".join(DEFAULT_AGENT_SPEC["responsibilities"]))
        self._replace_text(self.outputs_text, "\n".join(DEFAULT_AGENT_SPEC["required_output"]))
        self._replace_text(self.constraints_text, json.dumps(DEFAULT_AGENT_SPEC["constraints"], indent=2))

    @staticmethod
    def _replace_text(widget: tk.Text, value: str) -> None:
        widget.delete("1.0", "end")
        widget.insert("1.0", value)

    def build_spec_from_form(self) -> dict:
        try:
            constraints = json.loads(self.constraints_text.get("1.0", "end").strip() or "{}")
        except json.JSONDecodeError as exc:
            raise ValueError(f"Constraints JSON is invalid: {exc}") from exc

        return {
            "title": self.title_entry.var.get().strip() or "Celestial Agent Spec",
            "creator": self.creator_entry.var.get().strip() or "TDD",
            "system_role": self.role_entry.var.get().strip(),
            "use_case": self.use_case_entry.var.get().strip(),
            "business_goal": self.goal_entry.var.get().strip(),
            "users": [line for line in self.users_text.get("1.0", "end").splitlines() if line.strip()],
            "inputs": [line for line in self.inputs_text.get("1.0", "end").splitlines() if line.strip()],
            "tools": [line for line in self.tools_text.get("1.0", "end").splitlines() if line.strip()],
            "responsibilities": [line for line in self.responsibilities_text.get("1.0", "end").splitlines() if line.strip()],
            "memory_requirements": self.memory_entry.var.get().strip(),
            "constraints": constraints,
            "required_output": [line for line in self.outputs_text.get("1.0", "end").splitlines() if line.strip()],
            "success_criteria": self.success_entry.var.get().strip(),
        }

    def rotate_keys(self) -> None:
        self.crypto = AgentSpecCrypto()
        self.spec_status.set("Generated a new signing keypair for this session.")
        self.pack_preview.delete("1.0", "end")
        self.pack_preview.insert("1.0", "New keypair generated.\nPublic key:\n" + self.crypto.export_public_key_b64())

    def encrypt_and_sign(self) -> None:
        try:
            spec = self.build_spec_from_form()
            pack = self.crypto.encrypt_and_sign(spec, self.passphrase_entry.var.get())
            self.current_spec = spec
            self.current_pack = pack
            self.pack_preview.delete("1.0", "end")
            self.pack_preview.insert("1.0", pack.to_json())
            self.spec_status.set("Encrypted and signed agent spec.")
        except Exception as exc:
            messagebox.showerror("Encrypt + Sign failed", str(exc))

    def verify_and_decrypt(self) -> None:
        if not self.current_pack:
            messagebox.showwarning("Missing pack", "Encrypt/sign or import a pack first.")
            return
        try:
            spec = AgentSpecCrypto.verify_and_decrypt(self.current_pack, self.passphrase_entry.var.get())
            self.current_spec = spec
            self.decrypted_preview.delete("1.0", "end")
            self.decrypted_preview.insert("1.0", json.dumps(spec, indent=2, ensure_ascii=False))
            self.spec_status.set("Verified signature and decrypted agent spec.")
        except Exception as exc:
            messagebox.showerror("Verify + Decrypt failed", str(exc))

    def load_spec_into_runtime(self) -> None:
        if not self.current_spec:
            messagebox.showwarning("Missing spec", "Verify + decrypt a spec first.")
            return
        if not self.runtime:
            self.initialize_runtime()
        assert self.runtime is not None
        self.runtime.load_spec(self.current_spec)
        title = self.current_spec.get("title", "Untitled Spec")
        use_case = self.current_spec.get("use_case", "")
        self.runtime_status.set(f"Runtime initialized. Loaded spec: {title} — {use_case}")

    def export_pack(self) -> None:
        if not self.current_pack:
            messagebox.showwarning("Missing pack", "Encrypt/sign or import a pack first.")
            return
        path = filedialog.asksaveasfilename(title="Export Signed Pack", defaultextension=".json", filetypes=[("JSON files", "*.json")])
        if not path:
            return
        Path(path).write_text(self.current_pack.to_json(), encoding="utf-8")
        self.spec_status.set(f"Exported signed pack to {path}")

    def import_pack(self) -> None:
        path = filedialog.askopenfilename(title="Import Signed Pack", filetypes=[("JSON files", "*.json")])
        if not path:
            return
        raw = Path(path).read_text(encoding="utf-8")
        self.current_pack = SignedAgentPack.from_json(raw)
        self.pack_preview.delete("1.0", "end")
        self.pack_preview.insert("1.0", self.current_pack.to_json())
        self.spec_status.set(f"Imported signed pack from {path}")

    def choose_workspace(self) -> None:
        chosen = filedialog.askdirectory(title="Choose Workspace")
        if chosen:
            self.workspace_entry.var.set(chosen)

    def initialize_runtime(self) -> None:
        try:
            self.runtime = AgentRuntime(workspace_root=self.workspace_entry.var.get(), seed=self.seed_entry.var.get())
            loaded = ""
            if self.current_spec:
                self.runtime.load_spec(self.current_spec)
                loaded = f" Loaded spec: {self.current_spec.get('title', 'Untitled')}."
            self.runtime_status.set(f"Runtime initialized.{loaded}")
        except Exception as exc:
            messagebox.showerror("Runtime initialization failed", str(exc))

    def load_demo(self) -> None:
        self._replace_text(self.command_input, DEMO_COMMANDS)

    def compile_commands(self) -> None:
        try:
            if not self.runtime:
                self.initialize_runtime()
            assert self.runtime is not None
            encoded = self.runtime.compile_to_celestial(self.command_input.get("1.0", "end"))
            self.celestial_output.delete("1.0", "end")
            self.celestial_output.insert("1.0", encoded)
        except Exception as exc:
            messagebox.showerror("Compile failed", str(exc))

    def run_commands(self, celestial: bool) -> None:
        try:
            if not self.runtime:
                self.initialize_runtime()
            assert self.runtime is not None
            source = self.celestial_output.get("1.0", "end") if celestial else self.command_input.get("1.0", "end")
            result = self.runtime.execute(source, is_celestial=celestial)
            self.execution_output.delete("1.0", "end")
            self.execution_output.insert("1.0", result)
        except Exception as exc:
            messagebox.showerror("Run failed", str(exc))


def main() -> None:
    root = tk.Tk()
    style = ttk.Style()
    if "clam" in style.theme_names():
        style.theme_use("clam")
    CelestialDesktopApp(root)
    root.mainloop()


if __name__ == "__main__":
    main()
