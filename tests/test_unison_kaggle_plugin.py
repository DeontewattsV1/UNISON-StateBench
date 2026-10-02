import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PLUGIN = ROOT / "plugins" / "unison-kaggle"


def test_unison_kaggle_plugin_manifest_is_portable():
    manifest = json.loads((PLUGIN / "plugin.json").read_text(encoding="utf-8"))
    assert manifest["$schema"] == "https://agent-plugins.org/schemas/1.0.0/plugin.schema.json"
    assert manifest["name"] == "unison-kaggle"
    assert manifest["version"] == "0.1.0"


def test_unison_kaggle_plugin_uses_official_kaggle_mcp():
    mcp = json.loads((PLUGIN / "mcp.json").read_text(encoding="utf-8"))
    server = mcp["mcpServers"]["kaggle"]
    assert server == {
        "type": "streamable-http",
        "url": "https://www.kaggle.com/mcp",
    }


def test_unison_skill_locks_empirical_identifiers():
    skill = (PLUGIN / "skills" / "unison-empirical" / "SKILL.md").read_text(
        encoding="utf-8"
    )
    assert "df10125d05f8271c613213851214ad8d37554363" in skill
    assert "e1818b8a62d207fbce204b542a1c90e6d0525d223dc4e98a996b0c5e215d8619" in skill
    assert "162 * N" in skill
    assert "IPR, RCR, CRR, FHR, CAL, PLR, AIR, SCR" in skill
    assert "Do not start" in skill
