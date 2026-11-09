"""Loads lens configs from polymath/lenses/*/*.json, limited to the active build."""

import json
from functools import lru_cache

from .config import BUILD, LENS_DIR
from .models import LensConfig


@lru_cache(maxsize=1)
def load_lenses() -> list[LensConfig]:
    lenses = []
    for path in sorted(LENS_DIR.glob("*/*.json")):
        lens = LensConfig.model_validate(json.loads(path.read_text(encoding="utf-8")))
        if BUILD in lens.builds:
            lenses.append(lens)
    return sorted(lenses, key=lambda l: l.order)


def get_lens(lens_id: str) -> LensConfig | None:
    return next((l for l in load_lenses() if l.id == lens_id), None)
