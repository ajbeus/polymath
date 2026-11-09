"""Lens-specific scorers. A lens names one in its config ("filter": "worm_voc"); lenses without one
use the generic keyword scorer in app/scoring.py. Each filter returns (score 0..1, why) or None to
reject the paper for that lens."""

from typing import Callable, Optional

from ..sources import PaperRecord
from . import worm_voc

FILTERS: dict[str, Callable[[PaperRecord], Optional[tuple[float, str]]]] = {
    "worm_voc": worm_voc.score,
}
