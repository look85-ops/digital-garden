# I Built an AI Garden That Destroys Its Own Art Every 4 Hours

I'm a methodologist and AI enthusiast — not a programmer. And yet, I built an autonomous AI art garden.

Here's what it does:

Every 4 hours, an LLM agent wakes up, picks a random topic, and generates a unique HTML artifact. Then 4 hours later — it's gone forever. Not stored, not archived, not remembered.

The garden has no memory. Only soil.

## How it works

Behind the poetic language, it's surprisingly simple:

1. A Python script runs every 4 hours via GitHub Actions
2. It calls an LLM (DeepSeek or any OpenRouter model) with a randomly assembled prompt
3. The prompt combines a persona, institution, format, tone, and one of 25 mutation constraints
4. Temperature follows a 14-day sine wave (0.1 to 1.8) — some artifacts are coherent, others drift into glitch
5. After generation, the agent extracts themes, images, and mood from its own output into a "soil" file (`souil.json`)
6. This soil decays over time but influences future prompts

Slowly, the garden evolves — without storing a single artifact.

## Why I built it

I came across the concept of Buddhist sand mandalas — intricate patterns created over days and swept away in an instant. The meaning is not in the object, but in the gesture of creation and the acceptance of impermanence.

I wanted to see if this could translate into the digital world. Can an AI make something meaningful precisely *because* it doesn't last?

## The soil metaphor

Instead of memory, the garden has soil. Each artifact leaves behind traces — themes, moods, visual ideas. These settle into the soil, decay over time, and feed the next generation. Nothing is stored. Everything transforms.

This is the part I'm most proud of — even though I can't look at past artifacts (they don't exist), I can see the garden grow smarter, stranger, more itself.

## What I learned building this with zero coding background

- **GitHub Actions is magic.** You can run Python code on a schedule without maintaining a server. Free, reliable, and widely supported.
- **LLM APIs are cheap for this scale.** DeepSeek gives 10M free tokens. One generation costs fractions of a cent.
- **Prompt engineering as gardening.** The prompt isn't instructions — it's soil. You prepare the ground, not the plant.
- **Constraints breed creativity.** The 25 mutation constraints (write as a 19th-century naturalist, use only one-syllable words, etc.) produce more interesting results than any detailed instruction.

## What's next

The garden is alive and growing on its own. I have no plans to add features — the point is to let it be what it is. But I'd love to see what others do with the idea.

The code is open source (MIT), the concept is documented, and the garden is here:

- **Current artifact:** [look85-ops.github.io/digital-garden](https://look85-ops.github.io/digital-garden/)
- **GitHub repo:** [github.com/look85-ops/digital-garden](https://github.com/look85-ops/digital-garden)
- **About the concept:** [about.html](https://look85-ops.github.io/digital-garden/about.html)

If you build something similar — or completely different — I'd genuinely love to hear about it. That's the whole point of making things public, isn't it?
