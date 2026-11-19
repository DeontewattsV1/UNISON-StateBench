
from __future__ import annotations
import base64, json, os, shutil, time
from pathlib import Path
from cryptography.exceptions import InvalidSignature
try:
    from watchdog.events import FileSystemEventHandler
    from watchdog.observers import Observer
except Exception:
    class FileSystemEventHandler:
        pass

    class Observer:
        def schedule(self, *args, **kwargs):
            return None
        def start(self):
            return None
        def stop(self):
            return None
        def join(self):
            return None
from celestial_agent.agent_spec_crypto import AgentSpecCrypto, EncryptedAgentPack
from orchestrator import handle_decrypted_policy

BASE_DIR = Path(__file__).resolve().parent
VAULT_DIR = BASE_DIR / "vault"
MANIFESTS_DIR = BASE_DIR / "manifests"
DECRYPTED_DIR = BASE_DIR / "decrypted"
QUARANTINE_DIR = BASE_DIR / "quarantine"
KEYS_DIR = BASE_DIR / "keys"

def setup_workspace() -> None:
    for d in [VAULT_DIR, MANIFESTS_DIR, DECRYPTED_DIR, QUARANTINE_DIR, KEYS_DIR]:
        d.mkdir(parents=True, exist_ok=True)

def wait_for_stable_file(path: Path, checks: int = 3, delay: float = 0.4) -> None:
    last_size = -1
    stable_count = 0
    while stable_count < checks:
        if not path.exists():
            raise FileNotFoundError(f"File disappeared while waiting: {path}")
        size = path.stat().st_size
        if size == last_size:
            stable_count += 1
        else:
            stable_count = 0
            last_size = size
        time.sleep(delay)

def safe_move_to_quarantine(path: Path) -> None:
    if not path.exists():
        return
    target = QUARANTINE_DIR / path.name
    counter = 1
    while target.exists():
        target = QUARANTINE_DIR / f"{path.stem}_{counter}{path.suffix}"
        counter += 1
    shutil.move(str(path), str(target))

def load_split_pack(base_name: str) -> EncryptedAgentPack:
    enc_path = VAULT_DIR / f"{base_name}.enc"
    manifest_path = MANIFESTS_DIR / f"{base_name}.json"
    sig_path = MANIFESTS_DIR / f"{base_name}.sig"
    if not enc_path.exists():
        raise FileNotFoundError(f"Missing encrypted payload: {enc_path}")
    if not manifest_path.exists():
        raise FileNotFoundError(f"Missing manifest: {manifest_path}")
    if not sig_path.exists():
        raise FileNotFoundError(f"Missing signature: {sig_path}")
    manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
    ciphertext = enc_path.read_bytes()
    signature = sig_path.read_bytes()
    nonce_b64 = manifest.get("nonce_b64")
    salt_b64 = manifest.get("salt_b64")
    if not nonce_b64 or not salt_b64:
        raise ValueError("Manifest missing nonce_b64 or salt_b64.")
    return EncryptedAgentPack(
        manifest=manifest,
        ciphertext_b64=base64.b64encode(ciphertext).decode("utf-8"),
        nonce_b64=nonce_b64,
        salt_b64=salt_b64,
        signature_b64=base64.b64encode(signature).decode("utf-8"),
    )

class VaultHandler(FileSystemEventHandler):
    def __init__(self, passphrase: str):
        self.passphrase = passphrase
        self.processed: set[str] = set()

    def _process(self, filepath: Path) -> None:
        if filepath.suffix != ".enc":
            return
        key = str(filepath.resolve())
        if key in self.processed:
            return
        print(f"\n[⚡] Detected: {filepath.name}")
        try:
            wait_for_stable_file(filepath)
            pack = load_split_pack(filepath.stem)
            print(" ├── Verifying signature...")
            spec = AgentSpecCrypto.verify_and_decrypt(pack, self.passphrase)
            print(" ├── Signature valid")
            print(" ├── AES-GCM decryption successful")
            out_path = DECRYPTED_DIR / f"{filepath.stem}.json"
            out_path.write_text(json.dumps(spec, indent=2), encoding="utf-8")
            print(f" ├── Wrote decrypted spec: {out_path.name}")
            print(" └── Policy ready")
            handle_decrypted_policy(spec)
            self.processed.add(key)
        except InvalidSignature:
            print(" └── [SECURITY ALERT] Invalid Ed25519 signature")
            safe_move_to_quarantine(filepath)
        except Exception as exc:
            print(f" └── [ERROR] {exc}")
            safe_move_to_quarantine(filepath)

    def on_created(self, event):
        if not event.is_directory:
            self._process(Path(event.src_path))

    def on_modified(self, event):
        if not event.is_directory:
            self._process(Path(event.src_path))

def main() -> None:
    setup_workspace()
    passphrase = os.environ.get("PHASEFORM_PASSPHRASE")
    if not passphrase:
        raise RuntimeError("Set PHASEFORM_PASSPHRASE in your environment before starting the watcher.")
    print("Initializing PhaseForm Agent Vault Watcher...")
    print(f"[*] Vault: {VAULT_DIR}")
    print(f"[*] Manifests: {MANIFESTS_DIR}")
    print(f"[*] Decrypted: {DECRYPTED_DIR}")
    print(f"[*] Quarantine: {QUARANTINE_DIR}")
    print("[*] Monitoring for new *.enc policy packs...")
    print("[*] Press Ctrl+C to exit.")
    handler = VaultHandler(passphrase=passphrase)
    observer = Observer()
    observer.schedule(handler, str(VAULT_DIR), recursive=False)
    observer.start()
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n[*] Shutting down watcher.")
        observer.stop()
    observer.join()

if __name__ == "__main__":
    main()
