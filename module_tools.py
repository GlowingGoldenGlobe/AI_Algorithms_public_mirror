import os
import json as _json
import urllib.parse
import urllib.request

def _http_get(url, headers=None, timeout=20):
    req = urllib.request.Request(url, headers=headers or {})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.read()

def _http_post(url, headers=None, data=None, timeout=30):
    body = None
    if data is not None:
        body = _json.dumps(data).encode("utf-8")
    req = urllib.request.Request(url, headers=headers or {}, data=body, method="POST")
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.read()

_CONFIG_CACHE = None

def _clear_config_cache():
    """Clear the in-process config cache.

    Useful when another module updates config.json and the same Python process
    needs to see the change without restarting.
    """
    global _CONFIG_CACHE
    _CONFIG_CACHE = None

def _load_config():
    global _CONFIG_CACHE
    if _CONFIG_CACHE is not None:
        return _CONFIG_CACHE
    try:
        base_dir = os.path.dirname(os.path.abspath(__file__))
        path = os.path.join(base_dir, "config.json")
        with open(path, "r", encoding="utf-8") as f:
            _CONFIG_CACHE = _json.load(f)
    except Exception:
        _CONFIG_CACHE = {}
    return _CONFIG_CACHE

def search_internet(query, top=5):
    """
    Internet search using available providers (pref: SerpAPI, then Bing Web Search).
    Configure via env vars: SERPAPI_API_KEY or BING_SEARCH_API_KEY.
    Returns dict with provider and list of {title, link, snippet}.
    """
    cfg = _load_config() or {}
    search_cfg = cfg.get("search", {})
    pref = (search_cfg.get("provider") or "auto").lower()
    top = int(search_cfg.get("top", top))
    query_enc = urllib.parse.quote_plus(query)

    serp_key = os.getenv("SERPAPI_API_KEY")
    if serp_key and (pref in ("auto", "serpapi")):
        try:
            url = f"https://serpapi.com/search.json?engine=google&q={query_enc}&api_key={serp_key}&num={top}"
            raw = _http_get(url)
            data = _json.loads(raw.decode("utf-8"))
            results = []
            for item in (data.get("organic_results") or [])[:top]:
                results.append({
                    "title": item.get("title"),
                    "link": item.get("link"),
                    "snippet": item.get("snippet")
                })
            return {"provider": "serpapi", "results": results}
        except Exception as e:
            return {"provider": "serpapi", "error": str(e), "results": []}

    bing_key = os.getenv("BING_SEARCH_API_KEY")
    if bing_key and (pref in ("auto", "bing")):
        try:
            url = f"https://api.bing.microsoft.com/v7.0/search?q={query_enc}&count={top}"
            raw = _http_get(url, headers={"Ocp-Apim-Subscription-Key": bing_key})
            data = _json.loads(raw.decode("utf-8"))
            value = (((data or {}).get("webPages") or {}).get("value") or [])
            results = []
            for item in value[:top]:
                results.append({
                    "title": item.get("name"),
                    "link": item.get("url"),
                    "snippet": item.get("snippet")
                })
            return {"provider": "bing", "results": results}
        except Exception as e:
            return {"provider": "bing", "error": str(e), "results": []}

    # Fallback stub or forced stub
    return {
        "provider": "stub" if pref in ("auto", "stub") else pref,
        "results": [{"title": f"Search result for: {query}", "link": "", "snippet": "No provider configured."}]
    }

def query_llm(prompt, max_tokens=300):
    """
    LLM generation via OpenAI or Azure OpenAI.
    Configure via env vars:
      - OPENAI_API_KEY (and optional OPENAI_MODEL)
      - or AZURE_OPENAI_API_KEY + AZURE_OPENAI_ENDPOINT + AZURE_OPENAI_DEPLOYMENT
    Returns dict with provider and text.
    """
    cfg = _load_config() or {}
    llm_cfg = cfg.get("llm", {})
    pref = (llm_cfg.get("provider") or "auto").lower()
    max_tokens = int(llm_cfg.get("max_tokens", max_tokens))

    openai_key = os.getenv("OPENAI_API_KEY")
    if openai_key and (pref in ("auto", "openai")):
        try:
            model = os.getenv("OPENAI_MODEL", llm_cfg.get("openai_model", "gpt-4o-mini"))
            url = "https://api.openai.com/v1/chat/completions"
            payload = {
                "model": model,
                "messages": [{"role": "user", "content": prompt}],
                "max_tokens": max_tokens,
                "temperature": 0.2
            }
            raw = _http_post(url, headers={
                "Authorization": f"Bearer {openai_key}",
                "Content-Type": "application/json"
            }, data=payload)
            data = _json.loads(raw.decode("utf-8"))
            text = ((data.get("choices") or [{}])[0].get("message") or {}).get("content", "")
            return {"provider": "openai", "text": text, "model": model}
        except Exception as e:
            return {"provider": "openai", "error": str(e), "text": ""}

    az_key = os.getenv("AZURE_OPENAI_API_KEY")
    az_ep = os.getenv("AZURE_OPENAI_ENDPOINT")
    az_deploy = os.getenv("AZURE_OPENAI_DEPLOYMENT")
    if az_key and az_ep and az_deploy and (pref in ("auto", "azure-openai")):
        try:
            api_version = os.getenv("AZURE_OPENAI_API_VERSION", "2024-02-15-preview")
            url = f"{az_ep.rstrip('/')}/openai/deployments/{az_deploy}/chat/completions?api-version={api_version}"
            payload = {
                "messages": [{"role": "user", "content": prompt}],
                "max_tokens": max_tokens,
                "temperature": 0.2
            }
            raw = _http_post(url, headers={
                "api-key": az_key,
                "Content-Type": "application/json"
            }, data=payload)
            data = _json.loads(raw.decode("utf-8"))
            text = ((data.get("choices") or [{}])[0].get("message") or {}).get("content", "")
            return {"provider": "azure-openai", "text": text, "deployment": az_deploy}
        except Exception as e:
            return {"provider": "azure-openai", "error": str(e), "text": ""}

    # Fallback stub or forced stub
    return {"provider": "stub" if pref in ("auto", "stub") else pref, "text": f"No LLM provider configured. Prompt: {prompt[:160]}"}

def analyze_beneficial_detrimental(data):
    # Placeholder scoring
    return "Beneficial" if "good" in data else "Detrimental"
# module_tools.py
def _tokenize(text: str):
    import re
    if text is None:
        return []
    if not isinstance(text, str):
        try:
            text = _json.dumps(text, ensure_ascii=False)
        except Exception:
            text = str(text)
    return re.findall(r"[A-Za-z0-9_]+", text.lower())


def _jaccard(a_tokens, b_tokens) -> float:
    a = set(a_tokens or [])
    b = set(b_tokens or [])
    if not a and not b:
        return 0.0
    if not a or not b:
        return 0.0
    return len(a & b) / float(len(a | b))


def _cosine_sparse(a: dict, b: dict) -> float:
    """Cosine similarity between sparse {term: weight} dicts."""
    if not a or not b:
        return 0.0
    # dot product over smaller dict
    if len(a) > len(b):
        a, b = b, a
    dot = 0.0
    for k, av in a.items():
        bv = b.get(k)
        if bv is not None:
            dot += float(av) * float(bv)
    na = sum(float(v) * float(v) for v in a.values()) ** 0.5
    nb = sum(float(v) * float(v) for v in b.values()) ** 0.5
    if na == 0.0 or nb == 0.0:
        return 0.0
    return dot / (na * nb)


def _tfidf_vector(tokens: list, idf: dict, max_terms: int = 2048) -> dict:
    """Build a sparse TF-IDF vector from tokens.

    - TF: raw count
    - IDF: provided mapping
    - Term cap: keeps work bounded and deterministic (top terms by tf, tie-break by term).
    """
    from collections import Counter

    c = Counter(tokens or [])
    if not c:
        return {}
    items = list(c.items())
    items.sort(key=lambda kv: (-kv[1], kv[0]))
    if max_terms and len(items) > int(max_terms):
        items = items[: int(max_terms)]
    vec = {}
    for term, tf in items:
        w = float(tf) * float(idf.get(term, 1.0))
        if w:
            vec[term] = w
    return vec


def similarity(content, current_subject, long_term_index, exclude_id=None):
    """Deterministic similarity score in [0,1].

    Uses a lightweight token-based Jaccard similarity:
    - content vs current_subject tokens
    - content vs tokens of stored semantic items (semantic index)

    The semantic-corpus comparison excludes `exclude_id` to avoid self-matching.
    """
    cfg = _load_config() or {}
    sim_cfg = cfg.get('similarity', {}) if isinstance(cfg, dict) else {}
    method = str(sim_cfg.get('method', 'jaccard')).lower()
    max_docs = int(sim_cfg.get('max_docs', 200))
    max_terms = int(sim_cfg.get('max_terms', 2048))

    content_tokens = _tokenize(content)
    subject_tokens = _tokenize(current_subject)
    subj_sim = _jaccard(content_tokens, subject_tokens)

    # Compare against semantic index (built from LongTermStore/Semantic).
    try:
        base_dir = os.path.dirname(os.path.abspath(__file__))
        idx_path = os.path.join(base_dir, 'LongTermStore', 'Index', 'semantic_index.json')
        if not os.path.exists(idx_path):
            build_semantic_index(base_dir)
        with open(idx_path, 'r', encoding='utf-8') as f:
            idx = _json.load(f) or {}
        id_to_tokens = idx.get('id_to_tokens') or {}

        # Deterministic doc selection
        ids = sorted(id_to_tokens.keys())
        if max_docs and len(ids) > max_docs:
            ids = ids[:max_docs]

        best = 0.0
        if method == 'tfidf':
            import math

            # Build IDF from document frequencies over selected ids
            N = 0
            df = {}
            for _id in ids:
                if exclude_id is not None and str(_id) == str(exclude_id):
                    continue
                toks = set(id_to_tokens.get(_id) or [])
                if not toks:
                    continue
                N += 1
                for t in toks:
                    df[t] = df.get(t, 0) + 1
            if N <= 0:
                return round(subj_sim, 3)

            idf = {}
            # stable idf construction
            for t in sorted(df.keys()):
                # Smooth IDF: log((N+1)/(df+1)) + 1
                idf[t] = math.log((N + 1.0) / (float(df[t]) + 1.0)) + 1.0
            idf_default = math.log((N + 1.0) / 1.0) + 1.0

            # Vectorize content once
            # Use idf_default for unseen terms to avoid zeroing everything
            content_vec = _tfidf_vector(content_tokens, {**idf, **{}}, max_terms=max_terms)
            # Patch in default idf for terms not in idf (without exploding mapping size)
            if content_vec:
                for term in list(content_vec.keys()):
                    if term not in idf:
                        content_vec[term] = float(content_vec[term]) / 1.0 * idf_default

            for _id in ids:
                if exclude_id is not None and str(_id) == str(exclude_id):
                    continue
                toks = id_to_tokens.get(_id) or []
                if not toks:
                    continue
                # doc is binary presence * idf
                doc_vec = {}
                for t in toks:
                    doc_vec[t] = float(idf.get(t, idf_default))
                sim = _cosine_sparse(content_vec, doc_vec)
                if sim > best:
                    best = sim
        else:
            # Default: jaccard
            for _id in ids:
                if exclude_id is not None and str(_id) == str(exclude_id):
                    continue
                sim = _jaccard(content_tokens, id_to_tokens.get(_id) or [])
                if sim > best:
                    best = sim

        # Prefer the stronger of subject similarity and corpus similarity.
        return round(max(subj_sim, best), 3)
    except Exception:
        return round(subj_sim, 3)

def familiarity(data_id, occurrence_count, labels):
    """
    Check recurrence and prior labels for familiarity.
    Returns dict with recurs=True/False, has_prior_useful_labels=True/False.
    """
    return {
        "recurs": occurrence_count > 1,
        "has_prior_useful_labels": "important" in labels or "review" in labels
    }

def usefulness(content, objectives, current_activity):
    """
    Determine if content is useful for current objectives or activity.
    Accepts objectives as a list of strings or dicts with 'content'/'labels'.
    Returns 'useful_now', 'useful_later', or 'not_useful'.
    """
    content_l = (content or "").lower()
    act_l = (current_activity or "").lower() if isinstance(current_activity, str) else str(current_activity).lower()
    # direct keyword hint
    if 'useful' in content_l:
        return 'useful_now'
    for obj in objectives or []:
        if isinstance(obj, str):
            o = obj.lower()
            if o in content_l or o in act_l:
                return "useful_now"
        elif isinstance(obj, dict):
            otext = str(obj.get("content", "")).lower()
            labels = [str(x).lower() for x in obj.get("labels", [])]
            if any(l in content_l or l in act_l for l in labels) or (otext and any(w for w in otext.split() if w in content_l)):
                return "useful_now"
    return "not_useful"

def synthesis_potential(content, current_subject, related_items, objectives, long_term_index):
    """
    Check if combining content + related items can advance objectives.
    Accepts objectives as strings or dicts.
    Returns True/False.
    """
    content_l = (content or "").lower()
    def obj_matches(obj):
        if isinstance(obj, str):
            return obj.lower() in content_l
        if isinstance(obj, dict):
            otext = str(obj.get("content", "")).lower()
            labels = [str(x).lower() for x in obj.get("labels", [])]
            return any(l in content_l for l in labels) or (otext and any(w for w in otext.split() if w in content_l))
        return False
    if related_items and any(obj_matches(o) for o in (objectives or [])):
        return True
    return False

def compare_against_objectives(content, objectives):
    """
    Compare content against objectives (strings or dicts).
    Returns 'aligned', 'conflict', or 'unknown'.

    NOTE: 'conflict' should be reserved for explicit contradiction signals,
    not used as the default when no match is found.
    """
    content_l = (content or "").lower()

    # Explicit conflict cues (heuristic) should override alignment-by-keyword.
    # This prevents accidental "aligned" when the content contains generic
    # objective words but also clearly signals contradiction/conflict.
    conflict_markers = (
        "conflict",
        "contradict",
        "contradiction",
        "inconsistent",
        "detrimental",
        "harmful",
    )
    # Small guard against obvious negations
    negated_conflict = ("no conflict" in content_l) or ("without conflict" in content_l)
    if any(m in content_l for m in conflict_markers):
        if not negated_conflict:
            return "conflict"

    for obj in objectives or []:
        if isinstance(obj, str) and obj.lower() in content_l:
            return "aligned"
        if isinstance(obj, dict):
            otext = str(obj.get("content", "")).lower()
            labels = [str(x).lower() for x in obj.get("labels", [])]
            if any(l in content_l for l in labels) or (otext and any(w for w in otext.split() if w in content_l)):
                return "aligned"

    return "unknown"

def search_related(content, k=5):
    """
    Scan LongTermStore/Semantic and LongTermStore/Events for keywords found in the
    provided content. Returns a list of related item dicts with 'id' and 'path'.
    A simple heuristic extracts alphanumeric keywords of length >= 4.
    """
    import os, json, re

    base_dir = os.path.dirname(os.path.abspath(__file__))
    search_dirs = [
        os.path.join(base_dir, "LongTermStore", "Semantic"),
        os.path.join(base_dir, "LongTermStore", "Events"),
    ]

    words = set(w.lower() for w in re.findall(r"[A-Za-z0-9]+", content))
    keywords = {w for w in words if len(w) >= 4}
    results = []

    for d in search_dirs:
        if not os.path.isdir(d):
            continue
        for root, _, files in os.walk(d):
            for fn in files:
                if not fn.endswith('.json'):
                    continue
                path = os.path.join(root, fn)
                try:
                    with open(path, 'r', encoding='utf-8') as f:
                        data = json.load(f)
                except Exception:
                    continue

                text_blob = ' '.join([
                    str(data.get('id', '')),
                    str(data.get('content', '')),
                    ' '.join(map(str, data.get('labels', [])))
                ]).lower()

                if any(kw in fn.lower() or kw in text_blob for kw in keywords):
                    results.append({
                        'id': data.get('id', os.path.splitext(fn)[0]),
                        'path': path
                    })
                    if len(results) >= k:
                        return results

    return results

def procedural_match(objectives, labels):
    """
    Decide which modules/tools to use based on objectives and labels.
    Returns a plan: which modules, how many terminals, and labels.
    """
    plan = {"modules": [], "terminals": 0, "labels": list(labels)}

    # Objectives can be strings or dicts; normalize to labels set
    obj_labels = set()
    for obj in objectives or []:
        if isinstance(obj, str):
            obj_labels.add(obj.lower())
        elif isinstance(obj, dict):
            for l in obj.get("labels", []):
                obj_labels.add(str(l).lower())
            text = str(obj.get("content", "")).lower()
            if "synthesis" in text:
                obj_labels.add("synthesis")

    # Module selection based on objectives
    if "measurement" in obj_labels:
        plan["modules"].append("module_measure")
        plan["labels"].append("measurement")
    if "awareness" in obj_labels:
        plan["modules"].append("module_awareness")
        plan["labels"].append("awareness")
    if "synthesis" in obj_labels:
        # Synthesis favors search + measurement
        plan["modules"].extend(["search_internet", "module_measure"])
        plan["labels"].append("synthesis")

    # Labels can also request search
    if "search" in plan["labels"]:
        if "search_internet" not in plan["modules"]:
            plan["modules"].append("search_internet")

    # Scale terminals to number of modules, cap at 8
    plan["terminals"] = min(8, max(1, len(plan["modules"])) )

    return plan

# ---------------- New: Data Contracts, Path Safety, Indexing -----------------
import re as _re
from typing import Any, Dict, List, Optional

SCHEMA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), 'schemas')

def _load_schema(schema_name: str) -> Dict[str, Any]:
    path = os.path.join(SCHEMA_DIR, f"{schema_name}.schema.json")
    try:
        with open(path, 'r', encoding='utf-8') as f:
            return _json.load(f)
    except Exception:
        return {}

def validate_record(record: Dict[str, Any], schema_name: str) -> bool:
    schema = _load_schema(schema_name)
    if not schema or schema.get('type') != 'object':
        return False
    required = schema.get('required', [])
    props = schema.get('properties', {})
    for key in required:
        if key not in record:
            return False
    type_map = {
        'string': str,
        'number': (int, float),
        'object': dict,
        'array': list,
        'boolean': bool
    }
    for key, spec in props.items():
        if key in record:
            expected = spec.get('type')
            if isinstance(expected, list):
                if not any(isinstance(record[key], type_map.get(t, object)) for t in expected):
                    return False
            elif isinstance(expected, str):
                if not isinstance(record[key], type_map.get(expected, object)):
                    return False
    return True


def validate_relational_state(relational_state: Dict[str, Any]) -> bool:
    """Validate the canonical relational_state structure.

    This repo intentionally avoids a full JSONSchema dependency.
    This function enforces a deterministic, shallow structural contract:
    - required keys exist
    - required key types match
    - top-level keys are limited to the canonical set
    - entity/relation rows have minimal required fields
    """
    if not isinstance(relational_state, dict):
        return False

    required = (
        'entities',
        'relations',
        'constraints',
        'objective_links',
        'spatial_measurement',
        'decision_trace',
    )
    for k in required:
        if k not in relational_state:
            return False

    allowed = set(required) | {'focus_snapshot', 'conceptual_measurement'}
    for k in relational_state.keys():
        if k not in allowed:
            return False

    if not isinstance(relational_state.get('entities'), list):
        return False
    if not isinstance(relational_state.get('relations'), list):
        return False
    if not isinstance(relational_state.get('constraints'), list):
        return False
    if not isinstance(relational_state.get('objective_links'), list):
        return False
    sm = relational_state.get('spatial_measurement')
    if sm is not None and not isinstance(sm, dict):
        return False
    if not isinstance(relational_state.get('decision_trace'), dict):
        return False
    fs = relational_state.get('focus_snapshot')
    if fs is not None and not isinstance(fs, dict):
        return False

    # Minimal row-level checks (do not enforce full shapes).
    for e in relational_state.get('entities') or []:
        if not isinstance(e, dict):
            return False
        if not isinstance(e.get('id'), str) or not e.get('id'):
            return False
        if not isinstance(e.get('type'), str) or not e.get('type'):
            return False

    for r in relational_state.get('relations') or []:
        if not isinstance(r, dict):
            return False
        if not isinstance(r.get('subj'), str) or not isinstance(r.get('pred'), str) or not isinstance(r.get('obj'), str):
            return False

    for c in relational_state.get('constraints') or []:
        if not isinstance(c, dict):
            return False
        if 'type' in c and not isinstance(c.get('type'), str):
            return False

    for ol in relational_state.get('objective_links') or []:
        if not isinstance(ol, dict):
            return False
        oid = ol.get('objective_id')
        if oid is not None and not isinstance(oid, str):
            return False

    return True

ID_PATTERN = _re.compile(r'^[A-Za-z0-9_-]+$')

def sanitize_id(data_id: str, max_len: int = 80) -> str:
    if not isinstance(data_id, str):
        raise ValueError('data_id must be a string')
    if '..' in data_id:
        raise ValueError('data_id must not contain ..')
    if '/' in data_id or '\\' in data_id:
        raise ValueError('data_id must not contain path separators')
    if len(data_id) == 0 or len(data_id) > max_len:
        raise ValueError('data_id length invalid')
    if not ID_PATTERN.match(data_id):
        raise ValueError('data_id has invalid characters')
    return data_id

def safe_join(root: str, relpath: str) -> str:
    if not isinstance(root, str) or not isinstance(relpath, str):
        raise ValueError('paths must be strings')
    norm_root = os.path.abspath(root)
    target = os.path.abspath(os.path.join(norm_root, relpath))
    if os.path.commonpath([norm_root, target]) != norm_root:
        raise ValueError('unsafe path: escapes root')
    return target

def _ts() -> str:
    import datetime
    return datetime.datetime.now(datetime.timezone.utc).replace(microsecond=0).isoformat().replace('+00:00','Z')

def build_semantic_index(root: Optional[str] = None) -> Dict[str, Any]:
    base = root or os.path.dirname(os.path.abspath(__file__))
    store_dir = os.path.join(base, 'LongTermStore', 'Semantic')
    index_dir = os.path.join(base, 'LongTermStore', 'Index')
    os.makedirs(index_dir, exist_ok=True)
    index_path = os.path.join(index_dir, 'semantic_index.json')
    id_to_tokens: Dict[str, List[str]] = {}
    try:
        for name in os.listdir(store_dir):
            if not name.endswith('.json'):
                continue
            _id = os.path.splitext(name)[0]
            try:
                with open(os.path.join(store_dir, name), 'r', encoding='utf-8') as f:
                    rec = _json.load(f)
            except Exception:
                rec = {}
            content = rec.get('content', '')
            text = content if isinstance(content, str) else _json.dumps(content, ensure_ascii=False)
            tokens = sorted(set(_re.findall(r'[A-Za-z0-9_]+', text.lower())))
            id_to_tokens[_id] = tokens
    except FileNotFoundError:
        pass
    # determinism: use fixed timestamp if enabled and sort ids
    cfg = _load_config() or {}
    det = cfg.get('determinism', {})
    fixed_ts = det.get('fixed_timestamp') if det.get('deterministic_mode') else None
    index = {
        'schema_version': '1.0',
        'last_build_ts': fixed_ts or _ts(),
        'id_to_tokens': {k: id_to_tokens[k] for k in sorted(id_to_tokens.keys())}
    }
    try:
        with open(index_path, 'w', encoding='utf-8') as f:
            _json.dump(index, f, ensure_ascii=False, indent=2)
    except Exception:
        pass
    return index

# ---------------- Phase 7: Description Layer ----------------
def describe(content, context=None):
    """Lightweight description builder without external NLP.
    Returns dict: entities, claims, constraints, questions, action_candidates.
    """
    text = content if isinstance(content, str) else _json.dumps(content, ensure_ascii=False)
    words = [w for w in text.split() if len(w) > 3]
    entities = []
    seen = set()
    for w in words[:10]:
        lw = w.strip('.,:;"\'()').lower()
        if lw and lw not in seen:
            entities.append({"name": lw, "type": "token", "attributes": {}})
            seen.add(lw)
    claims = []
    if entities:
        for e in entities[:3]:
            claims.append({
                "subject": e["name"],
                "predicate": "related_to",
                "object": entities[0]["name"],
                "confidence": 0.5
            })
    constraints = []
    questions = []
    if context:
        questions.append({"text": f"How does {entities[0]['name']} relate to context?", "priority": "medium"})
    action_candidates = [{"action": "measure", "reason": "initial assessment", "expected_outcome": "signals"}]
    return {
        "entities": entities,
        "claims": claims,
        "constraints": constraints,
        "questions": questions,
        "action_candidates": action_candidates
    }

def match_procedure(similarity_score: float, usefulness: str, has_conflict: bool, base_dir: str = None):
    """Phase 16: match a stored procedure based on simple trigger conditions."""
    base = base_dir or os.path.dirname(os.path.abspath(__file__))
    proc_dir = os.path.join(base, 'LongTermStore', 'Procedural')
    try:
        # Prefer template file if it matches
        tpl = os.path.join(proc_dir, 'procedure_template.json')
        if os.path.exists(tpl):
            try:
                with open(tpl, 'r', encoding='utf-8') as f:
                    p = _json.load(f)
                trig = p.get('trigger_conditions', {})
                if similarity_score >= float(trig.get('similarity_min', 0)) and (usefulness == trig.get('usefulness', usefulness)):
                    return {"procedure": p, "path": tpl}
            except Exception:
                pass
        for name in os.listdir(proc_dir):
            if not name.endswith('.json'):
                continue
            path = os.path.join(proc_dir, name)
            with open(path, 'r', encoding='utf-8') as f:
                p = _json.load(f)
            trig = p.get('trigger_conditions', {})
            # Relax contradiction requirement to allow matching when similarity/usefulness fit
            if similarity_score >= float(trig.get('similarity_min', 0)) and (usefulness == trig.get('usefulness', usefulness)):
                return {"procedure": p, "path": path}
    except Exception:
        pass
    return None