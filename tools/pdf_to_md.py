"""Convert project PDFs using MinerU, with dry-run as the default."""

from pathlib import Path
import os
import sys

PROJECT_ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(PROJECT_ROOT))

from fondontology.corpus.mineru_batch import main


def _load_project_token() -> None:
    if os.getenv("MINERU_KEY") or os.getenv("MINERU_API_TOKEN"):
        return
    env_path = PROJECT_ROOT / ".env"
    if not env_path.is_file():
        return
    for line in env_path.read_text(encoding="utf-8").splitlines():
        key, separator, value = line.strip().partition("=")
        if separator and key in {"MINERU_KEY", "MINERU_API_TOKEN"}:
            value = value.strip()
            if value.startswith(("'", '"')) and value.endswith(value[0]):
                value = value[1:-1]
            if value:
                os.environ[key] = value

if __name__ == "__main__":
    _load_project_token()
    raise SystemExit(main())
