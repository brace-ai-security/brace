from pathlib import Path
import json
import tomllib
from .settings import Settings
from .host_settings import HostSettings
from .clock import Clock
from .bootstrap import build
from .host import Host

ROOT = Path(__file__).resolve().parent.parent

def build_host():
    with (ROOT / 'config/local.toml').open('rb') as handle:
        service = tomllib.load(handle)['service']
    with (ROOT / 'config/host.toml').open('rb') as handle:
        host = tomllib.load(handle)['host']
    catalog = json.loads((ROOT / 'config/tools.json').read_text())
    registry = build(Settings(**service).validate())
    return Host(registry, catalog, HostSettings(**host).validate(), Clock())
