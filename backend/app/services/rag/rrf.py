"""Reciprocal Rank Fusion de rankings semântico e textual."""


def rrf_merge(
    sem_rows: list[dict],
    text_rows: list[dict],
    top_k: int,
    k: int = 60,
) -> list[dict]:
    """Combina rankings via Reciprocal Rank Fusion clássico (pesos iguais)."""

    def _key(row: dict) -> tuple:
        return (
            row.get("law_number"),
            row.get("article") or "",
            row.get("chunk_text") or "",
        )

    scores: dict[tuple, float] = {}
    merged: dict[tuple, dict] = {}

    for rank, row in enumerate(sem_rows):
        key = _key(row)
        scores[key] = scores.get(key, 0.0) + 1.0 / (k + rank + 1)
        merged.setdefault(key, row)
    for rank, row in enumerate(text_rows):
        key = _key(row)
        scores[key] = scores.get(key, 0.0) + 1.0 / (k + rank + 1)
        merged.setdefault(key, row)

    ordered = sorted(
        merged.items(),
        key=lambda kv: scores[kv[0]],
        reverse=True,
    )
    return [row for _, row in ordered[:top_k]]
