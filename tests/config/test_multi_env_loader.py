import os
import json
from pathlib import Path
from src.config.multi_env_loader import MultiEnvConfigLoader, diff_envs

def _make_sample(root: Path):
    (root / "config" / "base").mkdir(parents=True)
    (root / "config" / "dev").mkdir()
    (root / "config" / "prod").mkdir()
    (root / "config" / "staging").mkdir()
    (root / "config" / "base" / "core.yaml").write_text("""
services:
  api:
    url: https://base
    timeout: 2
workers:
  - w1
secrets:
  api_key: BASEKEY
""", encoding="utf-8")
    (root / "config" / "dev" / "core.yaml").write_text("""
services:
  api:
    timeout: 5
workers:
  - dev-only
secrets:
  api_key: DEVKEY
""", encoding="utf-8")
    (root / "config" / "prod" / "core.yaml").write_text("""
services:
  api:
    timeout: 3
workers:
  - prod1
  - prod2
secrets:
  api_key: PRODKEY
""", encoding="utf-8")

def test_dev_merge(tmp_path, monkeypatch):
    _make_sample(tmp_path)
    monkeypatch.chdir(tmp_path)
    loader = MultiEnvConfigLoader()
    os.environ["BYKILT_ENV"] = "dev"
    cfg = loader.load()
    assert cfg["services"]["api"]["url"] == "https://base"
    assert cfg["services"]["api"]["timeout"] == 5
    assert cfg["workers"] == ["dev-only"]

def test_secret_mask_artifact(tmp_path, monkeypatch):
    _make_sample(tmp_path)
    monkeypatch.chdir(tmp_path)
    loader = MultiEnvConfigLoader()
    loader.load("prod")
    from src.utils.fs_paths import get_artifacts_base_dir
    art_dir = get_artifacts_base_dir() / "runs"
    assert art_dir.exists()
    newest = sorted(art_dir.iterdir())[-1]
    data = json.loads((newest / "effective_config.json").read_text(encoding="utf-8"))
    assert data["config"]["secrets"]["api_key"] == "***"
    assert "secrets.api_key" in data["masked_hashes"]

def test_diff(tmp_path, monkeypatch):
    _make_sample(tmp_path)
    monkeypatch.chdir(tmp_path)
    d = diff_envs("dev", "prod")
    assert d["from"] == "dev" and d["to"] == "prod"
    assert "workers.0" in d["added"] or "workers.0" in d["removed"] or d["changed"]
    