// no React import needed for react-jsx runtime
import './App.css';
import { useEffect, useRef, useState } from 'react';
import { PDFViewer } from '@/components/PDFViewer';
import { Annotator } from '@/components/Annotator';

export default function App() {
  const fileRef = useRef<HTMLInputElement | null>(null);
  const [url, setUrl] = useState<string>('');
  const [jobId, setJobId] = useState<number | null>(null);
  const [jobStatus, setJobStatus] = useState<any>(null);

  const loadSample = () => setUrl('/sample.pdf');
  const openFile = (e: React.ChangeEvent<HTMLInputElement>) => {
    const f = e.target.files?.[0];
    if (f) setUrl(URL.createObjectURL(f));
  };

  const startAuto = async () => {
    try {
      const [{ open }, { invoke }] = await Promise.all([
        import('@tauri-apps/api/dialog'),
        import('@tauri-apps/api/core'),
      ]);
      const picked = await open({ filters: [{ name: 'PDF', extensions: ['pdf'] }] });
      const pdfPath = typeof picked === 'string' ? picked : Array.isArray(picked) ? picked[0] : undefined;
      if (!pdfPath) return;
      const id = await invoke<number>('start_auto_takeoff', { pdfPath });
      setJobId(id);
    } catch (e) {
      // eslint-disable-next-line no-alert
      alert('Auto Takeoff requires the desktop app. ' + (e as Error).message);
    }
  };

  useEffect(() => {
    if (!jobId) return;
    let cancelled = false;
    const tick = async () => {
      try {
        const { invoke } = await import('@tauri-apps/api/core');
        const s = await invoke<any>('job_status', { id: jobId });
        if (!cancelled) setJobStatus(s);
      } catch {
        /* ignore */
      }
    };
    const t = setInterval(tick, 1000);
    void tick();
    return () => { cancelled = true; clearInterval(t); };
  }, [jobId]);

  return (
    <div className="app">
      <header className="header">
        <h1>BetterBeam</h1>
        <div className="actions">
          <button onClick={loadSample}>Load sample PDF</button>
          <button onClick={() => fileRef.current?.click()}>Open file…</button>
          <input ref={fileRef} type="file" accept="application/pdf" onChange={openFile} style={{ display: 'none' }} />
          <button onClick={startAuto}>Auto Takeoff</button>
          {jobId && (
            <span style={{ marginLeft: 8, fontSize: 12 }}>
              {typeof jobStatus?.state === 'object' && 'Running' in jobStatus.state
                ? `Auto: ${jobStatus.state.Running.stage} ${(jobStatus.state.Running.pct ?? 0)}%`
                : typeof jobStatus?.state === 'string'
                  ? `Auto: ${jobStatus.state}`
                  : 'Auto: running'}
            </span>
          )}
        </div>
      </header>

      <div className="workspace">
        <aside className="tools">
          <p>Tools</p>
        </aside>
        <main className="viewer">
          <div className="viewer-stack">
            {url && <PDFViewer url={url} />}
            <Annotator />
          </div>
        </main>
      </div>
    </div>
  );
}