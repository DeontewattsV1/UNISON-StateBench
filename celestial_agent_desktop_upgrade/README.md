# Celestial Desktop Prototype — Agent Spec Editor Upgrade

This desktop prototype adds a dedicated **Agent Spec Editor** panel to the local, permissioned runtime.

## Added features

- form-based editing of the agent spec
- **Encrypt + Sign**
- **Verify + Decrypt**
- **Load into Runtime**
- **Export Signed Pack**
- **Import Signed Pack**
- local workspace boundary enforcement
- signed manifests with Ed25519
- encrypted specs with AES-GCM and passphrase-derived keys

## Run

```bash
pip install -r requirements.txt
python app.py
```

## Notes

- All command execution stays inside the selected local workspace.
- The runtime does not make network calls.
- There is no recovery key. Keep your passphrase safe.
- Creator credit is embedded in the default spec and export flow for **TDD**.
