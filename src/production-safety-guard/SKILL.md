---
description: "Safety layer for working on production/live environments. TRIGGER when: user mentions 'production', 'live server', 'פרודקשן', 'שרת חי', 'שרת לייב', 'database migration', 'deploy to prod', 'customer data', 'real users', or when working with production connection strings, live API keys, or real databases. MUST trigger before any destructive operation on production systems."
---

# Production Safety Guard

## Purpose
Block dangerous operations when working on live/production systems. This skill acts as a technical safeguard that prevents accidental data loss, service disruption, or security breaches.

This follows Anthropic's practice of having a special skill activated ONLY when working on live customer servers, technically blocking the ability to delete files or overwrite databases by mistake.

## HARD RULES (Never Override Without Explicit User Confirmation)

### BLOCKED Operations in Production Context
These operations require the user to type explicit confirmation for EACH ONE:

1. **DELETE operations**
   - `DROP TABLE`, `DROP DATABASE`, `DELETE FROM` without WHERE
   - `rm -rf`, `del /s`, file deletion commands
   - Removing cloud resources (instances, buckets, queues)

2. **DESTRUCTIVE UPDATES**
   - `UPDATE` without WHERE clause
   - `TRUNCATE TABLE`
   - Overwriting config files without backup
   - Force-pushing to production branches

3. **SCHEMA CHANGES**
   - `ALTER TABLE` (can lock tables and cause downtime)
   - Migration scripts that drop columns
   - Index changes on large tables

4. **ACCESS CHANGES**
   - Modifying user permissions
   - Changing API keys or secrets
   - Opening/closing firewall rules
   - Modifying CORS settings

5. **DEPLOYMENT**
   - Direct deployment without staging verification
   - Deploying on Friday afternoon (warn user)
   - Deploying during peak hours (warn user)

## Safety Protocol

When a production context is detected:

### Step 1: Announce Safety Mode
```
PRODUCTION SAFETY MODE ACTIVE
Working on: [environment name]
All destructive operations require explicit confirmation.
```

### Step 2: Before ANY Write Operation
- State exactly what will be changed
- Show the command/query that will run
- Ask: "Confirm this operation on PRODUCTION? (yes/no)"
- Wait for explicit "yes" - not "ok", not "sure", only "yes" or "כן"

### Step 3: Recommend Safeguards
Always suggest:
- Take a backup first
- Test on staging/dev first
- Use transactions with rollback capability
- Run a dry-run if the tool supports it
- Schedule during low-traffic hours

## Detection Triggers

Automatically activate when detecting:
- Connection strings with `production`, `prod`, `live` in them
- Environment variables like `NODE_ENV=production`
- URLs pointing to production domains
- Database names containing `prod` or `live`
- Cloud resource names with production indicators
- User explicitly saying they're on production

## Emergency Rollback Checklist

If something goes wrong, present this immediately:
1. What was the last command executed?
2. Is there a backup to restore from?
3. Can the change be reverted with a transaction rollback?
4. Who should be notified?
5. Is there a runbook for this scenario?

## Key Principles

- ALWAYS err on the side of caution in production
- A 30-second confirmation delay is infinitely better than hours of disaster recovery
- If unsure whether it's production - treat it as production
- Log every production operation for audit trail
- Never store production credentials in skill files or logs
