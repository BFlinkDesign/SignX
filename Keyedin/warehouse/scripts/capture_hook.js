// =============================================================================
// KeyedIn Informer GWT RPC Capture Hook
// =============================================================================
//
// USAGE:
//   1. Login to KeyedIn ERP, navigate to Informer reports home
//   2. Open Chrome DevTools (F12) → Console tab
//   3. Paste this entire script and press Enter
//   4. Click through each report's "Data" tab normally
//   5. The console will log every captured RPC call
//   6. When done, run:  copy(JSON.stringify(window._captures, null, 2))
//   7. Paste into a file: C:\Scripts\keyedin-capture\reports\raw_captures.json
//   8. Run:  python split_captures.py
//
// The hook captures both request AND response for ViewRPCService and
// commandService calls. It also tracks which reportId you're viewing
// from the URL hash.
// =============================================================================

(function() {
  'use strict';

  // Storage
  window._captures = window._captures || [];
  window._captureCount = window._captureCount || 0;

  // Track current report from URL hash
  function getCurrentReportId() {
    const hash = window.location.hash || '';
    const match = hash.match(/reportId=(\d+)/);
    return match ? parseInt(match[1]) : null;
  }

  // --- Hook XMLHttpRequest ---
  const origOpen = XMLHttpRequest.prototype.open;
  const origSend = XMLHttpRequest.prototype.send;

  XMLHttpRequest.prototype.open = function(method, url, async, user, pass) {
    this._captureUrl = url;
    this._captureMethod = method;
    return origOpen.apply(this, arguments);
  };

  XMLHttpRequest.prototype.send = function(body) {
    const url = this._captureUrl || '';
    const isRPC = url.includes('ViewRPCService') || url.includes('commandService');

    if (isRPC && body && this._captureMethod === 'POST') {
      const reportId = getCurrentReportId();
      const endpoint = url.includes('ViewRPCService') ? 'view' : 'command';
      const captureIndex = window._captureCount++;

      // Capture the request
      const entry = {
        index: captureIndex,
        reportId: reportId,
        endpoint: endpoint,
        url: url,
        requestPayload: body,
        requestBytes: body.length,
        responseText: null,
        responseBytes: 0,
        timestamp: new Date().toISOString(),
        urlHash: window.location.hash,
      };

      // Hook the response
      this.addEventListener('load', function() {
        try {
          entry.responseText = this.responseText;
          entry.responseBytes = (this.responseText || '').length;
          console.log(
            `%c[CAPTURED #${captureIndex}] ${endpoint} — reportId=${reportId} — req=${entry.requestBytes}B resp=${entry.responseBytes}B`,
            'color: #00ff00; font-weight: bold'
          );
        } catch(e) {
          console.warn(`[CAPTURE] Response read failed for #${captureIndex}:`, e);
        }
      });

      this.addEventListener('error', function() {
        console.warn(`[CAPTURE] Request #${captureIndex} failed (network error)`);
        entry.error = 'network_error';
      });

      window._captures.push(entry);
      console.log(
        `%c[HOOK #${captureIndex}] ${endpoint} POST — reportId=${reportId} — ${body.length}B payload — waiting for response...`,
        'color: #ffff00'
      );
    }

    return origSend.apply(this, arguments);
  };

  // --- Hook fetch() as fallback ---
  const origFetch = window.fetch;
  window.fetch = function(input, init) {
    const url = typeof input === 'string' ? input : (input.url || '');
    const method = (init && init.method) || 'GET';
    const body = (init && init.body) || null;
    const isRPC = url.includes('ViewRPCService') || url.includes('commandService');

    if (isRPC && body && method === 'POST') {
      const reportId = getCurrentReportId();
      const endpoint = url.includes('ViewRPCService') ? 'view' : 'command';
      const captureIndex = window._captureCount++;
      const bodyStr = typeof body === 'string' ? body : '';

      const entry = {
        index: captureIndex,
        reportId: reportId,
        endpoint: endpoint,
        url: url,
        requestPayload: bodyStr,
        requestBytes: bodyStr.length,
        responseText: null,
        responseBytes: 0,
        timestamp: new Date().toISOString(),
        urlHash: window.location.hash,
        via: 'fetch',
      };

      window._captures.push(entry);
      console.log(
        `%c[HOOK-FETCH #${captureIndex}] ${endpoint} POST — reportId=${reportId} — ${bodyStr.length}B`,
        'color: #ffff00'
      );

      return origFetch.apply(this, arguments).then(function(response) {
        // Clone to read body without consuming it
        const clone = response.clone();
        clone.text().then(function(text) {
          entry.responseText = text;
          entry.responseBytes = text.length;
          console.log(
            `%c[CAPTURED-FETCH #${captureIndex}] ${endpoint} — resp=${text.length}B`,
            'color: #00ff00; font-weight: bold'
          );
        });
        return response;
      });
    }

    return origFetch.apply(this, arguments);
  };

  // --- Status helpers ---
  window._captureStatus = function() {
    const byReport = {};
    for (const c of window._captures) {
      const key = c.reportId || 'unknown';
      if (!byReport[key]) byReport[key] = {view: 0, command: 0, totalBytes: 0};
      byReport[key][c.endpoint]++;
      byReport[key].totalBytes += c.responseBytes;
    }
    console.table(byReport);
    console.log(`Total captures: ${window._captures.length}`);
    return byReport;
  };

  window._captureExport = function() {
    const json = JSON.stringify(window._captures, null, 2);
    // Try clipboard
    if (navigator.clipboard) {
      navigator.clipboard.writeText(json).then(
        () => console.log(`%c[EXPORT] ${window._captures.length} captures copied to clipboard (${json.length} bytes)`, 'color: #00ff00; font-weight: bold'),
        () => console.log('[EXPORT] Clipboard failed. Use: copy(JSON.stringify(window._captures, null, 2))')
      );
    } else {
      copy(json);
      console.log(`%c[EXPORT] ${window._captures.length} captures copied via copy()`, 'color: #00ff00; font-weight: bold');
    }
  };

  window._captureDownload = function() {
    const json = JSON.stringify(window._captures, null, 2);
    const blob = new Blob([json], {type: 'application/json'});
    const url = URL.createObjectURL(blob);
    const a = document.createElement('a');
    a.href = url;
    a.download = 'raw_captures.json';
    document.body.appendChild(a);
    a.click();
    document.body.removeChild(a);
    URL.revokeObjectURL(url);
    console.log(`%c[DOWNLOAD] ${window._captures.length} captures saved as raw_captures.json`, 'color: #00ff00; font-weight: bold');
  };

  // --- Ready ---
  console.log('%c[CAPTURE HOOK ACTIVE]', 'color: #00ff00; font-size: 16px; font-weight: bold');
  console.log('Commands:');
  console.log('  _captureStatus()   — show capture summary by report');
  console.log('  _captureExport()   — copy all captures to clipboard');
  console.log('  _captureDownload() — download as raw_captures.json');
  console.log('');
  console.log('Now click through each report. The console will log every GWT RPC call.');
})();
