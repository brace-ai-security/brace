from pathlib import Path

import yaml

ROOT = Path(__file__).resolve().parent.parent
settings = yaml.safe_load((ROOT / "config" / "settings.yaml").read_text())
tools_config = yaml.safe_load((ROOT / "config" / "tools.yaml").read_text())
release = yaml.safe_load((ROOT / "config" / "release.yaml").read_text())
