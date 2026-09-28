# Model Router

Send each question to the cheapest model that can answer it well.

Most questions an LLM application receives are easy. Sending all of them to a large, expensive model wastes money; sending all of them to a small model hurts quality. Model Router looks at each incoming question and decides which model should handle it, then measures whether that decision actually paid off.

The core claim this project has to prove with numbers:

> "Compared to always using the strong model, routing cut cost by **X%** while losing only **Y%** in quality."

---

## How it works

```
question ──▶ router ──┬──▶ small model  (free, fast, weaker)
                      │
                      └──▶ strong model (free, slower, stronger)
                                │
                                ▼
                     answer + cost + latency log
```

**Free models only.** This project runs entirely on free models. Cost is therefore
measured in two ways:

- **Real cost:** latency and compute (and free-tier quota, if an API is used).
- **Shadow cost:** what the same tokens would cost at a public paid API's list price.
  This shows the savings the router would bring to a production system that does pay.

1. A question comes in.
2. The router decides: is this easy enough for the small model?
3. The chosen model answers.
4. Every decision is logged with its cost and latency, so it can be evaluated later.

## How we measure it

A router is only as good as the evidence behind it. Every version is evaluated on a fixed test set against three baselines:

| Strategy | What it shows |
|---|---|
| Always small model | Lowest cost, quality floor |
| Always strong model | Highest cost, quality ceiling |
| **Router** | Where we land between the two |

Metrics:

- **Quality:** share of questions answered correctly, judged against reference answers (exact match where possible, LLM-as-judge otherwise).
- **Cost:** shadow cost of answering the test set (tokens × public list price).
- **Latency:** average response time.
- **Routing accuracy:** how often the router sent a question to the model that actually needed it.

---

## Roadmap

One repository, growing version by version. Every version ends with something that works on its own and can be tagged (`git tag v0.1`).

### v0.1 — Baseline and evaluation
Two models, a test set of 100–200 mixed easy/hard questions, a rule-based router (length, keywords), and the cost/quality table above.

**Done when:** the three-row comparison table exists and is filled with real numbers.

### v0.2 — Smarter routing
An embedding-based or small-classifier router, compared against the rule-based one on the same test set.

**Done when:** the table has a fourth row, and we know with numbers whether the smarter router beats the simple one.

### v0.3 — Gateway
Expose the router as an OpenAI-compatible API, so any app can use it as if it were a single model. Add fallback (if one model fails, use the other) and response caching.

**Done when:** an existing OpenAI client can point at the router and work unchanged.

### v0.4 — Monitoring
A dashboard showing which questions went where, what they cost and how long they took.

**Done when:** routing decisions and costs are visible without reading logs.

### v1.0 — Production
Docker packaging, rate limiting, prompt-injection safeguards, deployment.

**Done when:** `docker compose up` brings the whole system up.

---

## Repository structure

Folders are added only when their version starts.

```
model-router/
├── models/      # v0.1  clients for each model
├── eval/        # v0.1  test set + evaluation scripts
├── routing/     # v0.1  rule-based router
│                # v0.2  + embedding-based router
├── gateway/     # v0.3  OpenAI-compatible API, fallback, cache
├── dashboard/   # v0.4  monitoring
└── docker/      # v1.0  packaging and deployment
```

## Stack

- **Python 3.11+**
- **Small model:** [Ollama](https://ollama.com) running `llama3.2:3b` locally.
- **Strong model:** free as well. Either a larger local model via Ollama, or a free-tier API (decided in v0.1).

## Status

🚧 **v0.1 in progress.** Next step: connect to the local Ollama model from Python.

## Open decisions

- Which strong model: larger local model or free-tier API? (v0.1)
- Which public API's price list is used for shadow cost? (v0.1)
- Where does the test set come from: hand-written, public benchmark, or both? (v0.1)
- How is quality judged for open-ended answers? (v0.1)