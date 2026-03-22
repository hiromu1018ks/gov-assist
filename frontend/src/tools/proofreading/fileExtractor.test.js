import { describe, it, expect, vi, beforeEach } from 'vitest';

const { mockExtractRawText, mockGetDocument } = vi.hoisted(() => ({
  mockExtractRawText: vi.fn(),
  mockGetDocument: vi.fn(),
}));

vi.mock('mammoth', () => ({ default: { extractRawText: mockExtractRawText } }));
vi.mock('pdfjs-dist', () => ({
  getDocument: mockGetDocument,
  GlobalWorkerOptions: { workerSrc: '' },
}));

import { extractText } from './fileExtractor';

describe('fileExtractor', () => {
  beforeEach(() => {
    vi.clearAllMocks();
  });

  function makeFile(name, content = '') {
    return new File([content], name, { type: 'application/octet-stream' });
  }

  it('extracts text from .docx file using mammoth', async () => {
    mockExtractRawText.mockResolvedValue({ value: '  extracted docx text  ', messages: [] });

    const result = await extractText(makeFile('test.docx', 'binary'));

    expect(mockExtractRawText).toHaveBeenCalledOnce();
    expect(result.text).toBe('extracted docx text');
    expect(result.error).toBeNull();
  });

  it('extracts text from .pdf file using pdfjs-dist', async () => {
    const mockGetTextContent = vi.fn().mockResolvedValue({
      items: [{ str: 'Hello ' }, { str: 'world' }],
    });
    const mockGetPage = vi.fn().mockResolvedValue({ getTextContent: mockGetTextContent });
    mockGetDocument.mockReturnValue({
      promise: Promise.resolve({ numPages: 1, getPage: mockGetPage }),
    });

    const result = await extractText(makeFile('test.pdf', 'binary'));

    expect(mockGetDocument).toHaveBeenCalledOnce();
    expect(result.text).toBe('Hello world');
    expect(result.error).toBeNull();
  });

  it('returns error for unsupported file type', async () => {
    const result = await extractText(makeFile('test.xlsx'));

    expect(result.text).toBe('');
    expect(result.error).toContain('対応していない');
  });

  it('returns error when PDF has no extractable text (image-only)', async () => {
    mockGetDocument.mockReturnValue({
      promise: Promise.resolve({
        numPages: 1,
        getPage: vi.fn().mockResolvedValue({
          getTextContent: vi.fn().mockResolvedValue({ items: [] }),
        }),
      }),
    });

    const result = await extractText(makeFile('scan.pdf'));

    expect(result.text).toBe('');
    expect(result.error).toContain('テキストを抽出できませんでした');
  });

  it('extracts text from multi-page PDF by concatenating all pages', async () => {
    const mockGetTextContent1 = vi.fn().mockResolvedValue({
      items: [{ str: 'Page 1 text' }],
    });
    const mockGetTextContent2 = vi.fn().mockResolvedValue({
      items: [{ str: 'Page 2 text' }],
    });
    const mockGetPage = vi.fn()
      .mockResolvedValueOnce({ getTextContent: mockGetTextContent1 })
      .mockResolvedValueOnce({ getTextContent: mockGetTextContent2 });
    mockGetDocument.mockReturnValue({
      promise: Promise.resolve({ numPages: 2, getPage: mockGetPage }),
    });

    const result = await extractText(makeFile('multi.pdf', 'binary'));

    expect(result.text).toBe('Page 1 text\nPage 2 text');
    expect(mockGetPage).toHaveBeenCalledTimes(2);
  });

  it('returns error when mammoth throws', async () => {
    mockExtractRawText.mockRejectedValue(new Error('Invalid docx'));

    const result = await extractText(makeFile('broken.docx'));

    expect(result.text).toBe('');
    expect(result.error).toContain('読み込みに失敗しました');
  });

  it('returns error when pdfjs-dist throws', async () => {
    mockGetDocument.mockReturnValue({
      promise: Promise.reject(new Error('Invalid PDF')),
    });

    const result = await extractText(makeFile('broken.pdf'));

    expect(result.text).toBe('');
    expect(result.error).toContain('読み込みに失敗しました');
  });
});
