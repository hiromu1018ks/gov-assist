let pdfWorkerInitialized = false;

async function getPdfjsLib() {
  const pdfjsLib = await import('pdfjs-dist');
  if (!pdfWorkerInitialized) {
    pdfjsLib.GlobalWorkerOptions.workerSrc = new URL(
      'pdfjs-dist/build/pdf.worker.min.mjs',
      import.meta.url,
    ).toString();
    pdfWorkerInitialized = true;
  }
  return pdfjsLib;
}

/**
 * Extract text from a .docx or .pdf file.
 * @param {File} file - The file to extract text from
 * @returns {Promise<{text: string, error: string|null}>}
 */
export async function extractText(file) {
  const ext = file.name.split('.').pop().toLowerCase();

  if (ext !== 'docx' && ext !== 'pdf') {
    return { text: '', error: '対応していないファイル形式です（.docx, .pdf のみ対応）。' };
  }

  try {
    if (ext === 'docx') {
      return await extractDocx(file);
    }
    return await extractPdf(file);
  } catch {
    return { text: '', error: 'ファイルの読み込みに失敗しました。テキストを直接入力してください。' };
  }
}

async function extractDocx(file) {
  const { default: mammoth } = await import('mammoth');
  const arrayBuffer = await file.arrayBuffer();
  const result = await mammoth.extractRawText({ arrayBuffer });
  const text = result.value.trim();

  if (!text) {
    return { text: '', error: 'テキストを抽出できませんでした。テキスト形式のファイルか、テキストを直接入力してください。' };
  }

  return { text, error: null };
}

async function extractPdf(file) {
  const pdfjsLib = await getPdfjsLib();
  const arrayBuffer = await file.arrayBuffer();
  const pdf = await pdfjsLib.getDocument({ data: arrayBuffer }).promise;

  let fullText = '';
  for (let i = 1; i <= pdf.numPages; i++) {
    const page = await pdf.getPage(i);
    const content = await page.getTextContent();
    const pageText = content.items.map((item) => item.str).join('');
    fullText += pageText + '\n';
  }

  fullText = fullText.trim();

  if (!fullText) {
    return { text: '', error: 'テキストを抽出できませんでした。テキスト形式の PDF か、テキストを直接入力してください。' };
  }

  return { text: fullText, error: null };
}
