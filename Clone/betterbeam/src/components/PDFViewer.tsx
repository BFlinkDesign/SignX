import { useEffect, useRef, useState } from 'react';
import type { PDFDocumentProxy } from 'pdfjs-dist';
import { pdfjs } from '@/lib/pdf';

interface Props { url: string }

export function PDFViewer({ url }: Props) {
  const canvasRef = useRef<HTMLCanvasElement | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [_pageSize, setPageSize] = useState<{ width: number; height: number } | null>(null);

  useEffect(() => {
    let mounted = true;
    let doc: PDFDocumentProxy | null = null;
    let resizeObserver: ResizeObserver | null = null;

    const render = async () => {
      if (!canvasRef.current) return;
      try {
        const loadingTask = pdfjs.getDocument(url);
        doc = await loadingTask.promise;
        const page = await doc.getPage(1);
        const ratio = window.devicePixelRatio || 1;
        const viewport = page.getViewport({ scale: 1 });
        setPageSize({ width: viewport.width, height: viewport.height });
        const canvas = canvasRef.current;
        const context = canvas.getContext('2d');
        if (!context) return;
        const parent = canvas.parentElement as HTMLElement;
        const scale = Math.min(parent.clientWidth / viewport.width, 2);
        const scaled = page.getViewport({ scale });
        canvas.width = Math.floor(scaled.width * ratio);
        canvas.height = Math.floor(scaled.height * ratio);
        canvas.style.width = `${Math.floor(scaled.width)}px`;
        canvas.style.height = `${Math.floor(scaled.height)}px`;
        context.setTransform(ratio, 0, 0, ratio, 0, 0);
        await page.render({ canvas, canvasContext: context, viewport: scaled }).promise;
      } catch (e: any) {
        if (!mounted) return;
        // eslint-disable-next-line no-console
        console.error(e);
        setError(String(e?.message || e));
      }
    };

    render();

    // re-render on container resize
    if (canvasRef.current?.parentElement) {
      resizeObserver = new ResizeObserver(() => { void render(); });
      resizeObserver.observe(canvasRef.current.parentElement);
    }

    return () => {
      mounted = false;
      resizeObserver?.disconnect();
      doc?.destroy();
    };
  }, [url]);

  return (
    <div style={{ display: 'flex', justifyContent: 'center' }}>
      <canvas ref={canvasRef} />
      {error && <div style={{ color: 'red' }}>{error}</div>}
    </div>
  );
}
