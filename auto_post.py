# -*- coding: utf-8 -*-
# auto_post.py
import json
import logging
import os
import pathlib
import re
import string
from collections import Counter
from datetime import datetime, timezone
from logging.handlers import RotatingFileHandler
from typing import Iterable

import tweepy
import vertexai
from dotenv import load_dotenv
from vertexai.preview.generative_models import GenerativeModel

# .envファイルを読み込む
load_dotenv()
# ====== パス設定（必要に応じて変更） ======
BASE_DIR = pathlib.Path(__file__).resolve().parent
OUT_DIR = BASE_DIR / "out_auto"
LOG_DIR = BASE_DIR / "logs_auto"
OUT_DIR.mkdir(parents=True, exist_ok=True)
LOG_DIR.mkdir(parents=True, exist_ok=True)

MD_PATH = OUT_DIR / "tweets_preview.md"       # 追記されるMarkdown
JSON_PATH = OUT_DIR / "tweets_payload.json"   # 常に最新で上書き
LOG_PATH = LOG_DIR / "auto_post.log"  # ローテーションログ

# === Dedup additions ===
INDEX_PATH = OUT_DIR / "dedup_index.json"  # 過去ツイートの軽量インデックス

# ====== ログ設定（printは使わない） ======
logger = logging.getLogger("auto_post")
logger.setLevel(logging.INFO)
handler = RotatingFileHandler(
    LOG_PATH, maxBytes=1_000_000, backupCount=5, encoding="utf-8"
)
formatter = logging.Formatter(
    "%(asctime)s [%(levelname)s] %(message)s", datefmt="%Y-%m-%d %H:%M:%S"
)
handler.setFormatter(formatter)
logger.addHandler(handler)

# （任意）タスクから手動実行時の可視性を上げたい場合はコメント解除
# console = logging.StreamHandler()
# console.setFormatter(formatter)
# logger.addHandler(console)

def sanitize_and_limit(text: str, limit: int = 140) -> str:
    """改行や連続空白を畳み、文字数を上限に収める。"""
    if not text:
        return ""
    one_line = " ".join(text.split())
    if len(one_line) > limit:
        logger.warning("Tweet text exceeded %d chars; truncating.", limit)
        one_line = one_line[:limit]
    return one_line

def append_markdown_preview(text: str, hashtags: str | None, citations: list[str] | None, posted_url: str | None):
    ts = datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")
    with MD_PATH.open("a", encoding="utf-8") as f:
        f.write(f"\n\n# Tweet Preview ({ts})\n\n")
        f.write(text.replace("\n", " ") + "\n\n")
        if hashtags:
            f.write(hashtags + "\n\n")
        if citations:
            for u in citations:
                f.write(f"- {u}\n")
            f.write("\n")
        if posted_url:
            f.write(f"Posted: {posted_url}\n")

def save_payload_json(payload: dict):
    with JSON_PATH.open("w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)

# === Dedup additions: 軽量重複検出ユーティリティ ===
_PUNCT_TABLE = str.maketrans(
    {c: " " for c in (string.punctuation + "’“”‘「」『』（）()[]{}")}
)


def normalize(text: str) -> str:
    """記号を間引き、全角/半角や空白をならして比較用の正規化を行う。"""
    if not text:
        return ""
    t = text.strip().lower()
    t = re.sub(r"\s+", " ", t.translate(_PUNCT_TABLE))
    return t


def char_ngrams(s: str, n: int = 2) -> set[str]:
    """言語非依存の重複検出のための文字n-gram（デフォルト: 2-gram）。"""
    s = s.replace(" ", "")  # 日本語向けに空白を除外
    if len(s) < n:
        return {s} if s else set()
    return {s[i : i + n] for i in range(len(s) - n + 1)}


def jaccard(a: set[str], b: set[str]) -> float:
    if not a or not b:
        return 0.0
    inter = len(a & b)
    if inter == 0:
        return 0.0
    return inter / len(a | b)


def simhash(tokens: Iterable[str]) -> int:
    """シンプルな64bit SimHash。"""
    # 各トークンのハッシュに基づき符号付き重みを積算
    v = [0] * 64
    for tok, cnt in Counter(tokens).items():
        h = hash(tok) & ((1 << 64) - 1)  # 64bit
        w = cnt
        for i in range(64):
            if (h >> i) & 1:
                v[i] += w
            else:
                v[i] -= w
    out = 0
    for i, val in enumerate(v):
        if val >= 0:
            out |= 1 << i
    return out


def hamming(a: int, b: int) -> int:
    return (a ^ b).bit_count()


def load_existing_index() -> list[dict]:
    if INDEX_PATH.exists():
        try:
            return json.loads(INDEX_PATH.read_text(encoding="utf-8"))
        except Exception:
            logger.warning(
                "Failed to read %s; rebuilding index from MD.", INDEX_PATH.name
            )
    return []


def extract_past_texts_from_md(max_items: int | None = None) -> list[str]:
    """tweets_preview.md から本文行だけを抜く（見出しの次の非空行）。"""
    if not MD_PATH.exists():
        return []
    lines = MD_PATH.read_text(encoding="utf-8", errors="ignore").splitlines()
    texts: list[str] = []
    i = 0
    while i < len(lines):
        if lines[i].startswith("# Tweet Preview"):
            # 次の非空行を本文とする
            j = i + 1
            while j < len(lines) and not lines[j].strip():
                j += 1
            if j < len(lines):
                texts.append(lines[j].strip())
                if max_items and len(texts) >= max_items:
                    break
            i = j
        else:
            i += 1
    return texts


def build_index_from_md() -> list[dict]:
    """MDから再構築（初回 or 破損時）。"""
    texts = extract_past_texts_from_md()
    index: list[dict] = []
    for t in texts:
        norm = normalize(t)
        grams = char_ngrams(norm, 2)
        sh = simhash(grams)
        index.append({"norm": norm, "simhash": sh})
    return index


def persist_index(index: list[dict]) -> None:
    INDEX_PATH.write_text(
        json.dumps(index, ensure_ascii=False, indent=2), encoding="utf-8"
    )


def most_similar_info(
    candidate: str, index: list[dict]
) -> tuple[float, int, dict | None]:
    """候補と既存で最も近いものの (jaccard, hamming, item) を返す。"""
    norm = normalize(candidate)
    grams = char_ngrams(norm, 2)
    sh = simhash(grams)
    best = (0.0, 64, None)
    for item in index:
        jac = jaccard(grams, char_ngrams(item["norm"], 2))
        ham = hamming(sh, int(item["simhash"]))
        # 「似ている」度合いの総合指標として jaccard を優先
        if jac > best[0] or (jac == best[0] and ham < best[1]):
            best = (jac, ham, item)
    return best


def extract_block_terms(similar_norms: list[str], top_k: int = 8) -> list[str]:
    """似ていた文からよく出るトークンを抽出してNGワード化（短い文字n-gramベース）。"""
    cnt = Counter()
    for n in similar_norms:
        for g in char_ngrams(n, 2):
            cnt[g] += 1
    return [w for w, _ in cnt.most_common(top_k)]


def add_blocklist_to_prompt(prompt: str, block_terms: list[str]) -> str:
    if not block_terms:
        return prompt
    # Geminiに渡すのは短い回避語のみ（トークン節約）
    return (
        prompt
        + "\n次の短い文字列（話題・表現）に被らない新規性のある内容で書いてください:\n"
        + "、".join(block_terms[:12])
        + "\n"
    )


# === /Dedup additions ===


def main():
    # === 環境変数 ===
    project_id = os.getenv("GOOGLE_CLOUD_PROJECT")
    location = "us-central1"
    gemini_model = os.getenv("GEMINI_MODEL")

    x_api_key = os.getenv("X_API_KEY")
    x_api_secret = os.getenv("X_API_SECRET")
    x_access_token = os.getenv("X_ACCESS_TOKEN")
    x_access_token_secret = os.getenv("X_ACCESS_TOKEN_SECRET")

    # === 入力バリデーション ===
    missing = [k for k, v in {
        "GCP_PROJECT_ID": project_id,
        "GEMINI_MODEL": gemini_model,
        "X_API_KEY": x_api_key,
        "X_API_SECRET": x_api_secret,
        "X_ACCESS_TOKEN": x_access_token,
        "X_ACCESS_TOKEN_SECRET": x_access_token_secret,
    }.items() if not v]
    if missing:
        logger.error("Missing env vars: %s", ", ".join(missing))
        return 2  # 異常終了コード

    # === Dedup: 既存インデックスのロード or 再構築 ===
    index = load_existing_index()
    if not index:
        index = build_index_from_md()
        persist_index(index)
        logger.info("Dedup index initialized from MD. %d items.", len(index))
    else:
        # 追加分があればMDから追補（安全側）
        md_texts = {normalize(t) for t in extract_past_texts_from_md()}
        known = {i["norm"] for i in index}
        new_norms = list(md_texts - known)
        if new_norms:
            for n in new_norms:
                grams = char_ngrams(n, 2)
                index.append({"norm": n, "simhash": simhash(grams)})
            persist_index(index)
            logger.info("Dedup index updated from MD (+%d).", len(new_norms))

    # === Vertex AI 初期化 & 生成 ===
    try:
        vertexai.init(project=project_id, location=location)
        model = GenerativeModel(gemini_model)

        base_prompt = (
            "あなたはXの投稿を生成するAIエージェントです。\n"
            "140文字以内でテクノロジーに関する興味深い事実を投稿してください。\n"
            "冒頭にスクロールを止めるようなフックを入れてください。\n"
            "絵文字は控えめに、具体性と独自性を重視してください。\n"
        )

        # === Dedup: 生成→類似チェック→必要なら回避語を付与して再生成 ===
        MAX_ATTEMPTS = 5
        JACCARD_TH = 0.80  # これ以上は「被り」
        HAMMING_TH = 3  # SimHashが近い（重複）とみなす距離
        block_terms: list[str] = []
        chosen_text = None

        for attempt in range(1, MAX_ATTEMPTS + 1):
            prompt = (
                add_blocklist_to_prompt(base_prompt, block_terms)
                if block_terms
                else base_prompt
            )
            resp = model.generate_content(prompt)
            raw_text = (resp.text or "").strip()
            text = sanitize_and_limit(raw_text, 140)

            jac, ham, nearest = most_similar_info(text, index)
            logger.info("Attempt %d: similarity jac=%.3f ham=%d", attempt, jac, ham)

            if jac < JACCARD_TH and ham > HAMMING_TH:
                chosen_text = text
                break

            # 類似が高い → NGワードを刷新して再試行（過去全文は渡さない）
            sims = []
            if nearest:
                sims.append(nearest["norm"])
            # 余裕があれば他の上位近傍も拾いたいが、コスト/単純さ重視で1件で十分
            block_terms = extract_block_terms(sims, top_k=8)

        if not chosen_text:
            # どうしても被る場合は最後の案を採用しつつ、末尾に微修正（語彙の置換）で被りを緩和
            logger.warning(
                "Could not find a sufficiently novel tweet; applying light mutation."
            )
            norm = normalize(text)
            # ごく簡単な言い換え（英数字・一般語）
            replacements = {
                "ai": "生成系AI",
                "data": "データ",
                "cloud": "クラウド",
                "speed": "性能",
                "fast": "高速",
            }
            mutated = text
            for k, v in replacements.items():
                mutated = re.sub(rf"\b{k}\b", v, mutated, flags=re.IGNORECASE)
            chosen_text = sanitize_and_limit(mutated, 140)

        hashtags = None  # 例: "#AI #Tech"
        citations: list[str] = []  # 例: ["https://example.com/source1"]

        # 送信前プレビューの保存（Markdown追記 & JSON上書き）
        payload = {
            "text": chosen_text,
            "model": gemini_model,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "citations": citations,
            "hashtags": hashtags,
        }
        append_markdown_preview(chosen_text, hashtags, citations, posted_url=None)
        save_payload_json(payload)

        logger.info("Prepared tweet text (%d chars).", len(chosen_text))

    except Exception as e:
        logger.exception("Content generation failed: %s", e)
        return 3

    # === X (Twitter) 投稿 ===
    try:
        client = tweepy.Client(
            consumer_key=x_api_key,
            consumer_secret=x_api_secret,
            access_token=x_access_token,
            access_token_secret=x_access_token_secret,
        )
        res = client.create_tweet(text=chosen_text)
        tweet_id = res.data.get("id")
        tweet_url = f"https://x.com/i/web/status/{tweet_id}" if tweet_id else None

        # 投稿結果をMarkdownに追記、payloadも更新
        payload["posted_at"] = datetime.now(timezone.utc).isoformat()
        payload["tweet_id"] = tweet_id
        payload["tweet_url"] = tweet_url
        save_payload_json(payload)

        logger.info("Tweet posted: %s", tweet_url)

        # === Dedup: 新規投稿をインデックスへ反映 ===
        try:
            norm = normalize(chosen_text)
            grams = char_ngrams(norm, 2)
            new_item = {"norm": norm, "simhash": simhash(grams)}
            index.append(new_item)
            persist_index(index)
            logger.info("Dedup index appended (+1).")
        except Exception as e:
            logger.warning("Failed to update dedup index: %s", e)

        return 0

    except Exception as e:
        logger.exception("Tweet post failed: %s", e)
        return 4

if __name__ == "__main__":
    exit_code = main()
    # タスクスケジューラ用に終了コードを明示
    raise SystemExit(exit_code)