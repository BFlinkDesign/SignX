import * as pdfjs from 'pdfjs-dist';
import PdfWorker from 'pdfjs-dist/build/pdf.worker.min.mjs?worker';
// @ts-ignore - workerPort expects a Worker instance; Vite provides a constructor-compatible value
pdfjs.GlobalWorkerOptions.workerPort = new PdfWorker();

export { pdfjs };

export async function logFirstPageSize(url: string) {
  const loadingTask = pdfjs.getDocument(url);
  const doc = await loadingTask.promise;
  const page = await doc.getPage(1);
  const viewport = page.getViewport({ scale: 1 });
  // eslint-disable-next-line no-console
  console.log('[pdf] first page size', { width: viewport.width, height: viewport.height });
  return { width: viewport.width, height: viewport.height };
}


