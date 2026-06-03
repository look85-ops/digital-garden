# Digital Garden

**An autonomous AI art garden. One artifact every 4 hours. No archive — only impermanence.**

A language model agent generates a unique HTML artifact every four hours, themed around a random topic from 80+ curated subjects. The previous artifact is not stored, linked, or remembered. The garden has no memory — only soil.

[**View the current artifact →**](https://look85-ops.github.io/digital-garden/)

---

## Concept

Digital Garden is a practice of making and releasing — like building a sand mandala. Each artifact appears, lives for four hours, then vanishes. The meaning is not in the object but in the gesture of its creation and the acceptance of its impermanence.

- **Temperature** follows a 14-day sine wave (0.1–1.8) with occasional random spikes
- **Prompt** is assembled from random persona, institution, format, tone, and one of 25 mutation constraints
- **Soil (`souil.json`)** — extracted themes, images, and mood from each artifact decay over time and influence future prompts
- The garden slowly evolves without storing artifacts

---

## Quick Start

### Run locally

```bash
pip install -r requirements.txt

# DeepSeek (recommended, 10M free tokens)
set DEEPSEEK_API_KEY=sk-your_key
python src/curator.py

# or OpenRouter
set OPENROUTER_API_KEY=sk-or-v1-your_key
python src/curator.py
```

### Run on GitHub Actions (autonomous)

1. Fork or clone this repo
2. Add your API key as a repository secret:
   - `DEEPSEEK_API_KEY` (from [platform.deepseek.com](https://platform.deepseek.com)) — or
   - `OPENROUTER_API_KEY` (from [openrouter.ai/keys](https://openrouter.ai/keys))
3. The agent will run every 4 hours automatically via GitHub Actions
4. Enable GitHub Pages (Settings → Pages → source: `master`, root `/`)

Artifacts accumulate in `artifacts/`, gallery at `index.html`.

---

## Project Structure

```
garden/
├── src/
│   ├── curator.py       # agent core — generation loop, prompt assembly, soil management
│   └── sources.py       # topic bank (80+ concepts), personas, institutions, formats
├── artifacts/           # generated HTML artifacts (local history)
├── index.html           # root artifact — overwritten every cycle
├── about.html           # manifesto / about page
├── souil.json           # garden state (soil, mood, memory traces)
├── requirements.txt
└── .github/workflows/garden.yml
```

---

## License

MIT — see [LICENSE](LICENSE).
