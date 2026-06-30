<div align="center">

# 🧠 AI Employee Console

### The company brain that makes every AI employee smarter

<br>

[![Python](https://img.shields.io/badge/Python-3.9+-3776AB?style=flat-square&logo=python&logoColor=white)](https://python.org)
[![Flask](https://img.shields.io/badge/Flask-Lightweight-000000?style=flat-square&logo=flask)](https://flask.palletsprojects.com)
[![License](https://img.shields.io/badge/License-MIT-2563EB?style=flat-square)](./LICENSE)

<br>

*When a human resolves an ambiguity once, the system never asks again.*
*That's the thesis. This demo performs it live.*

<br>

</div>

---

> **The moat in AI employees isn't any single agent.**
> It's the compounding knowledge layer underneath — the *company brain* — that makes every agent smarter with every deployment.

Built as a working product demo for [Zamp](https://zamp.ai)'s Product Manager role.

<br>

## ⚡ The Demo in 60 Seconds

<table>
<tr>
<td width="60" align="center"><h3>1</h3></td>
<td>
<b>Priya Sharma joins as a Sales Engineer in Dubai.</b><br>
The AI employee extracts her details, builds a cross-functional plan across IT, HR, and Finance — then stops. "Sales Engineer" maps to both Sales and Engineering. The agent refuses to guess.
</td>
</tr>
<tr>
<td align="center"><h3>2</h3></td>
<td>
<b>The admin resolves it: Sales Engineer = Sales.</b><br>
One click. The decision cascades: IT access groups, finance tier, reporting line — all update. The resolution animates into the Company Brain as a persistent, queryable rule.
</td>
</tr>
<tr>
<td align="center"><h3>3</h3></td>
<td>
<b>Omar Reyes joins as a Sales Engineer in Dubai.</b><br>
This time, no ambiguity. The Company Brain fires. Omar's plan resolves automatically — same IT groups, same finance tier, same reporting line. No human needed.
</td>
</tr>
</table>

**Corrected once, never asks again.**

<br>

## 🚀 Run

```bash
pip install flask
python3 app.py
```

Open **[http://localhost:8080](http://localhost:8080)**. No database, no Docker, no build step.

<br>

## 🏗 Architecture

```
├── app.py                  Flask server · 6 endpoints
├── agent_engine.py         Deterministic onboarding logic + ambiguity map
├── brain_store.py          JSON-persisted company brain · search & query
├── gpt_client.py           Templated LLM responses · preset chips are instant
│
├── static/
│   ├── index.html          Two-tab product shell
│   ├── styles.css          Linear/Vercel-inspired design system
│   └── app.js              Staggered beats · fork viz · constellation brain
│
├── data/
│   └── company_brain.json  Persistent decisions · auto-created · gitignored
│
└── research/
    ├── README.md                             Methodology & findings
    ├── research_summary.html                 Visual summary · 629 complaints
    ├── clustered_painpoints.json             11 pain clusters
    └── filtered_records_and_seed_clusters.json   Raw extracted records
```

<br>

## 🎯 Design Decisions

| Decision | Why |
|:---|:---|
| **Ambiguity escalation is deterministic** | The backend checks a role-department map. The LLM provides language, not control flow. The hero moment never depends on model mood. |
| **Brain is a real persistence layer** | Decisions persist to JSON, survive restarts, and return grounded answers. Reset exists for clean recording takes. |
| **Preset chips are templated** | Three demo scenarios return instant, deterministic responses. Free-text falls through to the LLM. On camera, the product never waits. |
| **Only two animations are dramatic** | Knowledge created (fly-into-brain) and knowledge applied (rule pulse). Everything else stays calm so these moments land. |

<br>

## 🔬 Research

Before building, I scraped **629 public complaints** from Reddit and Trustpilot to map where Zamp's product has gaps.

**The finding:** every major ops pain point — AP, reconciliation, onboarding, vendor management — is already claimed. There is no process-level white space.

That's what led to the company brain thesis. The full research is in [`/research`](./research/).

<br>

## 🧩 Full-Stack Workbench

This repo is the focused thesis demo. The expanded full-stack product version lives here:

**[Company Brain Workbench](https://github.com/Karunasagar12/company-brain-workbench)** — approvals, audit trail, learned rules, and the Priya → Omar guided workflow in a production-style app shell.

<br>

## 💡 The Company Brain Thesis

Every time a human resolves an ambiguity an AI employee couldn't handle, that judgment becomes structured memory: what happened, what context mattered, what was decided, and when it should apply again.

Over time, this layer compounds. Each deployment makes the next one faster. Each correction eliminates a future escalation.

> **The moat isn't one agent — it's the accumulated decision intelligence of the organization.**

<br>

---

<div align="center">

Built by **[Karuna Sagar](https://github.com/Karunasagar12)**

Founder, Plato Tech — clinical & document AI agents shipped to hospitals

</div>
