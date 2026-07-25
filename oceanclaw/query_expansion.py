"""Domain query expansion for Korean maintenance questions."""

from __future__ import annotations


EXPANSION_TERMS = {
    "엔진 오일": "engine oil oil level dipstick MIN MAX",
    "오일": "oil engine oil",
    "점검": "check inspect inspection",
    "확인": "check inspect",
    "방법": "procedure how to",
    "연료 필터": "fuel filter replace replacement drain water",
    "필터": "filter replacement",
    "교체": "replace replacement",
    "냉각수": "coolant coolant level cooling circuit",
    "냉각": "cooling coolant",
    "과열": "overheating high coolant temperature warning alarm",
    "경고": "warning alarm notice",
    "배터리": "battery switch charging terminal voltage",
    "시동": "start stop engine start",
    "정지": "stop shutdown engine",
    "일일": "daily checks before operation",
    "매일": "daily checks before operation",
    "정비": "maintenance inspection procedure",
    "토크": "torque tighten tightening N m",
    "조임": "tighten tightening torque",
    "해수": "seawater cooling circuit",
    "윤활": "lubricating oil engine oil",
}


def expand_query(query: str) -> str:
    additions: list[str] = []
    normalized_query = query.lower()

    for korean, english_terms in EXPANSION_TERMS.items():
        if korean in normalized_query:
            additions.append(english_terms)

    if not additions:
        return query

    deduped_terms = []
    seen = set()
    for addition in additions:
        for term in addition.split():
            key = term.lower()
            if key not in seen:
                deduped_terms.append(term)
                seen.add(key)

    return f"{query} {' '.join(deduped_terms)}"
