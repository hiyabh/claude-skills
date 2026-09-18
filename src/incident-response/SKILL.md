---
description: "On-call / production incident triage: correlate logs + recent deploys + config changes into a most-likely-cause, read a console screenshot and give exact fix commands, or write+run a diagnostic query over metrics/logs and interpret it. TRIGGER when the user says 'API latency doubled in the last hour, check the logs, recent deploys, and config changes, then tell me the most likely cause', 'here is a screenshot of the AWS console, walk me through why the RDS instance is failing and give me the exact commands to fix it', 'show me all 5xx events for /payments over the last 24h, write the query, run it, and tell me what stands out', or reports an ongoing outage/latency spike/error surge. Hebrew: 'תקרית פרודקשן', 'ה-latency קפץ, תבדוק לוגים ודיפלויים', 'למה ה-RDS נופל', 'תכתוב שאילתת אבחון על הלוגים', 'טריאז׳ לתקרית'. For a single reproducible bug (not a live incident), use a root-cause debugging skill like debug instead, if you have one."
---

# Incident Response — Triage · Console-Screenshot · Diagnostic Query

## Purpose
Fast, structured handling of **live production incidents** — where something is
degrading *now* and you need the most-likely cause and the next action, not a leisurely
root-cause hunt. Three entry points: multi-signal **triage**, a **console screenshot**
walkthrough, and a **diagnostic query** over logs/metrics.

**Mindset:** mitigate first, diagnose in parallel, be explicit about confidence.
State the leading hypothesis *with evidence and a confidence level*; never present a
guess as a confirmed cause.

**Language:** explanations in Hebrew; commands, queries, and code in English.

---

## Mode 1 — Multi-signal triage
Trigger: "API latency doubled in the last hour. check the logs, recent deploys, and config changes, then tell me the most likely cause".

Correlate the three classic incident signals, oldest-suspect-first:

1. **Timeline** — pin *when* the degradation started as precisely as possible. Every
   other signal is judged against this timestamp.
2. **Recent deploys / releases** — what shipped just before the start time?
   `git log --since`, deploy history, release tags. A change landing minutes before
   the regression is the prime suspect.
3. **Config / infra changes** — feature flags, env vars, scaling changes, secret
   rotation, dependency/DB migrations, expiring certs/quotas.
4. **Logs & metrics** — error-rate and latency curves around the start time; new
   error signatures, timeouts, connection-pool exhaustion, upstream 5xx, GC/CPU/mem
   saturation.
5. **Correlate → rank causes** — produce a short ranked list: each candidate with the
   evidence for/against and a confidence %. Lead with the single most-likely cause.
6. **Recommend the next action** — mitigation (rollback the suspect deploy, flip the
   flag back, scale up) *and* the confirming check. Call out if a rollback is the
   safest immediate move even before full diagnosis.

---

## Mode 2 — Console screenshot → diagnosis + exact commands
Trigger: "here is a screenshot of the AWS console. walk me through why the RDS instance is failing and give me the exact commands to fix it".

1. **Read the screenshot carefully** — extract every relevant fact: resource
   ids/names, region, status/health, metric values, alarm text, error messages,
   timestamps. Quote the specific numbers you're reasoning from.
2. **Diagnose** — connect what's shown to a cause (e.g. storage-full, connection
   limit hit, failover in progress, CPU credit exhaustion, blocked security group).
   Explain the chain of reasoning so the user can follow it.
3. **Give exact, copy-paste commands** — the actual CLI (`aws rds ...`, `kubectl ...`,
   `gcloud ...`) with the real identifiers from the screenshot filled in, in the order
   to run them. Mark any **destructive/irreversible** step clearly and note what it
   affects before the user runs it.
4. **State verification** — the command/metric that confirms the fix worked, and a
   safer alternative if the primary action carries risk.
5. Note anything you **cannot** see in the screenshot that would change the diagnosis,
   so the user can check it.

---

## Mode 3 — Diagnostic query over logs/metrics
Trigger: "show me all 5xx events for /payments over the last 24h. write the query, run it, and tell me what stands out".

1. **Identify the data source & language** — CloudWatch Logs Insights, Loki/LogQL,
   Elasticsearch/OpenSearch DSL or KQL, Datadog, BigQuery/SQL, Prometheus/PromQL,
   Splunk SPL, `grep`/`jq` over raw logs. Confirm which the project uses; don't assume.
2. **Write the query** precisely to the ask — right filters (path, status class),
   time window, and a useful aggregation (count by status/route/time-bucket, p50/p95/p99
   latency, group by error signature or user/tenant) rather than a raw dump.
3. **Run it** if the tooling/credentials are available; otherwise hand the user the
   exact runnable query and ask them to paste results back.
4. **Interpret — "what stands out"** is the deliverable: spikes, concentrations (one
   route/tenant/version dominating), correlation with a deploy time, new error types.
   Don't just restate the numbers — say what they *mean* and the likely cause.
5. Suggest the **follow-up query** that would confirm the leading hypothesis.

---

## Rules
- Separate **fact** (from logs/screenshot/query) from **inference** (your hypothesis),
  and attach a confidence level to conclusions.
- Prefer reversible mitigation (rollback, flag flip, scale) over risky live surgery.
- Any destructive command gets a clear warning + what it affects, before it's run.
- If evidence is thin, say the most-likely cause *and* what to gather to confirm —
  don't fabricate certainty.
- Read-only diagnosis is autonomous; state-changing prod actions on infra outside the
  project's scope get flagged for the user before running.
