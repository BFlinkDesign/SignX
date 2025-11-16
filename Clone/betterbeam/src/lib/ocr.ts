export async function ocrImage(blob: Blob) {
  const { createWorker } = await import('tesseract.js');
  const worker = await createWorker();
  try {
    // tesseract.js v6: reinitialize replaces initialize in types; use it for TS compat
    // @ts-expect-error types mismatch across versions
    if (typeof worker.loadLanguage === 'function') {
      // @ts-ignore
      await worker.loadLanguage('eng');
    }
    // @ts-ignore reinitialize exists in types; initialize exists at runtime sometimes
    if (typeof worker.reinitialize === 'function') {
      // @ts-ignore
      await worker.reinitialize('eng');
    } else if (typeof (worker as any).initialize === 'function') {
      await (worker as any).initialize('eng');
    }
    const { data } = await worker.recognize(blob);
    return data.text as string;
  } finally {
    await worker.terminate();
  }
}


