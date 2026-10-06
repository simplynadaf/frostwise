---
title: I built an offline AI that knows your last frost date, no internet, no API
published: false
description: An open-weight tabular model forecasts your last spring frost and a local Gemma writes the planting advice. Fully offline, no account, $0 to run.
tags: devchallenge, hf26challenge, ai, opensource
cover_image:
canonical_url:
---

*This is a submission for the [Hacktoberfest Open-Source AI Challenge Week 1: Touch Grass](https://dev.to/challenges/hacktoberfest-week1-2026-10-05)*

The most useful number in a vegetable garden is the last spring frost date. Get it wrong by a week and one cold night turns your tomato seedlings to mush.

Every tool that gives you that number has the same flaw. It lives on a server. You look it up on your phone, standing in the one corner of the allotment that gets a bar of signal, hoping the page loads before the rain starts.

So I built **FrostWise**: it predicts your last frost and tells you what to plant, and it does the whole thing on your laptop with the Wi-Fi off. Two open-weight models, no API key, no account, nothing leaves the machine.

## What I Built

FrostWise answers one question honestly: when does the cold let go where you are, and what should you do about it.

You pick a location (or type your own climate numbers), choose a crop, and it returns three things:

- **A date.** Your predicted last spring frost, with an honest range, not a fake single-day promise.
- **The advice.** Plain language for your exact crop. Wait until after the frost for tender things like tomato and basil. Sow a few weeks early for hardy things like peas and kale.
- **A reason to trust it.** The number comes from a model you can inspect and retrain, and the range tells you the risk.

It gets people off the screen in the most literal way. The screen is the ten seconds you spend before you walk outside and put a seed in the ground. The whole point is to make that part short.

Who it is for: anyone with a patch of soil and a spotty signal. Community plots, hillside allotments, a herb bed at a trail-head cabin. The places where a cloud API is useless are exactly where people garden.

## Demo

Here is the full flow across three very different climates: Miami (effectively frost-free), Chicago (a real May frost), and Fargo (frost that lingers into summer). Same code, three honest answers.

{% embed https://www.youtube.com/watch?v=VIDEO_ID %}

The frost date animates in, then a local Gemma model writes the planting advice live. Nothing in that video calls out to the internet.

## Code

{% embed https://github.com/simplynadaf/frostwise %}

Clone it, `python run.py`, and it is on `localhost:8077`. The first forecast caches the model weights once; after that you can pull the network cable and it still works.

## How I Built It

The whole thing is two open-weight models doing one honest job each, locally.

### The forecast: TabPFN-v2

[TabPFN](https://github.com/PriorLabs/TabPFN) is a tabular foundation model from Prior Labs. It is the strange and wonderful part. Instead of training a model on my frost data, I hand it the data as context and it predicts in a single forward pass. No training loop, no hyperparameter search, no GPU.

```python
from tabpfn import TabPFNRegressor
from tabpfn.constants import ModelVersion

reg = TabPFNRegressor.create_default_for_version(ModelVersion.V2, device="cpu")
reg.fit(X_train, y_train)          # "fit" is just loading the context
pred = reg.predict(X_test)         # one forward pass, a few seconds on CPU
```

I use the **v2 weights on purpose**. The default TabPFN-3.5 weights are non-commercial and want a browser login. The v2 weights are the Prior Labs License (Apache-2.0 plus attribution), so the whole stack stays genuinely open and runs headless. For an "open innovation" project that distinction is the point, not a footnote.

The features are the things that actually drive frost timing: latitude, elevation, the February and March mean temperatures, the coldest winter night, and an ENSO index for that winter. The target is the last-frost day-of-year. On a plain 8-core CPU it predicts in about 3 seconds, and I read the 10 to 90 percent quantiles for the range.

For a Chicago-like input it lands on May 20, range May 15 to 26. For Fargo it says June 19. Those match the real climate norms, which told me the model was learning the physics and not memorizing noise.

### The advice: Gemma 3, local via Ollama

The date is a number. A gardener wants a sentence. So a local [Gemma 3](https://ai.google.dev/gemma) model, served by [Ollama](https://ollama.com), turns the forecast plus the crop into guidance.

```python
payload = {
    "model": "gemma3:1b",
    "prompt": f"{SYSTEM}\n\nLocation: {station}. Last frost: {date}. Plant: {crop}.",
    "stream": False,
    "options": {"temperature": 0.3, "num_predict": 160},
}
```

I started with `gemma3:270m` because it is tiny. It was too tiny: it ignored the frost date and chatted. `gemma3:1b` (about 815 MB) follows the instruction cleanly and still runs comfortably on CPU. One honest line in the design: the model is told the date, it never invents one. The number is always TabPFN's.

### The fallback: when the model is not there

A tool that promises "works offline" has to survive the model being unreachable too. If Ollama is down, a deterministic tender-vs-hardy rule writes a correct tip from the same date. The app never shows a frightened spinner that never ends.

```python
def advise(plant, forecast):
    try:
        return {"text": call_gemma(plant, forecast), "source": "gemma"}
    except Exception:
        return {"text": rule_based(plant, forecast), "source": "offline-fallback"}
```

### The shell

A small FastAPI server wires the two models together and serves a single-page UI (Three.js for a quiet night-sky background, no build step). The server only ever talks to `localhost`. There is no outbound call anywhere in the request path once the weights are cached.

## Why Does Open Innovation Matter?

I kept asking: would a closed, hosted model have made this better? Every time the answer was no.

**Offline is the entire premise.** The place you most need a frost date is the plot with no signal. A closed API cannot reach it. Open weights on your own disk work there. This is not a nice-to-have for FrostWise, it is the reason it exists.

**Your location is yours.** "Where do you garden" is personal data. With open weights there is no server to send it to, no account to create, nothing logged. A hosted model turns your garden into someone else's row in a database.

**It costs nothing.** Open weights mean zero per-request fees. A community garden can run it a thousand times and the bill is still zero. A metered API would make the same tool expensive at exactly the moment you want to share it.

**You own the brain.** You can read how TabPFN predicts, retrain it on your own weather-station records, and swap Gemma for any open-weight model Ollama can run. Nothing is locked to a vendor you cannot inspect. If a forecast looks wrong, it is my data and my model to fix, not a prompt I have to beg a black box to honor.

A closed API would have been faster to wire up for about an hour, and then wrong forever for the one person standing in a field with no signal.

## Prize Categories

- **Best Use of Gemma.** Gemma 3 runs locally via Ollama and writes every piece of planting advice. It is the whole language layer, offline, swappable, told the date so it cannot invent one.
- **Best Use of TabPFN.** TabPFN-v2 (open weights) is the forecaster. It predicts the last-frost day-of-year from climate features in one CPU pass, with a calibrated range, no training required. The date on screen is always its number.

---

*Follow me for more on AWS architecture, DevOps, and AI Infrastructure:*
*[Portfolio](https://sarvarnadaf.com) | [LinkedIn](https://www.linkedin.com/in/sarvar04/) | [Dev.to](https://dev.to/sarvar_04) | [YouTube](https://www.youtube.com/@sarvar-nadaf) | [Email](mailto:simplynadaf@gmail.com) | [AWS Builder Center](https://builder.aws.com/community/@sarvar) | [X](https://x.com/SarvarN_04)*
