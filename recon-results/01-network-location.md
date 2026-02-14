# TEST 1: Network Location

**Date:** 2026-02-14
**Target:** `eaglesign.keyedinsign.com`

## Results

### DNS Resolution from Cloud Sandbox

```
DNS RESOLUTION FAILED: [Errno -3] Temporary failure in name resolution
```

**This is expected.** This Claude Code session runs in a cloud sandbox without access to Eagle Sign's internal network or VPN. The host `eaglesign.keyedinsign.com` was successfully accessed from `C:\Scripts\SignX\Keyedin` on Eagle Sign's network in previous sessions (2025-11-12).

### Analysis

The DNS failure from a public internet host is actually informative:

- If `eaglesign.keyedinsign.com` resolved publicly, we'd see it from anywhere
- DNS failure from outside suggests it may resolve only via:
  1. Private DNS on Eagle Sign's network (ON-PREM)
  2. VPN-only DNS resolution (HOSTED but private)
  3. Split-horizon DNS (public domain, private records)

### Cannot Determine from This Environment

All subsequent tests (2-5) also require network access to `eaglesign.keyedinsign.com` which is unreachable from this sandbox.

## Commands Brady Must Run

Brady is connected via Cisco VPN. Run these from PowerShell:

```powershell
# 1. DNS Resolution
nslookup eaglesign.keyedinsign.com

# 2. Check if private or public IP
# Private ranges: 10.x.x.x, 172.16-31.x.x, 192.168.x.x
# If private → ON-PREM or hosted on Eagle Sign's network
# If public → hosted by KeyedIn/KIMCO

# 3. Trace route to see network path
tracert eaglesign.keyedinsign.com

# 4. Check both ports
Test-NetConnection -ComputerName eaglesign.keyedinsign.com -Port 443
Test-NetConnection -ComputerName eaglesign.keyedinsign.com -Port 8443

# 5. Quick curl test (no auth needed)
curl -v https://eaglesign.keyedinsign.com/cgi-bin/mvi.exe/LOGIN.START 2>&1 | head -30
```

## Verdict

**BLOCKED** — Cannot test from this environment. Brady must run the commands above.
