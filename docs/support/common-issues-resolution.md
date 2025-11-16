# Common Issues Resolution

Top 20 most common issues with step-by-step resolutions.

## Issue Categories

1. [Authentication & Access](#authentication--access)
2. [Project Creation](#project-creation)
3. [Calculations](#calculations)
4. [File Operations](#file-operations)
5. [Performance](#performance)
6. [Reports](#reports)

## Authentication & Access

### Issue 1: Can't Log In

**Symptoms:**
- "Invalid credentials" error
- Account locked

**Diagnosis:**
```bash
# Check account status
curl -X GET https://api.example.com/users/user@example.com \
  -H "Authorization: Bearer $ADMIN_TOKEN"
```

**Resolution:**
1. Verify email/password correct
2. Check account status (not locked)
3. Reset password if needed
4. Clear browser cache/cookies

**Prevention:**
- Use password manager
- Enable 2FA (if available)

### Issue 2: API Key Invalid

**Symptoms:**
- 401 Unauthorized errors
- "Invalid API key" message

**Diagnosis:**
```bash
# Test API key
curl https://api.example.com/health \
  -H "X-Apex-Key: your-api-key"
```

**Resolution:**
1. Verify API key correct
2. Check key expiration
3. Regenerate key if needed
4. Update application with new key

## Project Creation

### Issue 3: Project Creation Fails

**Symptoms:**
- Error on project creation
- "Validation error" message

**Diagnosis:**
```bash
# Check error details
curl -X POST https://api.example.com/projects \
  -H "Content-Type: application/json" \
  -d '{"name": "Test", "account_id": "demo"}' | jq '.trace.validation_errors'
```

**Resolution:**
1. Verify required fields:
   - `name` (required, 1-255 chars)
   - `account_id` (required)
2. Check field formats
3. Review error messages
4. Fix validation errors

**Common Errors:**
- Missing required field
- Field too long/short
- Invalid format (email, etc.)

### Issue 4: Project Not Appearing in List

**Symptoms:**
- Created project doesn't show
- List filter issues

**Diagnosis:**
```sql
-- Check project exists
SELECT * FROM projects WHERE project_id = 'proj_123';
```

**Resolution:**
1. Refresh page
2. Check filters (status, search)
3. Verify permissions (access to project)
4. Clear browser cache

## Calculations

### Issue 5: Derive Not Updating

**Symptoms:**
- Canvas changes don't update form
- Confidence badge stuck

**Diagnosis:**
```bash
# Check API response
curl -X POST https://api.example.com/signage/common/cabinets/derive \
  -H "Content-Type: application/json" \
  -d '{...}' | jq '.confidence, .assumptions'
```

**Resolution:**
1. Check internet connection
2. Verify inputs valid (numeric, in range)
3. Wait for debounce (300ms)
4. Refresh page if stuck
5. Check browser console for errors

### Issue 6: Low Confidence Score

**Symptoms:**
- Confidence <0.7
- Orange/red badge
- Warnings displayed

**Diagnosis:**
```bash
# Check assumptions
curl ... | jq '.assumptions, .confidence'
```

**Resolution:**
1. Review assumptions array:
   - Check for warnings
   - Identify root cause
2. Adjust inputs:
   - Fix invalid ranges
   - Address warnings
3. Re-run calculation
4. Request engineering review if needed

**Common Causes:**
- Pole height >40ft (uncommon)
- Depth >5ft (review required)
- Unusual configuration

### Issue 7: No Pole Options Returned

**Symptoms:**
- Empty options list
- "No feasible poles" message

**Diagnosis:**
```bash
# Check filter parameters
curl -X POST https://api.example.com/signage/common/poles/options \
  -d '{...}' | jq '.assumptions, .confidence'
```

**Resolution:**
1. Check assumptions:
   - Loads too high?
   - Material constraint?
2. Adjust inputs:
   - Reduce loads
   - Change material
   - Increase height
3. Review alternatives in trace

## File Operations

### Issue 8: File Upload Fails

**Symptoms:**
- Upload error
- "File too large" or "Invalid type"

**Diagnosis:**
```bash
# Check file size/type
ls -lh file.pdf
file file.pdf
```

**Resolution:**
1. Verify file size (<10MB)
2. Check file type (PDF, images)
3. Get new presigned URL (expires after 1 hour)
4. Retry upload
5. Check CORS if browser error

### Issue 9: Presigned URL Expired

**Symptoms:**
- 403 Forbidden on upload
- "URL expired" error

**Resolution:**
1. Request new presigned URL:
   ```bash
   curl -X POST https://api.example.com/files/presign \
     -d '{"filename": "file.pdf"}'
   ```
2. Use new URL immediately
3. Upload within 1 hour

### Issue 10: Can't Download File

**Symptoms:**
- 404 Not Found
- File not accessible

**Diagnosis:**
```bash
# Check file exists
curl -I https://api.example.com/artifacts/blobs/ab/abc123.pdf
```

**Resolution:**
1. Verify file key correct
2. Check file permissions
3. Request new download URL
4. Contact support if persists

## Performance

### Issue 11: Slow Response Times

**Symptoms:**
- Requests take >5 seconds
- Timeout errors

**Diagnosis:**
```bash
# Check API latency
curl -w "@curl-format.txt" https://api.example.com/health

# Check metrics
curl https://api.example.com/metrics | grep http_request_duration
```

**Resolution:**
1. Check internet connection
2. Clear browser cache
3. Try different network
4. Check system status page
5. Contact support if persistent

### Issue 12: High Error Rate

**Symptoms:**
- Multiple 5xx errors
- Intermittent failures

**Diagnosis:**
```bash
# Check error rate
curl https://api.example.com/metrics | grep http_requests_total | grep "status=\"5"
```

**Resolution:**
1. Check system status
2. Retry failed requests
3. Contact support immediately
4. Provide error details

## Reports

### Issue 13: Report Not Generating

**Symptoms:**
- Task stuck in "processing"
- No PDF after 5+ minutes

**Diagnosis:**
```bash
# Check task status
curl https://api.example.com/tasks/task_123

# Check worker logs
docker compose logs worker | grep report
```

**Resolution:**
1. Wait 30-60 seconds (normal)
2. Check task status
3. Verify Celery workers running
4. Retry if failed
5. Contact support if >5 minutes

### Issue 14: Report Content Incorrect

**Symptoms:**
- Wrong calculations in PDF
- Missing information

**Diagnosis:**
```bash
# Verify payload
curl https://api.example.com/projects/proj_123/payload
```

**Resolution:**
1. Verify payload correct
2. Regenerate report
3. Check constants version
4. Report bug if persists

### Issue 15: Can't Download Report

**Symptoms:**
- Download link doesn't work
- 404 Not Found

**Resolution:**
1. Verify report generated
2. Check download URL
3. Request new download link
4. Clear browser cache

## System Issues

### Issue 16: Service Unavailable (503)

**Symptoms:**
- All requests return 503
- "Service temporarily unavailable"

**Diagnosis:**
```bash
# Check health
curl https://api.example.com/health
curl https://api.example.com/ready
```

**Resolution:**
1. Check system status page
2. Wait 5 minutes (maintenance?)
3. Contact support immediately
4. Provide error details

### Issue 17: Database Connection Error

**Symptoms:**
- "Database connection failed"
- 500 errors on queries

**Diagnosis:**
```bash
# Check database health
curl https://api.example.com/ready | jq '.checks.database'
```

**Resolution:**
1. Check system status
2. Retry request
3. Contact support (P1 issue)
4. System will auto-recover typically

### Issue 18: Cache Issues

**Symptoms:**
- Stale data
- Inconsistent responses

**Resolution:**
1. Clear browser cache
2. Hard refresh (Ctrl+F5)
3. Wait for cache TTL (if server-side)
4. Report if persists

## Integration Issues

### Issue 19: Webhook Not Received

**Symptoms:**
- Integration not triggering
- Missing events

**Diagnosis:**
```bash
# Check webhook config
curl https://api.example.com/webhooks

# Test webhook
curl -X POST https://your-app.com/webhook \
  -H "X-Apex-Signature: ..." \
  -d '{...}'
```

**Resolution:**
1. Verify webhook URL correct
2. Check signature verification
3. Test webhook endpoint
4. Review webhook logs

### Issue 20: Idempotency Key Conflict

**Symptoms:**
- "Idempotency-Key already used"
- Submission fails

**Resolution:**
1. Use unique key (UUID)
2. Clear stale key if >24 hours old
3. Store key in localStorage for retry
4. Generate new key for new submission

## Quick Reference

| Issue | Priority | Response Time | Resolution Time |
|-------|----------|---------------|-----------------|
| Service Down | P0 | <15 min | <4 hours |
| High Error Rate | P1 | <1 hour | <24 hours |
| Report Not Generating | P2 | <4 hours | <1 week |
| Upload Failed | P2 | <4 hours | <1 week |
| Low Confidence | P3 | <24 hours | Backlog |

---

**Next Steps:**
- [**Support Tiers**](support-tiers.md) - Tier structure
- [**SLA Definitions**](sla-definitions.md) - Response times

