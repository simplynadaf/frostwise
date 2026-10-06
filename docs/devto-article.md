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

I built it for a specific person: my friend who keeps a plot at a community garden on a hill where the signal drops to nothing. Every spring she texts me "is it safe to plant yet" because she cannot load a frost-date site from the plot itself. FrostWise is the answer she can keep on her own phone and open with no bars.

## What I Built

FrostWise answers one question honestly: when does the cold let go where you are, and what should you do about it.

You pick a location (or type your own climate numbers), choose a crop, and it returns three things:

- **A date.** Your predicted last spring frost, with an honest range, not a fake single-day promise.
- **The advice.** Plain language for your exact crop. Wait until after the frost for tender things like tomato and basil. Sow a few weeks early for hardy things like peas and kale.
- **A reason to trust it.** The number comes from a model you can inspect and retrain, and the range tells you the risk.

It gets people off the screen in the most literal way. The screen is the ten seconds you spend before you walk outside and put a seed in the ground. The whole point is to make that part short.

Who it is for: anyone with a patch of soil and a spotty signal. Community plots, hillside allotments, a herb bed at a trail-head cabin. The places where a cloud API is useless are exactly where people garden.

![FrostWise homepage: the headline Know when the frost lets go over a soft midnight-galaxy starfield, with Plan my garden and How it works buttons](https://raw.githubusercontent.com/simplynadaf/frostwise/main/docs/screenshots/homepage.png)

## Demo

**Try it now:** [d2damz5gbd2rbh.cloudfront.net](https://d2damz5gbd2rbh.cloudfront.net)

That hosted link is a static site (S3 plus CloudFront, near zero cost) that serves real, pre-computed TabPFN-v2 and Gemma results for the preset cities, so you can click through actual model output. The live models themselves run on your own machine. For custom climate input, fully offline, clone the repo and run `python run.py`.

Here is the full flow across three very different climates: Miami (effectively frost-free), Chicago (a real May frost), and Fargo (frost that lingers into summer). Same code, three honest answers.

Here is what one answer looks like: a predicted last frost, the honest range around it, and planting advice written locally by Gemma for the exact crop.

![FrostWise result for Chicago: a predicted last spring frost of May 20, likely between May 15 and May 26, with an amber advice card for tomato written locally by Gemma](https://raw.githubusercontent.com/simplynadaf/frostwise/main/docs/screenshots/02-result.png)

And here is the full walkthrough across all three climates:

{% embed https://www.youtube.com/watch?v=VIDEO_ID %}

The frost date animates in, then a local Gemma model writes the planting advice live. Nothing in that video calls out to the internet.

## Code

{% embed https://github.com/simplynadaf/frostwise %}

Clone it, `python run.py`, and it is on `localhost:8077`. The first forecast caches the model weights once; after that you can pull the network cable and it still works.

## How I Built It

The whole thing is two open-weight models doing one honest job each, locally.

![FrostWise architecture: the browser sends a location and crop to a local server; TabPFN-v2 forecasts the last-frost day on CPU; Gemma 3 in local Ollama turns that date into advice; a deterministic rule covers the offline fallback; nothing leaves the machine](https://raw.githubusercontent.com/simplynadaf/frostwise/main/docs/architecture.png)

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

One honest note on the data. The 400-row dataset in the repo is grounded but synthetic: I generated it from documented last-frost norms for 20 real United States locations, so the relationships are real, but it is a teaching dataset, not a live weather feed. That is a feature, not a dodge. Point `fit` at your own weather-station CSV and the same model forecasts your actual backyard. The open stack is what makes that swap a one-line change instead of a support ticket.

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

## What the Data Actually Says

Once the model was fitting cleanly, I did the thing a forecast tool rarely does: I asked it what it had learned. I swept each feature across its real 10th-to-90th-percentile range and measured how many days the predicted last frost moved. Every number here is reproducible with `python scripts/analyze.py`.

The result surprised me.

| What changes | Realistic swing moves the last frost by |
|---|---|
| February mean temperature | **50 days** |
| March mean temperature | 32 days |
| Coldest winter night | 27 days |
| Latitude | 24 days |
| Elevation | 12 days |
| El Nino / La Nina (ENSO) | 10 days |

Gardeners obsess over latitude. "I'm up north, so I plant late." But in this data **a cold-versus-mild February swings your last frost more than twice as hard as how far north you are.** The month most people ignore, the dead one before anything grows, is the strongest single tell. Latitude is a slow backdrop; February is the actual signal.

Two more things fell out of the sweep:

**The El Nino signal is not shared equally.** I expected it to shift everyone. It barely touches the cold north: at a Fargo-like station the La Nina to El Nino swing was about 0.1 days, basically nothing. At a Houston-like station it was 8 days. The climate oscillation you hear about on the news moves the mild south and leaves the frozen north alone.

**Elevation is real but modest.** At 40 degrees north, climbing from sea level to 1600 meters (think Denver) pushed the last frost about 13 days later. Real, worth knowing, but a quarter of February's pull.

None of this is on a frost-date website, because those sites look up a static average by ZIP code. They cannot tell you *what moves your number*. A model you can interrogate can. That is the difference between a lookup table and something that has actually learned the shape of the problem.

## Why Does Open Innovation Matter?

I kept asking: would a closed, hosted model have made this better? Every time the answer was no.

**Offline is the entire premise.** The place you most need a frost date is the plot with no signal. A closed API cannot reach it. Open weights on your own disk work there. This is not a nice-to-have for FrostWise, it is the reason it exists.

**Your location is yours.** "Where do you garden" is personal data. With open weights there is no server to send it to, no account to create, nothing logged. A hosted model turns your garden into someone else's row in a database.

**It costs nothing.** Open weights mean zero per-request fees. A community garden can run it a thousand times and the bill is still zero. A metered API would make the same tool expensive at exactly the moment you want to share it.

**You own the brain.** You can read how TabPFN predicts, retrain it on your own weather-station records, and swap Gemma for any open-weight model Ollama can run. Nothing is locked to a vendor you cannot inspect. If a forecast looks wrong, it is my data and my model to fix, not a prompt I have to beg a black box to honor.

A closed API would have been faster to wire up for about an hour, and then wrong forever for the one person standing in a field with no signal.

## My Agent Session

I built FrostWise with an AI coding agent, and I kept it honest the same way the app keeps its forecasts honest: the agent proposed, I verified every claim against a real run before it shipped.

The useful parts of that session, in order:

1. **Research before code.** The agent read the challenge rules, the official template, and two past winning posts, then wrote the "why open beats closed" argument from the prompt's own bullets instead of guessing.
2. **A feasibility spike first.** Before a line of product code, it proved both models actually run on a plain CPU box: TabPFN-v2 predicting a frost date in about 3 seconds, and `gemma3:1b` answering a planting question offline. Only then did we build.
3. **Catching my own overclaim.** During review the agent flagged that the dataset is synthetic and made me say so in this post, rather than let "matches real climate norms" imply a live feed. That note is in "How I Built It" now because the agent pushed back.
4. **Real bugs, found by running it.** A static-path mistake made the UI load blank; a weak `gemma3:270m` ignored the frost date. Both were caught by actually running the thing, not by reading the diff.

The through-line: the agent is fast, but nothing shipped until a real run backed it up. That is the same contract as the product. The model proposes, the evidence decides.

## Did It Touch Grass?

I ran it for my friend's plot before she planted. FrostWise put her last frost in early May; she waited, set her tomatoes out the week after, and did not lose a single seedling to a late cold night. The screen part took about ten seconds. The rest of the afternoon she was in the dirt. That is the whole idea: the tool gets out of the way and sends you outside.

## Prize Categories

- **Best Use of Gemma.** Gemma 3 runs locally via Ollama and writes every piece of planting advice. It is the whole language layer, offline, swappable, told the date so it cannot invent one.
- **Best Use of TabPFN.** TabPFN-v2 (open weights) is the forecaster. It predicts the last-frost day-of-year from climate features in one CPU pass, with a calibrated range, no training required. The date on screen is always its number.

---

*Follow me for more on AWS architecture, DevOps, and AI Infrastructure:*
*[Portfolio](https://sarvarnadaf.com) | [LinkedIn](https://www.linkedin.com/in/sarvar04/) | [Dev.to](https://dev.to/sarvar_04) | [YouTube](https://www.youtube.com/@sarvar-nadaf) | [Email](mailto:simplynadaf@gmail.com) | [AWS Builder Center](https://builder.aws.com/community/@sarvar) | [X](https://x.com/SarvarN_04)*
