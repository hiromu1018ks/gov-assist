import { describe, it, expect } from 'vitest';
import { preprocessText } from './preprocess';

describe('preprocessText', () => {
  // --- Rule: NULL文字除去 (§3.3.2) ---

  it('removes NULL and control characters but preserves tab, newline, carriage return, form feed', () => {
    // \x00 (NULL), \x01-\x08, \x0b (VT), \x0e-\x1f should be removed
    // \x09 (TAB), \x0a (LF), \x0d (CR), \x0c/\f (FF — handled by page break rule) are preserved
    const input = 'hel\x00lo\two\x08rld\x0b\x0e\x1f';
    const { text } = preprocessText(input);
    expect(text).toBe('hello\tworld');
  });

  it('preserves tab characters in text', () => {
    const { text } = preprocessText('col1\tcol2\tcol3');
    expect(text).toBe('col1\tcol2\tcol3');
  });

  // --- Rule: ページ区切りの除去 (§3.3.2) ---

  it('replaces form feed (\\f) with newline', () => {
    const { text } = preprocessText('page1\fpage2');
    expect(text).toBe('page1\npage2');
  });

  it('replaces multiple form feeds with newlines', () => {
    const { text } = preprocessText('a\fb\f\fc');
    expect(text).toBe('a\nb\n\nc');
  });

  // --- Rule: 行頭・行末の空白トリム (§3.3.2) ---

  it('trims leading and trailing whitespace from each line', () => {
    const { text } = preprocessText('  hello  \n  world  ');
    expect(text).toBe('hello\nworld');
  });

  it('removes tabs from line edges', () => {
    const { text } = preprocessText('\t\tindented\t\n\tnext\t');
    expect(text).toBe('indented\nnext');
  });

  // --- Rule: 連続改行の正規化 (§3.3.2) ---

  it('collapses 3+ consecutive newlines to 2', () => {
    const { text } = preprocessText('a\n\n\nb');
    expect(text).toBe('a\n\nb');
  });

  it('collapses many consecutive newlines to 2', () => {
    const { text } = preprocessText('a\n\n\n\n\n\nb');
    expect(text).toBe('a\n\nb');
  });

  it('preserves exactly 2 consecutive newlines', () => {
    const { text } = preprocessText('a\n\nb');
    expect(text).toBe('a\n\nb');
  });

  it('preserves single newlines', () => {
    const { text } = preprocessText('a\nb');
    expect(text).toBe('a\nb');
  });

  // --- Combined preprocessing ---

  it('applies all rules in sequence for realistic PDF extraction output', () => {
    // Simulates PDF extraction: form feeds, extra newlines, control chars, whitespace, CRLF
    const input = '  Document Title  \x00\r\n\n\f  Section 1  \x0b\r\n  Content here  \n\n\n\n  ';
    const { text } = preprocessText(input);
    expect(text).toBe('Document Title\n\nSection 1\nContent here');
  });

  it('handles empty string', () => {
    const { text, error } = preprocessText('');
    expect(text).toBe('');
    expect(error).toBeNull();
  });

  it('handles string with only whitespace and control characters', () => {
    const { text, error } = preprocessText('  \x00\x01\n\n\n  ');
    expect(text).toBe('');
    expect(error).toBeNull();
  });

  it('handles normal Japanese text without changes', () => {
    const input = 'これはテスト文書です。\n\n段落2です。';
    const { text } = preprocessText(input);
    expect(text).toBe(input);
  });

  // --- 文字数チェック (§3.3.2) ---

  it('returns error when preprocessed text exceeds 8000 characters', () => {
    const longText = 'あ'.repeat(8001);
    const { text, error } = preprocessText(longText);
    expect(text.length).toBe(8001);
    expect(error).toContain('8,000');
    expect(error).toContain('8,001');
  });

  it('returns no error when text is exactly 8000 characters', () => {
    const text8000 = 'あ'.repeat(8000);
    const { text, error } = preprocessText(text8000);
    expect(text.length).toBe(8000);
    expect(error).toBeNull();
  });

  it('returns no error for short text', () => {
    const { text, error } = preprocessText('短いテキスト');
    expect(error).toBeNull();
    expect(text).toBe('短いテキスト');
  });

  // --- Edge cases ---

  it('handles non-string input gracefully', () => {
    const { text, error } = preprocessText(null);
    expect(text).toBe('');
    expect(error).toBe('テキストが文字列ではありません。');
  });

  it('handles undefined input gracefully', () => {
    const { text, error } = preprocessText(undefined);
    expect(text).toBe('');
    expect(error).toBe('テキストが文字列ではありません。');
  });

  it('handles numeric input gracefully', () => {
    const { text, error } = preprocessText(12345);
    expect(text).toBe('');
    expect(error).toBe('テキストが文字列ではありません。');
  });

  it('removes carriage returns (\\r) from CRLF sequences correctly', () => {
    const { text } = preprocessText('a\r\n\r\nb');
    expect(text).toBe('a\n\nb');
  });

  it('normalizes bare \\r to \\n', () => {
    const { text } = preprocessText('hel\rlo');
    expect(text).toBe('hel\nlo');
  });
});
