/**
 * テキスト前処理ユーティリティ（§3.3.2）
 * バックエンド送信前にテキストを正規化する
 */

const MAX_CHARS = 8000;

/**
 * テキストを前処理して正規化する
 * @param {string} text - 生テキスト
 * @returns {{ text: string, error: string|null }}
 */
export function preprocessText(text) {
  if (typeof text !== 'string') {
    return { text: '', error: 'テキストが文字列ではありません。' };
  }

  let result = text;

  // 1. NULL文字除去: 制御文字（\x00〜\x08、\x0b、\x0e〜\x1f）を除去
  //    \x0c(\f) はページ区切りルールで処理するため除外
  //    \t(0x09), \n(0x0a), \r(0x0d) は保持
  result = result.replace(/[\x00-\x08\x0b\x0e-\x1f]/g, '');

  // 2. ページ区切りの除去: \f を改行に変換
  result = result.replace(/\f/g, '\n');

  // 3. 改行の正規化: \r\n / \r を \n に統一
  result = result.replace(/\r\n?/g, '\n');

  // 4. 行頭・行末の空白トリム: 各行の先頭・末尾スペース・タブを除去
  result = result.split('\n').map((line) => line.trim()).join('\n');

  // 5. 連続改行の正規化: 3行以上の連続改行を2行に圧縮
  result = result.replace(/\n{3,}/g, '\n\n');

  // 6. 末尾の余分な改行を除去
  result = result.trimEnd();

  // 7. 文字数チェック
  if (result.length > MAX_CHARS) {
    return {
      text: result,
      error: `前処理後のテキストが${MAX_CHARS.toLocaleString()}文字を超えています（${result.length.toLocaleString()}文字）。テキストを短くしてください。`,
    };
  }

  return { text: result, error: null };
}
