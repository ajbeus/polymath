"""Worm-lab relevance filter for C. elegans odor responses.

Ported from abstract_parser.py (the scoring half: regex families, odor_score, score_relevance).
The rules and weights are unchanged; only the file/CSV/fetch code moved elsewhere
(app/sources/pubmed.py). Abstracts are only a FILTER: they nominate papers, and the real labels
come from full text later. Tune these weights against hand review (and the eval set, once it exists).
"""

import re
from typing import Optional

from ..sources import PaperRecord

# --- relevance terms (regex stems, case-insensitive) ---------------------
WORM_STRONG = re.compile(r"\b(c\.\s?elegans|caenorhabditis)\b", re.I)
WORM_WEAK = re.compile(r"\bnematodes?\b|\bworms?\b", re.I)

CHEMO = re.compile(
    r"\b(chemota[cx]\w*|chemosens\w*|chemoattract\w*|chemorepel\w*|olfact\w*|"
    r"odou?r\w*|volatile\w*|attract\w*|repel\w*|repuls\w*|avoid\w*|aversi\w*)",
    re.I,
)
DIRECTION = re.compile(
    r"\b(attract\w*|repel\w*|repuls\w*|avoid\w*|aversi\w*|chemoattract\w*|"
    r"chemorepel\w*|neutral)\b",
    re.I,
)
GOOD_MESH = {"Chemotaxis", "Olfactory Perception", "Smell", "Odorants",
             "Olfactory Receptor Neurons", "Chemoreceptor Cells"}

# --- tiered odor score -----------------------------------------------------
# Each family counts ONCE per paper. Salt/taste chemotaxis is real chemotaxis but not volatile,
# so it is penalised; aging/disease papers often use chemotaxis only as a readout, so small penalty.
SCORE_FAMILIES = {
    "odor":       (3, re.compile(r"\b(odou?r\w*|smell\w*)", re.I)),
    # Review fixes (2026-11): "volatile anesthetic" (isoflurane) is not an odor; and the stem
    # "chemotax" missed "chemotactic" (chemota[cx] catches both).
    "volatile":   (3, re.compile(r"\b(volatile(?!\s+anesth)\w*|VOCs?)\b", re.I)),
    "olfactory":  (2, re.compile(r"\bolfact\w*", re.I)),
    "chemotaxis": (2, re.compile(r"\b(chemota[cx]\w*|chemosens\w*|chemoattract\w*|chemorepel\w*)", re.I)),
    "attract":    (2, re.compile(r"\b(attract\w*|repel\w*|repuls\w*)", re.I)),
    "avoid":      (1, re.compile(r"\b(avoid\w*|aversi\w*)", re.I)),
}
PENALTY_FAMILIES = {
    "salt_taste":    (3, re.compile(r"\b(salts?|nacl|sodium chloride|gustat\w*|taste\w*)\b", re.I)),
    "aging_disease": (1, re.compile(r"\b(lifespan|life span|longevity|neurodegenerat\w*|amyloid|parkinson\w*|alzheimer\w*)\b", re.I)),
}
MESH_BONUS = 2    # per good MeSH heading, capped at 2 headings
RELEVANT_MIN = 5  # score needed (with C. elegans named) to be "relevant"
MAYBE_MIN = 2     # score needed to be "maybe"

# Maps odor_score to the 0..1 stage-1 score the API reports. A score of 12 or more is a near-perfect fit.
SCORE_SCALE = 12

def split_sentences(text):
    """Cheap sentence splitter; good enough for abstracts."""
    return [s.strip() for s in re.split(r"(?<=[.!?])\s+(?=[A-Z])", text) if s.strip()]


def odor_score(blob, good_mesh):
    """Weighted odor-relevance score plus a readable breakdown, e.g. 'odor+3;olfactory+2;salt_taste-3'."""
    score, parts = 0, []
    for name, (weight, rx) in SCORE_FAMILIES.items():
        if rx.search(blob):
            score += weight
            parts.append(f"{name}+{weight}")
    for name, (weight, rx) in PENALTY_FAMILIES.items():
        if rx.search(blob):
            score -= weight
            parts.append(f"{name}-{weight}")
    bonus = MESH_BONUS * min(len(good_mesh), 2)
    if bonus:
        score += bonus
        parts.append(f"mesh+{bonus}")
    return score, ";".join(parts)


def score_relevance(rec):
    """Add relevance fields to a dict with title, abstract and mesh.

    relevant : names C. elegans AND odor_score >= RELEVANT_MIN
    maybe    : a worm named and odor_score >= MAYBE_MIN, OR strong odor language with no worm named,
               OR a worm paper with no abstract (title-only, so we can't judge it)
    off_topic: everything else
    """
    blob = f"{rec['title']} {rec['abstract']}"
    worm_strong = bool(WORM_STRONG.search(blob)) or any(
        "Caenorhabditis elegans" in m for m in rec["mesh"])
    worm_weak = bool(WORM_WEAK.search(blob))
    has_worm = worm_strong or worm_weak
    chemo_terms = sorted({m.group(0).lower() for m in CHEMO.finditer(blob)})
    good_mesh = sorted(set(rec["mesh"]) & GOOD_MESH)
    score, detail = odor_score(blob, good_mesh)

    if worm_strong and score >= RELEVANT_MIN:
        label = "relevant"
    elif has_worm and score >= MAYBE_MIN:
        label = "maybe"
    elif score >= RELEVANT_MIN:  # strong odor language, no worm named
        label = "maybe"
    else:
        label = "off_topic"
    if not rec["abstract"] and has_worm and label == "off_topic":
        label = "maybe"

    hints = [s for s in split_sentences(rec["abstract"]) if DIRECTION.search(s)]

    rec.update({
        "relevance": label,
        "worm_match": "strong" if worm_strong else ("weak" if worm_weak else "none"),
        "odor_score": score,
        "score_detail": detail,
        "chemo_terms": ";".join(chemo_terms),
        "good_mesh": ";".join(good_mesh),
        "hint_sentences": " || ".join(hints),
        "has_abstract": bool(rec["abstract"]),
    })
    return rec


def score(paper: PaperRecord) -> Optional[tuple[float, str]]:
    """Adapter used by the lens pipeline: (0..1 score, why) or None if the paper is off topic."""
    mesh = paper.extras.get("mesh") or paper.categories
    rec = score_relevance({"title": paper.title, "abstract": paper.abstract, "mesh": list(mesh)})
    if rec["relevance"] == "off_topic":
        return None
    if rec["worm_match"] != "strong":
        return None  # lens decision: C. elegans must be named (excludes plant-parasitic nematodes etc.)
    value = min(1.0, max(0.05, rec["odor_score"] / SCORE_SCALE))
    detail = rec["score_detail"] or "no scoring terms"
    worm = {"strong": "C. elegans named", "weak": "worm/nematode named", "none": "no worm named"}[rec["worm_match"]]
    return round(value, 3), f"Worm VOC filter rated this {rec['relevance']} ({worm}; {detail})."
