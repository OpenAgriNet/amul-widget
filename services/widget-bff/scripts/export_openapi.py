from __future__ import annotations

import json
from pathlib import Path

from widget_bff.config import Settings
from widget_bff.main import create_app

repository_root = Path(__file__).resolve().parents[3]
destination = repository_root / "packages" / "contracts" / "openapi.json"
application = create_app(
    Settings(environment="test", jwt_secret="contract-export-secret-at-least-32-chars")
)
destination.write_text(
    json.dumps(application.openapi(), indent=2, sort_keys=True) + "\n",
    encoding="utf-8",
)
print(destination)
