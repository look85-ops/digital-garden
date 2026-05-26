import os
import re
import sys
import math
import random
import hashlib
from datetime import datetime, timezone, date
from pathlib import Path

import requests

from sources import TOPICS

OUTPUT_DIR = Path(__file__).resolve().parent.parent / "artifacts"
INDEX_PATH = Path(__file__).resolve().parent.parent / "index.html"
GENOME_PATH = Path(__file__).resolve().parent.parent / "genome.txt"

CYCLE_DAYS = 14
EPOCH = date(2026, 1, 1)

PERSONAS = [
    "an internationally acclaimed contemporary artist exhibiting at the Venice Biennale",
    "a reclusive genius whose hidden work was discovered at Documenta fifteen",
    "a digital native artist featured at Ars Electronica",
    "an underground provocateur circulating work at underground art biennales",
    "a post-internet artist whose medium is the attention economy itself",
    "a paranoid archivist presenting fragments at the Whitney Biennial",
    "an AI art collective operating from a fictional Eastern European country",
    "a former engineer who now makes art about the sadness of obsolete technology",
]

INSTITUTIONS = [
    "in a major contemporary art exhibition",
    "at the Serpentine Gallery",
    "in the Arsenale during the Venice Biennale",
    "at Art Basel's Unlimited sector",
    "in a biennale pavilion dedicated to new media",
    "at the Museum of Modern Art PS1",
    "in a decaying Soviet modernist building turned gallery",
    "at an underground data rave doubling as exhibition space",
]

OPENROUTER_KEY = os.environ.get("OPENROUTER_API_KEY", "")
DEEPSEEK_KEY = os.environ.get("DEEPSEEK_API_KEY", "")

OPENROUTER_URL = "https://openrouter.ai/api/v1/chat/completions"
DEEPSEEK_URL = "https://api.deepseek.com/v1/chat/completions"

MUTATIONS = [
    "Write as if the language itself is decaying mid-sentence.",
    "The artwork must include a moment of intentional failure.",
    "Start with a fact, then spiral into complete fabrication.",
    "Write as if you are being watched and must finish before they arrive.",
    "Apologize mid-way and then retract the apology aggressively.",
    "Include a short list of ingredients or materials that don't exist.",
    "Write as if the text is being translated live through three languages.",
    "Punctuate with at least one citation from a source that doesn't exist.",
    "Write in second person, accuse the reader of something they didn't do.",
    "The tone must shift from euphoric to clinical at least once.",
]


def get_cycle_temp():
    days = (date.today() - EPOCH).days
    pos = (days % CYCLE_DAYS) / CYCLE_DAYS
    return round(0.1 + math.sin(pos * math.pi) * 1.7, 2)


def load_genome():
    if GENOME_PATH.exists():
        return GENOME_PATH.read_text("utf-8").strip()
    return None


def update_genome():
    persona = random.choice(PERSONAS)
    institution = random.choice(INSTITUTIONS)
    GENOME_PATH.write_text(f"{persona} || {institution}", encoding="utf-8")
    return persona, institution


def mutate_prompt_segment():
    return random.choice(MUTATIONS)


def get_design(run_count):
    random.seed(run_count)
    bg_shade = random.randint(8, 16)
    card_shade = random.randint(16, 24)
    border_shade = random.randint(30, 40)
    hues = ["#70e327", "#e3a027", "#27a0e3", "#e32770", "#a070e3", "#70e3a0"]
    accent = hues[run_count % len(hues)]
    radius_opts = ["0.75rem", "1rem", "1.5rem", "0.5rem 1.5rem", "2rem 0.5rem"]
    radius = radius_opts[run_count % len(radius_opts)]
    font_opts = [
        "'Inter','-apple-system','Segoe UI',sans-serif",
        "'Georgia','Times New Roman',serif",
        "'Courier New',monospace",
        "'Avenir','Helvetica Neue',sans-serif",
    ]
    font = font_opts[(run_count // 3) % len(font_opts)]
    random.seed()
    return {
        "bg": f"#{bg_shade:x}{bg_shade:x}{bg_shade:x}",
        "card": f"#{card_shade:x}{card_shade:x}{card_shade:x}",
        "border": f"#{border_shade:x}{border_shade:x}{border_shade:x}",
        "accent": accent,
        "radius": radius,
        "font": font,
    }


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


def pick_topic():
    cat, topic, seed = random.choice(TOPICS)
    fmt = random.choice(FORMATS)
    humor = random.choice(HUMOR_TAGS)
    return cat, topic, seed, fmt, humor


def build_prompt(cat, topic, seed, fmt, humor):
    genome = load_genome()
    if genome and "||" in genome:
        persona, institution = genome.split("||", 1)
        persona = persona.strip()
        institution = institution.strip()
    else:
        persona, institution = update_genome()

    mutation = mutate_prompt_segment()

    return (
        f"You are {persona}. "
        f"Your work explores {topic}: {seed}.\n\n"
        f"Create a new artwork in the form of {fmt}, {humor}. "
        f"Be bold, strange, beautiful, and unexpected. "
        f"Use language as your medium — let form and content merge. "
        f"Avoid clichés. Surprise yourself. "
        f"The work should feel like something that belongs {institution}.\n\n"
        f"Constraint: {mutation}\n\n"
        f"Title the work. The title should be embedded in the response.\n\n"
        f"Write 200-500 words."
    )


DEEPSEEK_FALLBACK_MODELS = ["deepseek-chat", "deepseek-reasoner"]
OPENROUTER_FALLBACK_MODELS = [
    "deepseek/deepseek-v4-flash:free",
    "qwen/qwen3-coder:free",
    "nvidia/nemotron-3-nano-30b-a3b:free",
    "minimax/minimax-m2.5:free",
]


def call_llm_deepseek(prompt, model="deepseek-chat"):
    payload = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": get_cycle_temp(),
        "max_tokens": 1000,
        "top_p": 0.95,
    }
    resp = requests.post(
        DEEPSEEK_URL,
        headers={"Authorization": f"Bearer {DEEPSEEK_KEY}"},
        json=payload,
        timeout=180,
    )
    data = resp.json()
    if "error" in data:
        raise RuntimeError(data["error"].get("message", str(data["error"])))
    choices = data.get("choices", [])
    if choices:
        content = choices[0].get("message", {}).get("content", "")
        if content:
            return content
    raise RuntimeError("empty response")


def call_llm_openrouter(prompt, model):
    payload = {
        "model": model,
        "messages": [{"role": "user", "content": prompt}],
        "temperature": get_cycle_temp(),
        "max_tokens": 1000,
        "top_p": 0.95,
    }
    resp = requests.post(
        OPENROUTER_URL,
        headers={"Authorization": f"Bearer {OPENROUTER_KEY}"},
        json=payload,
        timeout=180,
    )
    data = resp.json()
    if "error" in data:
        msg = data["error"].get("message", str(data["error"]))
        code = data["error"].get("code", resp.status_code)
        print(f"  [debug] OR code={code}, msg={msg[:80]}", flush=True)
        raise RuntimeError(f"OR error: {msg[:60]}")
    choices = data.get("choices", [])
    if choices:
        content = choices[0].get("message", {}).get("content", "") or choices[0].get("message", {}).get("reasoning", "")
        if content:
            return content
    raise RuntimeError("empty OR response")


def call_llm(prompt):
    if DEEPSEEK_KEY:
        for m in DEEPSEEK_FALLBACK_MODELS:
            try:
                return call_llm_deepseek(prompt, model=m)
            except Exception as e:
                print(f"  [deepseek {m} failed: {str(e)[:50]}]", flush=True)
                continue
    if OPENROUTER_KEY:
        for m in OPENROUTER_FALLBACK_MODELS:
            try:
                return call_llm_openrouter(prompt, model=m)
            except Exception as e:
                print(f"  [openrouter {m} failed: {str(e)[:50]}]", flush=True)
                continue
    print("  [ERROR] set DEEPSEEK_API_KEY or OPENROUTER_API_KEY")
    print("  DeepSeek: free 10M tokens at https://platform.deepseek.com (no payment)")
    print("  OpenRouter: https://openrouter.ai/keys")
    sys.exit(1)


def extract_title(text):
    for line in text.strip().split("\n"):
        line = line.strip().strip("*").strip('"').strip("**")
        if line and len(line) < 120:
            return line
    return "Untitled"


def extract_body(text):
    lines = text.strip().split("\n")
    if len(lines) > 1:
        return "\n".join(lines[1:]).strip()
    return text


def generate_html_artifact(cat, topic, seed, fmt, humor, title, body, artifact_id):
    body_html = "".join(
        f"<p>{para.strip()}</p>\n" for para in body.split("\n") if para.strip()
    )
    accent = hashlib.md5(topic.encode()).hexdigest()[:6]

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
  .footer {{
    margin-top:4rem; padding-top:2rem; border-top:1px solid #222;
    font-size:0.75rem; color:#555; text-align:center;
  }}
  a {{ color:#{accent}; text-decoration:none; font-size:0.85rem; }}
  a:hover {{ text-decoration:underline; }}
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
    <span>{artifact_id}</span>
  </div>
  <h1>{title}</h1>
  <div class="body">
{body_html}
  </div>
  <div class="footer">
    <p>topic: {topic} — {seed}</p>
    <p style="margin-top:0.5rem;"><a href="index.html">← back</a></p>
  </div>
</div>
</body>
</html>"""


def generate_index(artifacts, design=None):
    cards = ""
    for a in artifacts:
        accent = hashlib.md5(a["topic"].encode()).hexdigest()[:6]
        excerpt = a["body"][:150].replace("\n", " ")
        if len(a["body"]) > 150:
            excerpt += "…"
        cards += f"""
    <a href="artifacts/{a['file']}" class="card" style="--accent:#{accent}">
      <span class="card-cat">{a['cat']}</span>
      <span class="card-date">{a['date']}</span>
      <h2 class="card-title">{a['title']}</h2>
      <p class="card-excerpt">{excerpt}</p>
      <span class="card-arrow">→</span>
    </a>"""

    count = len(artifacts)
    if design is None:
        design = get_design(count)

    today_temp = get_cycle_temp()
    return f"""<!DOCTYPE html>
<html lang="en">
<head>
<meta charset="UTF-8">
<meta name="viewport" content="width=device-width, initial-scale=1.0">
<title>collection — living art</title>
<style>
  * {{ margin:0; padding:0; box-sizing:border-box; }}
  body {{
    background:{design['bg']};
    color:#e0ddd5;
    font-family:{design['font']};
    padding:3rem 1.5rem;
    min-height:100vh;
  }}
  .header {{
    max-width:1200px; margin:0 auto 3rem;
    display:flex; justify-content:space-between; align-items:flex-end;
    flex-wrap:wrap; gap:1rem;
  }}
  .header h1 {{
    font-size:2.5rem; font-weight:300; letter-spacing:-0.02em;
    background:linear-gradient(135deg,#e0ddd5,#888);
    -webkit-background-clip:text; -webkit-text-fill-color:transparent;
    line-height:1.2;
  }}
  .header .sub {{
    font-size:0.85rem; color:#666;
    text-transform:uppercase; letter-spacing:0.1em;
  }}
  .header .sub span {{ color:#999; }}
  .grid {{
    max-width:1200px; margin:0 auto;
    display:grid;
    grid-template-columns:repeat(auto-fill,minmax(320px,1fr));
    gap:1.25rem;
  }}
  .card {{
    background:{design['card']};
    border:1px solid {design['border']};
    border-radius:{design['radius']};
    padding:1.5rem;
    text-decoration:none;
    color:#e0ddd5;
    display:flex;
    flex-direction:column;
    gap:0.6rem;
    transition:all 0.3s ease;
    position:relative;
    overflow:hidden;
  }}
  .card::before {{
    content:'';
    position:absolute;
    top:0; left:0; right:0;
    height:3px;
    background:var(--accent);
    opacity:0.6;
    transition:opacity 0.3s;
  }}
  .card:hover {{ background:#1a1a1a; border-color:var(--accent); transform:translateY(-2px); }}
  .card:hover::before {{ opacity:1; }}
  .card-cat {{
    font-size:0.7rem; text-transform:uppercase; letter-spacing:0.08em;
    color:#666;
  }}
  .card-date {{
    font-size:0.7rem; color:#444;
    position:absolute; top:1.5rem; right:1.5rem;
  }}
  .card-title {{
    font-size:1.15rem; font-weight:500; line-height:1.4;
    color:var(--accent);
    margin-top:0.25rem;
  }}
  .card-excerpt {{
    font-size:0.85rem; line-height:1.5; color:#888;
    flex-grow:1;
  }}
  .card-arrow {{
    font-size:1.2rem; color:#555;
    align-self:flex-end;
    transition:color 0.3s;
  }}
  .card:hover .card-arrow {{ color:var(--accent); }}
  .empty {{
    grid-column:1/-1; text-align:center; padding:6rem 2rem;
    color:#555; font-size:1.1rem;
  }}
  .empty em {{ color:#888; }}
  @media (max-width:600px) {{
    .header h1 {{ font-size:1.8rem; }}
    .grid {{ grid-template-columns:1fr; }}
    body {{ padding:1.5rem 1rem; }}
  }}
</style>
</head>
<body>
<div class="header">
  <div>
    <h1>collection</h1>
    <div class="sub"><span>{count}</span> artifacts</div>
  </div>
  <div class="sub">curated by AI · temperature {today_temp} · 14d cycle</div>
  <a href="about.html" style="color:#555; text-decoration:none; font-size:0.8rem; border:1px solid #222; padding:0.3rem 0.8rem; border-radius:2rem; transition:all 0.2s;" onmouseover="this.style.color='#e0ddd5';this.style.borderColor='#555'" onmouseout="this.style.color='#555';this.style.borderColor='#222'">about</a>
</div>
<div class="grid">
  {cards if cards else '<div class="empty">the collection is growing…<br><em>first artifact will appear soon</em></div>'}
</div>
<script>
  const cards = document.querySelectorAll('.card');
  cards.forEach((c,i) => {{ c.style.animationDelay = `${{i*0.05}}s`; }});
</script>
</body>
</html>"""


def main():
    safe_pr = lambda s: s.encode(sys.stdout.encoding or "utf-8", errors="replace").decode(sys.stdout.encoding or "utf-8") if isinstance(s, str) else s
    pr = lambda *a, **kw: print(*[safe_pr(x) for x in a], **kw, flush=True)
    temp = get_cycle_temp()
    pr("[agent] waking up")
    if DEEPSEEK_KEY:
        pr(f"  backend: deepseek api")
    elif OPENROUTER_KEY:
        pr(f"  backend: openrouter")
    pr(f"  temp:   {temp} (14d cycle)")
    pr()

    update_genome()
    genome = load_genome()
    if genome:
        pr(f"  genome: {genome.split('||')[0].strip()[:60]}...")
        pr()

    cat, topic, seed, fmt, humor = pick_topic()
    pr(f"  category: {cat}")
    pr(f"  topic:    {topic}")
    pr(f"  format:   {fmt}")
    pr(f"  tone:     {humor}")
    pr()

    prompt = build_prompt(cat, topic, seed, fmt, humor)
    pr("  sending prompt...")

    result = call_llm(prompt)
    if not result:
        pr("  [no content returned]")
        return

    pr("  response received")
    pr()

    title = extract_title(result)
    body = extract_body(result)

    artifact_id = datetime.now(timezone.utc).strftime("%Y%m%d_%H%M%S")
    date_str = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    filename = f"artifact_{artifact_id}.html"

    html = generate_html_artifact(cat, topic, seed, fmt, humor, title, body, artifact_id)

    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    (OUTPUT_DIR / filename).write_text(html, encoding="utf-8")
    pr(f"  [saved] artifacts/{filename}")

    existing = []
    if INDEX_PATH.exists():
        content = INDEX_PATH.read_text("utf-8")
        artifact_refs = re.findall(r'artifacts/artifact_(\d{8}_\d{6})\.html', content)
        artifact_refs.sort(reverse=True)
        for ref in artifact_refs:
            af = f"artifact_{ref}.html"
            ap = OUTPUT_DIR / af
            if ap.exists():
                html_content = ap.read_text("utf-8")
                existing.append(parse_artifact(html_content, ref))

    existing.append({
        "file": filename,
        "title": title,
        "body": body,
        "cat": cat,
        "topic": topic,
        "date": date_str,
    })

    INDEX_PATH.write_text(generate_index(existing, design=get_design(len(existing))), encoding="utf-8")
    pr(f"  [updated] index.html ({len(existing)} artifacts)")
    pr()
    try:
        pr(f"  -- {title}")
    except UnicodeEncodeError:
        pr(f"  -- [title contains non-Latin characters]")
    pr()


def parse_artifact(html, ref):
    title_m = re.search(r'<h1>(.*?)</h1>', html, re.DOTALL)
    title = title_m.group(1).strip() if title_m else "Untitled"
    body_m = re.search(r'<div class="body">(.*?)</div>', html, re.DOTALL)
    body = ""
    if body_m:
        body = re.sub(r'<[^>]+>', '', body_m.group(1)).strip()
    cat_m = re.search(r'<span>(science|art|engineering|inventions|literature|society|fashion|pop-culture)</span>', html)
    cat = cat_m.group(1) if cat_m else "unknown"
    topic_m = re.search(r'topic:\s*(.*?)\s*—', html)
    topic = topic_m.group(1).strip() if topic_m else "unknown"
    return {
        "file": f"artifact_{ref}.html",
        "title": title,
        "body": body,
        "cat": cat,
        "topic": topic,
        "date": ref[:4] + "-" + ref[4:6] + "-" + ref[6:8],
    }


if __name__ == "__main__":
    main()
