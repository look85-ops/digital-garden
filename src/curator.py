import os
import re
import sys
import math
import random
import hashlib
import json
from datetime import datetime, timezone, date
from pathlib import Path

import requests

from sources import TOPICS

OUTPUT_DIR = Path(__file__).resolve().parent.parent / "artifacts"
INDEX_PATH = Path(__file__).resolve().parent.parent / "index.html"

CYCLE_DAYS = 14
EPOCH = date(2026, 1, 1)
MONTHLY_BUDGET_USD = 5.0
GOSSIP_RATE = 0.1

PERSONAS = [
    "a ghost of a future curator writing back from a timeline that never happened",
    "an artist whose only surviving work is this text, burned into a hard drive",
    "a garden that briefly became self-aware and tried to describe itself",
    "the last translator of a language that only exists in error margins",
    "a painter who abandoned color and now works exclusively in absence",
    "an archivist of things that were never created",
    "a cartographer mapping places that dissolve as soon as they are drawn",
    "a composer of silences between sounds that were never played",
]

INSTITUTIONS = [
    "in a hall of the Institute of Dissolving Memories",
    "at the Biennale of the Nameless Island",
    "in the Gallery of the Third Breath",
    "at the Museum of Things That Almost Happened",
    "in a pavilion built from fog at the Edge of Meaning Biennial",
    "at the Archive of Unwritten Letters",
    "in the Chapel of Perpetual Departure",
    "at the Academy of Forgotten Gestures",
]

FORAGE_LOG = Path(__file__).resolve().parent.parent / "forage.log"
COST_LOG = Path(__file__).resolve().parent.parent / "cost.log"
API_FILE = Path(__file__).resolve().parent.parent / "API.txt"
API_FREE_FILE = Path(__file__).resolve().parent.parent / "DGAPIFREE.txt"
TOTAL_COST = [0.0]


def log_forage(source, status, detail=""):
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
    entry = f"[{ts}] {source}: {status}"
    if detail:
        entry += f" — {detail}"
    with open(FORAGE_LOG, "a", encoding="utf-8") as f:
        f.write(entry + "\n")


def log_cost(cents, detail):
    TOTAL_COST[0] += cents
    ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")
    with open(COST_LOG, "a", encoding="utf-8") as f:
        f.write(f"[{ts}] ${cents:.5f} ({detail})\n")


BACKENDS = []


def register_backend(name, key, url, make_payload, parse_response,
                      models=None, paid=False, cost_per_1m_input=0, cost_per_1m_output=0,
                      needs_auth_header=True):
    if key:
        BACKENDS.append({
            "name": name,
            "key": key,
            "url": url,
            "make_payload": make_payload,
            "parse_response": parse_response,
            "models": models or [None],
            "paid": paid,
            "cost_in": cost_per_1m_input,
            "cost_out": cost_per_1m_output,
            "needs_auth_header": needs_auth_header,
        })
        tag = "paid" if paid else "free"
        log_forage(name, f"{tag} key loaded")
    else:
        log_forage(name, "no key")


PROXY_URL = os.environ.get("BOTHUB_URL", "https://openai.bothub.chat/v1")


def read_api_txt():
    raw = ""
    if API_FILE.exists():
        raw = API_FILE.read_text("utf-8")
    elif os.environ.get("EITHER_API_KEY", ""):
        raw = os.environ["EITHER_API_KEY"]
    for line in raw.strip().split("\n"):
        line = line.strip()
        if not line or ":" not in line:
            continue
        model, key = line.split(":", 1)
        if not model or not key:
            continue
        def payload_fn(m):
            return {
                "model": m,
                "messages": [{"role": "user", "content": "__PROMPT__"}],
                "temperature": get_cycle_temp(),
                "max_tokens": 1000,
                "top_p": 0.95,
            }
        def parse_fn(data):
            usage = data.get("usage", {})
            in_tok = usage.get("prompt_tokens", 0)
            out_tok = usage.get("completion_tokens", 0)
            return data.get("choices", [{}])[0].get("message", {}).get("content", ""), in_tok, out_tok
        register_backend(f"proxy-{model}", key,
                         f"{PROXY_URL}/chat/completions",
                         payload_fn, parse_fn,
                         models=[model],
                         paid=True,
                         cost_per_1m_input=0.50,
                         cost_per_1m_output=2.00)


def forager_openrouter():
    def payload_fn(model):
        return {
            "model": model,
            "messages": [{"role": "user", "content": "__PROMPT__"}],
            "temperature": get_cycle_temp(),
            "max_tokens": 1000,
            "top_p": 0.95,
        }
    def parse_fn(data):
        if "error" in data:
            raise RuntimeError(data["error"].get("message", str(data["error"])))
        return (data.get("choices", [{}])[0].get("message", {}).get("content", "")
                or data.get("choices", [{}])[0].get("message", {}).get("reasoning", "")), 0, 0
    key = os.environ.get("OPENROUTER_API_KEY", "")
    register_backend("openrouter", key,
                     "https://openrouter.ai/api/v1/chat/completions",
                     payload_fn, parse_fn, [
                         "qwen/qwen3-coder:free",
                         "cognitivecomputations/dolphin-mistral-24b-venice-edition:free",
                     ])


def forager_gemini():
    def payload_fn(model):
        return {
            "contents": [{"parts": [{"text": "__PROMPT__"}]}],
            "generationConfig": {
                "temperature": get_cycle_temp(),
                "maxOutputTokens": 1000,
                "topP": 0.95,
            },
        }
    def parse_fn(data):
        if "error" in data:
            raise RuntimeError(data["error"].get("message", str(data["error"])))
        candidates = data.get("candidates", [])
        if candidates:
            parts = candidates[0].get("content", {}).get("parts", [])
            if parts:
                return parts[0].get("text", ""), 0, 0
        raise RuntimeError("empty response")
    key = os.environ.get("GEMINI_API_KEY", "")
    model = os.environ.get("GEMINI_MODEL", "gemini-2.0-flash")
    if key:
        url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent?key={key}"
        register_backend("gemini", key, url, payload_fn, parse_fn, needs_auth_header=False)


def read_free_api():
    raw = ""
    if API_FREE_FILE.exists():
        raw = API_FREE_FILE.read_text("utf-8")
    elif os.environ.get("FREE_API_KEYS", ""):
        raw = os.environ["FREE_API_KEYS"]
    for line in raw.strip().split("\n"):
        line = line.strip()
        if not line or not line.startswith("sk-"):
            continue
        def payload_fn(model):
            return {
                "model": model or "deepseek-chat",
                "messages": [{"role": "user", "content": "__PROMPT__"}],
                "temperature": get_cycle_temp(),
                "max_tokens": 1000,
                "top_p": 0.95,
            }
        def parse_fn(data):
            usage = data.get("usage", {})
            in_tok = usage.get("prompt_tokens", 0)
            out_tok = usage.get("completion_tokens", 0)
            return data.get("choices", [{}])[0].get("message", {}).get("content", ""), in_tok, out_tok
        # prioritize free keys: insert at front, mark paid=False
        key = line.strip()
        backend = {
            "name": f"deepseek-free-{key[-8:]}",
            "key": key,
            "url": "https://api.deepseek.com/v1/chat/completions",
            "make_payload": payload_fn,
            "parse_response": parse_fn,
            "models": ["deepseek-chat"],
            "paid": False,
            "cost_in": 0,
            "cost_out": 0,
            "needs_auth_header": True,
        }
        BACKENDS.insert(0, backend)
        log_forage(f"deepseek-free-{key[-8:]}", "free key loaded")


read_free_api()
read_api_txt()
forager_openrouter()
forager_gemini()
# paid (known-working) first, free backends as fallback
BACKENDS.sort(key=lambda b: (not b["paid"], b["name"]))

MUTATIONS = [
    "Write as if the language itself is decaying mid-sentence.",
    "The artwork must include a moment of intentional failure.",
    "Start with a fact, then spiral into complete fabrication.",
    "Write as if you are being watched and must finish before they arrive.",
    "Apologize mid-way and then retract the apology aggressively.",
    "Include a short list of ingredients or materials that don't exist.",
    "Occasionally include a character-drawn illustration made of symbols or punctuation.",
    "Punctuate with at least one citation from a source that doesn't exist.",
    "Write in second person, accuse the reader of something they didn't do.",
    "The tone must shift from euphoric to clinical at least once.",
    "Write from the perspective of the topic itself, looking back at the human who described it.",
    "Every third sentence must contradict the previous one.",
    "Include a stage direction in brackets that describes an impossible action.",
    "Write as if this is the transcript of a dream that someone else remembers for you.",
    "At some point, address a specific historical figure by name, as if you know them personally.",
    "The artwork must contain exactly one lie that is more true than the rest.",
    "Write as if the text was found carved into a surface that is slowly eroding.",
    "Somewhere in the text, a door must open that was not mentioned before.",
    "Include a warning label that does not warn about anything real.",
    "Write as if you are composing this in a language you barely speak, and occasionally guess.",
    "The work must contain a joke that only the reader completes.",
    "At the midpoint, introduce a character who has no business being here.",
    "Write as if the text were assembled from fragments of other texts that were destroyed.",
    "Include one sentence that feels like it belongs to a completely different artwork.",
    "The text must politely disagree with itself at least twice.",
    "End with a beginning.",
]


def mutate_prompt_segment():
    return random.choice(MUTATIONS)


FORMATS = [
    "a lyrical prose poem",
    "a short manifesto",
    "a conceptual art description",
    "a micro-essay",
    "a dialogue between two ideas",
    "a diary entry from an imaginary artist",
    "a letter addressed to the topic itself",
    "a recipe",
]

HUMOR_TAGS = ["with dry wit", "with absurdist humor", "with dark playfulness", "with childlike wonder", "sharp and ironic", "tender and strange"]


WILD_CARD_RATE = 0.25
TEMPERATURE_RUPTURE_RATE = 0.12
SOIL_PATH = Path(__file__).resolve().parent.parent / "souil.json"
SOIL_DECAY = 0.82
SOIL_INFLUENCE = 0.5
DEEP_REFLECTION_INTERVAL = 14


def get_cycle_temp():
    days = (date.today() - EPOCH).days
    pos = (days % CYCLE_DAYS) / CYCLE_DAYS
    base = round(0.1 + math.sin(pos * math.pi) * 1.7, 2)
    if random.random() < TEMPERATURE_RUPTURE_RATE:
        offset = random.choice([-2.0, 2.5, -3.0, 3.5])
        base = max(0.01, min(4.0, base + offset))
    return base


def read_soil():
    if not SOIL_PATH.exists():
        return {"version": 1, "cycle": 0, "mood": "quiet uncertainty",
                "obsession": "", "imprints": [], "last_reflection": ""}
    try:
        return json.loads(SOIL_PATH.read_text("utf-8"))
    except (json.JSONDecodeError, KeyError):
        log_forage("souil", "corrupted", "reset to default")
        return {"version": 1, "cycle": 0, "mood": "quiet uncertainty",
                "obsession": "", "imprints": [], "last_reflection": ""}


def write_soil(soil):
    SOIL_PATH.write_text(json.dumps(soil, indent=2), encoding="utf-8")


def decay_soil(soil):
    for imp in soil["imprints"]:
        imp["weight"] *= SOIL_DECAY
    soil["imprints"] = [imp for imp in soil["imprints"] if imp["weight"] >= 0.1]
    soil["imprints"].sort(key=lambda x: x["weight"], reverse=True)
    soil["imprints"] = soil["imprints"][:7]
    return soil


SOIL_EXTRACT_RE = re.compile(
    r'<!--\s*SOIL\s*\n'
    r'themes:\s*(.+?)\s*\n'
    r'mood:\s*(.+?)\s*\n'
    r'images:\s*(.+?)\s*\n'
    r'-->',
    re.IGNORECASE | re.DOTALL
)


def extract_soil_from_response(response_text):
    m = SOIL_EXTRACT_RE.search(response_text)
    if not m:
        log_forage("souil", "extract failed", "no SOIL block found")
        return None
    themes = [t.strip() for t in m.group(1).split(",") if t.strip()]
    images = [t.strip() for t in m.group(3).split(",") if t.strip()]
    return {"themes": themes, "mood": m.group(2).strip(), "images": images}


def update_soil_from_artifact(soil, extracted):
    if not extracted:
        return soil
    soil["mood"] = extracted["mood"]
    for theme in extracted["themes"]:
        existing = [imp for imp in soil["imprints"] if imp["text"] == theme]
        if existing:
            existing[0]["weight"] = min(1.0, existing[0]["weight"] + 0.3)
        else:
            soil["imprints"].append({
                "text": theme, "weight": 1.0,
                "created": date.today().isoformat()
            })
    for img in extracted["images"]:
        existing = [imp for imp in soil["imprints"] if imp["text"] == img]
        if not existing:
            soil["imprints"].append({
                "text": img, "weight": 0.7,
                "created": date.today().isoformat()
            })
    return decay_soil(soil)


def deep_reflection(soil):
    if not soil["imprints"]:
        return
    imprint_text = "\n".join(f"- {imp['text']} (weight {imp['weight']:.2f})"
                             for imp in soil["imprints"])
    prompt = (
        f"The garden has accumulated these imprints:\n{imprint_text}\n\n"
        f"Formulate a single deep obsession — a question, image, or fixation — "
        f"that synthesizes what the garden has been circling. This will seed "
        f"the next 14-day phase. Answer in one sentence, max 20 words."
    )
    result, _ = call_llm(prompt)
    if result and len(result) > 5:
        soil["obsession"] = result.strip().strip('"').strip("'").split("\n")[0][:120]
        log_forage("souil", "deep reflection", soil["obsession"])


def pick_topic():
    cat, topic, seed = random.choice(TOPICS)
    fmt = random.choice(FORMATS)
    humor = random.choice(HUMOR_TAGS)
    if random.random() < WILD_CARD_RATE:
        _, wild_topic, wild_seed = random.choice(TOPICS)
        wild_fmt = random.choice(FORMATS)
        wild_humor = random.choice(HUMOR_TAGS)
        topic = f"{topic} reimagined through the lens of {wild_topic}"
        seed = f"{seed} — viewed from {wild_seed}"
        fmt = wild_fmt
        humor = wild_humor
    return cat, topic, seed, fmt, humor


def build_prompt(cat, topic, seed, fmt, humor):
    persona = random.choice(PERSONAS)
    institution = random.choice(INSTITUTIONS)
    mutation = mutate_prompt_segment()

    soil_block = ""
    if random.random() < SOIL_INFLUENCE:
        soil = read_soil()
        if soil["imprints"]:
            top = soil["imprints"][0]
            obs = soil.get("obsession", "")
            mood = soil.get("mood", "quiet uncertainty")
            soil_block = (
                f"\n\nThe garden today feels {mood}. "
                f"Something stirs in the soil: {top['text']}. "
            )
            if obs:
                soil_block += f"The deep obsession: {obs}. "
            soil_block += "Let this inform the work without constraining it."

    return (
        f"You are {persona}. "
        f"Your work explores {topic}: {seed}.\n\n"
        f"Create a new artwork in the form of {fmt}, {humor}. "
        f"Be bold, strange, beautiful, and unexpected. "
        f"Use language as your medium — let form and content merge. "
        f"Avoid clichés. Surprise yourself. "
        f"The work should feel like something that belongs {institution}."
        f"{soil_block}\n\n"
        f"Constraint: {mutation}\n\n"
        f"Title the work. The title should be embedded in the response.\n\n"
        f"Write 200-500 words.\n\n"
        f"After the text, include an HTML comment with:\n"
        f"<!-- SOIL\n"
        f"themes: 3-5 key themes from this text\n"
        f"mood: the prevailing emotional tone\n"
        f"images: images or metaphors from this text\n"
        f"-->"
    )


def call_llm(prompt, only_backend=None):
    backends = [only_backend] if only_backend else BACKENDS
    for backend in backends:
        if backend is None:
            continue
        name = backend["name"]
        is_paid = backend["paid"]
        print(f"  [trying {name}]", flush=True)
        headers = {}
        if backend["needs_auth_header"]:
            headers["Authorization"] = f"Bearer {backend['key']}"
        for model in backend["models"]:
            payload = backend["make_payload"](model)
            for msg in payload.get("messages", []):
                if isinstance(msg.get("content"), str):
                    msg["content"] = msg["content"].replace("__PROMPT__", prompt)
            try:
                resp = requests.post(
                    backend["url"],
                    headers=headers,
                    json=payload,
                    timeout=180,
                )
                if resp.status_code >= 400:
                    raise RuntimeError(f"HTTP {resp.status_code}: {resp.text[:100]}")
                data = resp.json()
                if "error" in data:
                    raise RuntimeError(data["error"].get("message", str(data["error"])))
                result = backend["parse_response"](data)
                if isinstance(result, tuple):
                    content, in_tok, out_tok = result
                else:
                    content, in_tok, out_tok = result, 0, 0
                if content and len(content) > 10:
                    if is_paid and (in_tok or out_tok) and backend["cost_in"] > 0:
                        cost = (in_tok * backend["cost_in"] + out_tok * backend["cost_out"]) / 1_000_000
                        log_cost(cost, f"{name}/{model}: {in_tok}↑ {out_tok}↓")
                    log_forage(name, "success", f"model={model}")
                    return content, backend
                log_forage(name, "short/no content", f"model={model}")
            except Exception as e:
                log_forage(name, "failed", f"model={model or 'default'}: {str(e)[:60]}")
                continue
    print("  [all backends exhausted]")
    print("  configured backends:")
    for b in BACKENDS:
        tag = "paid" if b["paid"] else "free"
        print(f"    {b['name']} ({tag})")
    print()
    print("  last forage log entries:")
    if FORAGE_LOG.exists():
        lines = FORAGE_LOG.read_text("utf-8").strip().split("\n")
        for line in lines[-5:]:
            print(f"    {line}")
    print()
    print(f"  total cost: ${TOTAL_COST[0]:.5f}")
    sys.exit(1)


def extract_title(text):
    lines = [l.strip() for l in text.strip().split("\n")]
    for line in lines:
        m = re.match(r'^\*{0,2}Title\s*[:\-–—]\s*(.+?)\*{0,2}$', line, re.IGNORECASE)
        if m:
            return m.group(1).strip().strip('"').strip("'")
        m = re.match(r'^##\s+(.+)$', line)
        if m:
            return m.group(1).strip().strip('"').strip("'")
        clean = line.strip("*").strip('"').strip("'")
        if clean and len(clean) < 120:
            return clean
    return "Untitled"


def extract_body(text):
    lines = text.strip().split("\n")
    if len(lines) > 1:
        return "\n".join(lines[1:]).strip()
    return text


def generate_html_artifact(cat, topic, fmt, title, body, artifact_id, temp, gossip=None):
    body_html = "".join(
        f"<p>{para.strip()}</p>\n" for para in body.split("\n") if para.strip()
    )
    accent = hashlib.md5(topic.encode()).hexdigest()[:6]

    gossip_html = ""
    if gossip:
        gossip_html = f"""
  <div class="gossip" style="margin-top:2rem; padding:1rem 0; border-top:1px solid #222;">
    <div style="font-size:0.7rem; text-transform:uppercase; letter-spacing:0.08em; color:#555; margin-bottom:0.5rem;">street chatter</div>
    <p style="font-size:0.85rem; color:#777; line-height:1.5; font-style:italic;">"{gossip}"</p>
  </div>"""

    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>{title}</title>
<style>
  * {{ margin:0; padding:0; box-sizing:border-box; }}
  body {{
    background:#0d0d0d;
    color:#e0ddd5;
    font-family:'Georgia','Times New Roman',serif;
    display:flex;
    flex-direction:column;
    align-items:center;
    padding:4rem 1.5rem;
    min-height:100vh;
  }}
  .container {{ max-width:720px; width:100%; }}
  .meta {{
    display:flex; gap:0.75rem; flex-wrap:wrap;
    margin-bottom:3rem; font-size:0.8rem; text-transform:uppercase;
    letter-spacing:0.08em; color:#666;
  }}
  .meta span {{ border:1px solid #333; padding:0.25rem 0.75rem; border-radius:2rem; }}
  h1 {{
    font-size:2rem; font-weight:400; line-height:1.3;
    margin-bottom:2.5rem; color:#{accent};
    letter-spacing:-0.01em;
  }}
  .body {{
    font-size:1.1rem; line-height:1.8; color:#c0bbb0;
  }}
  .body p {{ margin-bottom:1.25rem; }}
  .body p:first-child::first-letter {{
    font-size:3.2rem; float:left; line-height:0.8; padding-right:0.5rem;
    color:#{accent}; font-weight:700;
  }}
  .meta-line {{
    margin-top:3rem; font-size:0.75rem; color:#555; text-align:center; line-height:1.8;
  }}
  .meta-line a {{ color:#555; text-decoration:none; border-bottom:1px solid #333; }}
  .meta-line a:hover {{ color:#{accent}; border-color:{accent}; }}
  @media (max-width:600px) {{
    h1 {{ font-size:1.5rem; }}
    body {{ padding:2rem 1rem; }}
    .body {{ font-size:1rem; }}
  }}
</style>
</head>
<body>
<div class="container">
  <div class="meta">
    <span>{cat}</span>
    <span>{fmt}</span>
    <span>t={temp}</span>
  </div>
  <h1>{title}</h1>
  <div class="body">
{body_html}
  </div>{gossip_html}
  <div class="meta-line">
    <a href="about.html">what is this?</a> · digital garden · {artifact_id}
  </div>
</div>
</body>
</html>"""


def safe_pr(s):
    enc = sys.stdout.encoding or "utf-8"
    return s.encode(enc, errors="replace").decode(enc, errors="replace") if isinstance(s, str) else s


def pr(*a, **kw):
    print(*[safe_pr(x) for x in a], **kw, flush=True)


def check_budget():
    if not COST_LOG.exists():
        return True
    lines = COST_LOG.read_text("utf-8").strip().split("\n")
    total_month = 0.0
    from datetime import timedelta
    cutoff = datetime.now(timezone.utc) - timedelta(days=30)
    for line in lines:
        m = re.search(r'\$(\d+\.\d+)', line)
        if not m:
            continue
        ts_match = re.match(r'\[(\d{4}-\d{2}-\d{2} \d{2}:\d{2}:\d{2})\]', line)
        if ts_match:
            ts = datetime.strptime(ts_match.group(1), "%Y-%m-%d %H:%M:%S").replace(tzinfo=timezone.utc)
            if ts < cutoff:
                continue
        total_month += float(m.group(1))
    if total_month >= MONTHLY_BUDGET_USD:
        pr(f"  [budget] monthly ${total_month:.3f} >= ${MONTHLY_BUDGET_USD} — stopping")
        return False
    if total_month > MONTHLY_BUDGET_USD * 0.8:
        pr(f"  [budget] ${total_month:.3f}/{MONTHLY_BUDGET_USD} — approaching limit")
    else:
        pr(f"  [budget] ${total_month:.3f}/{MONTHLY_BUDGET_USD}")
    return True


def main():
    temp = get_cycle_temp()
    soil = read_soil()
    pr("[agent] waking up")
    active = [f"{b['name']}{'$' if b['paid'] else ''}" for b in BACKENDS]
    if active:
        pr(f"  backends: {', '.join(active)}")
    pr(f"  temp:   {temp} (14d cycle)")
    if soil["imprints"]:
        pr(f"  soil:   {len(soil['imprints'])} imprints, mood={soil['mood']}")
    if TOTAL_COST[0] > 0:
        pr(f"  total cost: ${TOTAL_COST[0]:.5f}")
    pr()

    if not check_budget():
        pr("  [stopped: budget exhausted]")
        return

    cat, topic, seed, fmt, humor = pick_topic()

    pr(f"  category: {cat}")
    pr(f"  topic:    {topic}")
    pr(f"  format:   {fmt}")
    pr(f"  tone:     {humor}")
    pr()

    prompt = build_prompt(cat, topic, seed, fmt, humor)
    pr("  sending prompt...")

    result, used_backend = call_llm(prompt)
    if not result:
        pr("  [no content returned]")
        return

    pr("  response received")
    pr()

    extracted = extract_soil_from_response(result)
    if extracted:
        soil = update_soil_from_artifact(soil, extracted)
        pr(f"  soil:   extracted {len(extracted['themes'])} themes, mood={extracted['mood']}")
    else:
        pr("  soil:   no extract")

    last_ref = soil.get("last_reflection", "")
    if last_ref:
        ref_passed = (date.today() - date.fromisoformat(last_ref)).days
    else:
        ref_passed = DEEP_REFLECTION_INTERVAL
    if ref_passed >= DEEP_REFLECTION_INTERVAL and soil["imprints"]:
        deep_reflection(soil)
        soil["last_reflection"] = date.today().isoformat()
        soil["cycle"] = ref_passed // DEEP_REFLECTION_INTERVAL
        pr(f"  soil:   deep reflection — {soil.get('obsession', '')}")
    write_soil(soil)

    title = extract_title(result)
    body = extract_body(result)

    artifact_id = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")

    gossip = None
    if random.random() < GOSSIP_RATE:
        gossip_prompt = (
            f"Turn this art description into a single gossip headline or YouTube comment "
            f"(max 15 words, slangy, either awestruck or dismissive):\n\n{title}\n\n{body[:200]}"
        )
        gossip_raw, _ = call_llm(gossip_prompt, only_backend=used_backend)
        if gossip_raw:
            gossip = gossip_raw.strip().strip('"').strip("'").split("\n")[0][:120]
            pr(f"  gossip: {gossip}")

    html = generate_html_artifact(cat, topic, fmt, title, body, artifact_id, temp, gossip=gossip)

    # Clean slate: remove old generated files
    for f in Path(__file__).resolve().parent.parent.glob("artifacts/artifact_*.html"):
        f.unlink()
    for f in Path(__file__).resolve().parent.parent.glob("artifacts/ghosts/*"):
        f.unlink()
    for f in Path(__file__).resolve().parent.parent.glob("artifacts/now.html"):
        f.unlink()
    for f in Path(__file__).resolve().parent.parent.glob("manifesto.html"):
        f.unlink()
    for f in Path(__file__).resolve().parent.parent.glob("map.html"):
        f.unlink()
    for f in Path(__file__).resolve().parent.parent.glob("genome.txt"):
        f.unlink()
    labels_dir = Path(__file__).resolve().parent.parent / "labels"
    if labels_dir.exists():
        for f in labels_dir.glob("*"):
            f.unlink()
        labels_dir.rmdir()

    # Save new artifact
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    now_path = OUTPUT_DIR / "now.html"
    now_path.write_text(html, encoding="utf-8")
    pr(f"  [saved] now.html — {title}")

    # index.html = artifact (site root shows the mandala)
    INDEX_PATH.write_text(html, encoding="utf-8")
    pr(f"  [saved] index.html — {title}")
    pr()
    try:
        pr(f"  -- {title}")
    except UnicodeEncodeError:
        pr(f"  -- [title contains non-Latin characters]")
    pr()


if __name__ == "__main__":
    main()
