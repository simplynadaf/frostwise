# FrostWise YouTube Metadata

## Title (front-loaded keyword + payoff + freshness, under 70 chars)
Offline AI Frost Predictor: TabPFN + Gemma, no internet (2026)

A/B alternative (first-person hook):
I Built an Offline AI That Predicts Frost, No Internet, No API (2026)

## Description

Your last spring frost date decides whether your tomatoes live. Every tool that gives
you that number lives on a server, and the one place you need it, the allotment with no
signal, is the one place it will not load. So I built FrostWise: it predicts your last
frost and tells you what to plant, entirely on your laptop, with the Wi-Fi off.

Two open-weight models do the work. TabPFN-v2, a tabular foundation model, forecasts the
last-frost day in one CPU pass with an honest range. Gemma 3, running locally through
Ollama, turns that date into plain-language planting advice. No API key, no account,
nothing leaves your machine. $0 to run.

In this video I run it across three very different climates, Miami, Chicago, and Fargo,
and the frost date genuinely changes with the climate because the model is predicting,
not looking up a table.

Built for the Hacktoberfest Open-Source AI Challenge 2026, Week 1: Touch Grass.

Code (MIT, clone and run): https://github.com/simplynadaf/frostwise

Chapters:
0:00  The problem: a frost date you cannot load offline
0:20  FrostWise: the one honest number
0:40  Forecast 1, Miami, effectively frost-free
1:05  Forecast 2, Chicago, a real May frost
1:30  Forecast 3, Fargo, frost into summer
2:00  How it works: TabPFN-v2 + Gemma 3, both local
2:30  Why open innovation matters: offline, private, free, swappable

Tools used:
- TabPFN-v2 (open-weight tabular foundation model): https://github.com/PriorLabs/TabPFN
- Gemma 3 (open-weight LLM): https://ai.google.dev/gemma
- Ollama (local model runner): https://ollama.com

Follow me:
Portfolio: https://sarvarnadaf.com
LinkedIn: https://www.linkedin.com/in/sarvar04/
Dev.to: https://dev.to/sarvar_04
GitHub: https://github.com/simplynadaf
X: https://x.com/SarvarN_04

#OpenSourceAI #Gemma #TabPFN #OfflineAI #Hacktoberfest

## Tags (YouTube, comma-separated)
offline AI, open weight model, Gemma 3, TabPFN, local LLM, Ollama, run AI offline,
frost date, last spring frost, when to plant tomatoes, garden planner, hacktoberfest 2026,
open source AI, no internet AI, on-device AI, python fastapi, tabular foundation model,
local AI tutorial, AI without API, private AI

## Thumbnail text (max 3 words, high contrast)
"FROST, OFFLINE"  (or)  "NO INTERNET AI"
Pair with the FrostWise cover art (ice->amber on near-black). Keep text left, result
date visible right.

## Pinned comment (first-hour seeding)
Code is MIT and runs fully offline: https://github.com/simplynadaf/frostwise
The surprising part was TabPFN, it predicts from the data as context in one CPU pass,
no training loop at all. Ask me anything about wiring two open-weight models together.
