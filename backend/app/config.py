"""Settings, read from the environment and the repo-root .env (the same file the front end uses)."""

import os
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
BACKEND_DIR = ROOT / "backend"


def _load_dotenv(path: Path) -> None:
    """Tiny .env reader. Real environment variables win over the file."""
    if not path.exists():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, _, value = line.partition("=")
        os.environ.setdefault(key.strip(), value.strip().strip('"').strip("'"))


_load_dotenv(ROOT / ".env")

# One flag drives both the front end and the backend: showcase (default) or full.
BUILD = os.environ.get("POLYMATH_BUILD") or os.environ.get("VITE_BUILD") or "showcase"
if BUILD not in ("showcase", "full"):
    BUILD = "showcase"

DB_PATH = Path(os.environ.get("POLYMATH_DB") or BACKEND_DIR / "data" / "polymath.sqlite")
LENS_DIR = ROOT / "lenses"

# Optional. Raises the PubMed rate limit from 3 to 10 requests/second. Never put it in code.
NCBI_API_KEY = os.environ.get("NCBI_API_KEY") or os.environ.get("PUBMED_API_KEY") or ""

# Identifies this client to arXiv/NCBI. Set CONTACT_EMAIL if you want to be reachable by them.
CONTACT_EMAIL = os.environ.get("CONTACT_EMAIL", "")
USER_AGENT = "polymath-course-project/0.1" + (f" (mailto:{CONTACT_EMAIL})" if CONTACT_EMAIL else "")

DIGEST_DAYS = int(os.environ.get("DIGEST_DAYS", "7"))
CORS_ORIGINS = [o.strip() for o in os.environ.get(
    "CORS_ORIGINS", "http://localhost:5173,http://localhost:5174,http://127.0.0.1:5173"
).split(",") if o.strip()]
