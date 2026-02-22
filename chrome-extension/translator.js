/**
 * Voice Bridge - 翻訳モジュール
 *
 * Google Translate の非公式エンドポイントを使用して英→日翻訳を行う。
 * Chrome 拡張のコンテキストでは CORS 制限を受けないため直接アクセス可能。
 */

class Translator {
  constructor() {
    this._endpoint = "https://translate.googleapis.com/translate_a/single";
  }

  /**
   * テキストを英語から日本語に翻訳
   * @param {string} text - 翻訳する英語テキスト
   * @returns {Promise<string>} 日本語テキスト
   */
  async translate(text) {
    if (!text || !text.trim()) {
      return "";
    }

    const params = new URLSearchParams({
      client: "gtx",
      sl: "en",       // ソース言語: 英語
      tl: "ja",       // ターゲット言語: 日本語
      dt: "t",        // 翻訳テキストを返す
      q: text,
    });

    const url = `${this._endpoint}?${params.toString()}`;

    for (let attempt = 0; attempt < 3; attempt++) {
      try {
        const response = await fetch(url);

        if (!response.ok) {
          throw new Error(`HTTP ${response.status}`);
        }

        const data = await response.json();

        // レスポンス形式: [[["翻訳テキスト","原文",null,null,10]],null,"en",...]
        if (data && data[0]) {
          const translated = data[0]
            .map((segment) => segment[0])
            .filter(Boolean)
            .join("");
          return translated;
        }

        return "";
      } catch (err) {
        console.warn(`[Translator] 翻訳エラー (${attempt + 1}/3):`, err.message);
        if (attempt < 2) {
          // リトライ前に待機（指数バックオフ）
          await new Promise((r) => setTimeout(r, 500 * (attempt + 1)));
        }
      }
    }

    console.error("[Translator] 翻訳に3回失敗しました");
    return "";
  }
}
