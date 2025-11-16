# Escalation Procedures

Complete guide for escalating support issues.

## When to Escalate

### Automatic Escalation Triggers

**Escalate to Tier 3 (Engineering):**
- P0/P1 incidents
- System bugs
- Performance degradation (>500ms P95)
- Data corruption
- Security issues
- Unknown root cause after 2 hours investigation

**Escalate to Tier 4 (Vendor):**
- Infrastructure outages (AWS, GCP)
- Third-party service failures
- Vendor-specific issues

## Escalation Path

```
Tier 1 (Self-Service)
    ↓ (if unresolved)
Tier 2 (Help Desk)
    ↓ (if P0/P1 or engineering needed)
Tier 3 (Engineering On-Call)
    ↓ (if vendor-related)
Tier 4 (Vendor Support)
```

## Who to Escalate To

### Tier 2 → Tier 3 (Engineering)

**Primary On-Call Engineer:**
- Check PagerDuty rotation schedule
- Current on-call: Available 24/7
- Backup: Secondary on-call

**Engineering Lead:**
- For P0 issues unresolved after 1 hour
- For architectural decisions
- For production deployment approval

### Tier 3 → Tier 4 (Vendor)

**AWS Support:**
- Infrastructure issues
- Service degradation
- Billing problems

**GCP Support:**
- Similar to AWS

**Third-Party Vendors:**
- SendGrid: Email delivery issues
- MinIO: Storage issues
- OpenSearch: Search issues

## How to Escalate

### Email Escalation Template

**Subject**: `[ESCALATE] P1: Issue Description - Ticket #12345`

**Body**:
```
Priority: P1 (High)
Ticket: #12345
Customer: customer@example.com
Issue: Brief description

Details:
- Error message: ...
- Steps to reproduce: ...
- Expected vs. actual: ...
- Logs: [attached]
- Screenshots: [attached]

Tier 2 Actions Taken:
- Attempted: ...
- Results: ...

Escalation Reason:
- Requires engineering investigation
- Cannot resolve with standard procedures
- Impact: Multiple users affected
```

### PagerDuty Escalation

**For P0 Issues:**

1. **Create PagerDuty Alert**
   - Title: "P0: System Down"
   - Description: Ticket details
   - Severity: Critical
   - Assign: Current on-call

2. **Include Information**
   - Ticket link
   - Error messages
   - Relevant logs
   - Customer impact

3. **Follow Up**
   - Acknowledge alert
   - Provide status updates
   - Resolve when fixed

### Slack Escalation

**Channel**: #apex-oncall

**Format**:
```
@oncall [P1] Ticket #12345 needs escalation
Issue: Brief description
Customer: customer@example.com
Impact: Multiple users
Link: https://tickets.example.com/12345
```

## Information Required for Escalation

### Required Information

1. **Ticket Details**
   - Ticket ID
   - Priority
   - Customer
   - Issue description

2. **Error Information**
   - Error messages
   - Stack traces
   - Log entries
   - Screenshots

3. **Impact Assessment**
   - Number of users affected
   - Business impact
   - Workaround available?

4. **Investigation Details**
   - Steps already taken
   - What didn't work
   - Hypotheses tested

### Optional but Helpful

- Request IDs
- Trace IDs
- Database query results
- Network captures
- Performance metrics

## Post-Escalation

### Tier 2 Responsibilities

1. **Monitor Ticket**
   - Track engineering progress
   - Provide customer updates
   - Gather additional information

2. **Customer Communication**
   - Acknowledge escalation
   - Provide estimated timeline
   - Set expectations

3. **Documentation**
   - Update ticket with escalation details
   - Document learnings
   - Update knowledge base

### Tier 3 (Engineering) Responsibilities

1. **Acknowledge** (<15 min for P0, <1 hour for P1)
   - Confirm receipt
   - Initial assessment
   - Estimated timeline

2. **Investigate**
   - Root cause analysis
   - Verify issue
   - Develop fix

3. **Resolve**
   - Deploy fix
   - Verify resolution
   - Update ticket

4. **Document**
   - Root cause
   - Fix applied
   - Prevention measures

## Escalation Metrics

### Tracking

```sql
-- Escalation rate
SELECT 
    COUNT(*) as total_tickets,
    COUNT(CASE WHEN escalated_to_tier3 THEN 1 END) as tier3_escalations,
    COUNT(CASE WHEN escalated_to_tier4 THEN 1 END) as tier4_escalations,
    ROUND(100.0 * COUNT(CASE WHEN escalated_to_tier3 THEN 1 END) / COUNT(*), 2) as tier3_rate,
    ROUND(100.0 * COUNT(CASE WHEN escalated_to_tier4 THEN 1 END) / COUNT(*), 2) as tier4_rate
FROM support_tickets
WHERE created_at > NOW() - INTERVAL '30 days';
```

**Targets:**
- Tier 3 escalation rate: <20%
- Tier 4 escalation rate: <5%

### Time to Escalation

**P0**: Should escalate immediately (<15 min)  
**P1**: Escalate if unresolved after 1 hour

---

**Next Steps:**
- [**Common Issues Resolution**](common-issues-resolution.md) - Step-by-step fixes
- [**Support Tiers**](support-tiers.md) - Tier definitions

