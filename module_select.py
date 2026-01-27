def select_information(source):
    """Select and rank information from a semantic file or content.
    Returns dict with ranking entries including relevance_score and reason_codes.
    """
    import json, os
    ranking = []
    try:
        # If source is a file path, load it; else treat as string content
        if os.path.exists(source):
            with open(source, "r", encoding="utf-8") as f:
                record = json.load(f)
            content = str(record.get("content", ""))
            data_id = record.get("id", os.path.basename(source))
        else:
            content = str(source)
            data_id = "unknown"
        # Simple scoring: length and keyword presence
        relevance_score = min(len(content), 100) / 100.0
        reason_codes = []
        for kw in ("synthesis", "useful", "beneficial"):
            if kw in content.lower():
                reason_codes.append(kw)
        ranking.append({
            "id": data_id,
            "relevance_score": relevance_score,
            "reason_codes": reason_codes,
            "objective_alignment": "aligned" if "beneficial" in reason_codes else "unknown"
        })
        return {"ranking": ranking[:10]}
    except Exception as e:
        return {"error": str(e)}


def rank(items, objectives=None):
    """Rank a list of items against optional objectives.

    items: list of dicts or strings. If dict, expects keys {id, content}.
    objectives: list of objective dicts with optional keywords.

    Returns list of {id, relevance_score, reason_codes, objective_alignment}.
    """
    ranked = []
    obj_keywords = set()
    try:
        for o in (objectives or []):
            kws = o.get("keywords") if isinstance(o, dict) else None
            if isinstance(kws, list):
                for k in kws:
                    obj_keywords.add(str(k).lower())
        for it in items:
            if isinstance(it, dict):
                data_id = it.get("id", "unknown")
                content = str(it.get("content", ""))
            else:
                data_id = "unknown"
                content = str(it)
            base_score = min(len(content), 200) / 200.0
            reasons = []
            for kw in ("synthesis", "useful", "beneficial"):
                if kw in content.lower():
                    reasons.append(kw)
            # objective keyword boost
            alignment = "unknown"
            if obj_keywords:
                hits = sum(1 for k in obj_keywords if k in content.lower())
                if hits:
                    base_score = min(1.0, base_score + min(hits * 0.1, 0.3))
                    alignment = "aligned"
                    reasons.append("objective_match")
            ranked.append({
                "id": data_id,
                "relevance_score": round(base_score, 3),
                "reason_codes": reasons,
                "objective_alignment": alignment
            })
        # Top-N
        ranked.sort(key=lambda x: x["relevance_score"], reverse=True)
        return ranked[:10]
    except Exception as e:
        return [{"error": str(e)}]