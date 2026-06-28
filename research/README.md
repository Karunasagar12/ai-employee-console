# Ops Pain-Signal Research

## What this is

629 public complaints scraped from 6 subreddits (r/Accounting, r/Bookkeeping, r/FPandA, r/msp, r/sysadmin, r/automation) and Trustpilot reviews of 4 enterprise automation/procurement tools (SAP Ariba, Coupa, BILL, ServiceNow). Clustered into 11 named pain categories using GPT-5.5.

## Key finding

Every major ops pain point — AP, reconciliation, onboarding, vendor management, compliance — is already claimed by Zamp's product. No process-level white space exists. The opportunity is the compounding knowledge layer beneath the agents, not another agent.

## Files

- `research_summary.html` — cinematic visual summary (open in browser)
- `clustered_painpoints.json` — 11 clusters with names, frequencies, departments, evidence
- `filtered_records_and_seed_clusters.json` — 629 filtered records with extracted pain points

## Methodology

1. Scraped public complaints via Apify (Reddit scraper + Trustpilot scraper)
2. Filtered by task-pain keywords (manual, automate, tedious, hours, etc.)
3. Extracted structured pain points via GPT-5.5
4. Clustered into 11 categories by theme and department
5. Mapped clusters against Zamp's published product capabilities

## Source details

Distinct source targets represented in the filtered records: 10.

- Reddit: Accounting, Bookkeeping, FPandA, msp, sysadmin, automation
- Trustpilot: SAP Ariba, Coupa, BILL, ServiceNow
