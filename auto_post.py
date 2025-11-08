# -*- coding: utf-8 -*-
# auto_post.py (OpenAI / Gemini 自動切替版)
import json
import logging
import os
import pathlib
import re
import string
from collections import Counter
from datetime import datetime, timezone
from logging.handlers import RotatingFileHandler
from typing import Dict, Iterable, List, Optional, Tuple

import tweepy
from dotenv import load_dotenv
# OpenAI クライアント
from openai import OpenAI

# .env を読み込む
load_dotenv()

# ====== パス設定 ======
BASE_DIR = pathlib.Path(__file__).resolve().parent
OUT_DIR = BASE_DIR / "out_auto"
LOG_DIR = BASE_DIR / "logs_auto"
OUT_DIR.mkdir(parents=True, exist_ok=True)
LOG_DIR.mkdir(parents=True, exist_ok=True)

MD_PATH = OUT_DIR / "tweets_preview.md"
JSON_PATH = OUT_DIR / "tweets_payload.json"
LOG_PATH = LOG_DIR / "auto_post.log"
INDEX_PATH = OUT_DIR / "dedup_index.json"

# ====== ログ設定 ======
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

# ====== 生成バックエンド選択フラグ ======
# 0 = OpenAI, 1 = Gemini, -1 = 自動（環境変数の有無で選択）
PROVIDER_FLAG = int(os.getenv("PROVIDER_FLAG", "-1"))

# ====== 共通ユーティリティ ======
def sanitize_and_limit(text: str, limit: int = 140) -> str:
    if not text:
        return ""
    one_line = " ".join(text.split())
    if len(one_line) > limit:
        logger.warning("Tweet text exceeded %d chars; truncating.", limit)
        one_line = one_line[:limit]
    return one_line

def append_markdown_preview(
    text: str,
    hashtags: Optional[str],
    citations: Optional[List[str]],
    posted_url: Optional[str],
):
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

def save_payload_json(payload: Dict):
    with JSON_PATH.open("w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)

# === Dedup utilities ===
_PUNCT_TABLE = str.maketrans(
    {c: " " for c in (string.punctuation + "’“”‘「」『』（）()[]{}")}
)

def normalize(text: str) -> str:
    if not text:
        return ""
    t = text.strip().lower()
    t = re.sub(r"\s+", " ", t.translate(_PUNCT_TABLE))
    return t

def char_ngrams(s: str, n: int = 2) -> set:
    s = s.replace(" ", "")
    if len(s) < n:
        return {s} if s else set()
    return {s[i : i + n] for i in range(len(s) - n + 1)}

def jaccard(a: set, b: set) -> float:
    if not a or not b:
        return 0.0
    inter = len(a & b)
    if inter == 0:
        return 0.0
    return inter / len(a | b)


def simhash(tokens: Iterable[str]) -> int:
    v = [0] * 64
    for tok, cnt in Counter(tokens).items():
        h = hash(tok) & ((1 << 64) - 1)
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

def load_existing_index() -> List[Dict]:
    if INDEX_PATH.exists():
        try:
            return json.loads(INDEX_PATH.read_text(encoding="utf-8"))
        except Exception:
            logger.warning(
                "Failed to read %s; rebuilding index from MD.", INDEX_PATH.name
            )
    return []

def extract_past_texts_from_md(max_items: Optional[int] = None) -> List[str]:
    if not MD_PATH.exists():
        return []
    lines = MD_PATH.read_text(encoding="utf-8", errors="ignore").splitlines()
    texts: List[str] = []
    i = 0
    while i < len(lines):
        if lines[i].startswith("# Tweet Preview"):
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

def build_index_from_md() -> List[Dict]:
    texts = extract_past_texts_from_md()
    index: List[Dict] = []
    for t in texts:
        norm = normalize(t)
        grams = char_ngrams(norm, 2)
        index.append({"norm": norm, "simhash": simhash(grams)})
    return index

def persist_index(index: List[Dict]) -> None:
    INDEX_PATH.write_text(
        json.dumps(index, ensure_ascii=False, indent=2), encoding="utf-8"
    )

def most_similar_info(
    candidate: str, index: List[Dict]
) -> Tuple[float, int, Optional[Dict]]:
    norm = normalize(candidate)
    grams = char_ngrams(norm, 2)
    sh = simhash(grams)
    best = (0.0, 64, None)
    for item in index:
        jac = jaccard(grams, char_ngrams(item["norm"], 2))
        ham = hamming(sh, int(item["simhash"]))
        if jac > best[0] or (jac == best[0] and ham < best[1]):
            best = (jac, ham, item)
    return best

def extract_block_terms(similar_norms: List[str], top_k: int = 8) -> List[str]:
    cnt = Counter()
    for n in similar_norms:
        for g in char_ngrams(n, 2):
            cnt[g] += 1
    return [w for w, _ in cnt.most_common(top_k)]

def add_blocklist_to_prompt(prompt: str, block_terms: List[str]) -> str:
    if not block_terms:
        return prompt
    return (
        prompt
        + "\n次の短い文字列（話題・表現）に被らない新規性のある内容で書いてください:\n"
        + "、".join(block_terms[:12])
        + "\n"
    )

# ====== 生成バックエンド実装 ======
def generate_with_openai(base_prompt: str, model: str, api_key: str) -> str:
    client = OpenAI(api_key=api_key)
    resp = client.chat.completions.create(
        model=model,
        messages=[
            {
                "role": "system",
                "content": "あなたはXの投稿を生成するAIエージェントです。出力は純テキストのみ。",
            },
            {"role": "user", "content": base_prompt},
        ],
        temperature=0.9,
        max_tokens=200,
    )
    return (resp.choices[0].message.content or "").strip()

def generate_with_gemini(
    base_prompt: str, project_id: str, model_name: str, location: str = "us-central1"
) -> str:
    # 使う時だけ import（環境に vertexai が無い場合でも他経路は動かすため）
    try:
        import vertexai
        from vertexai.preview.generative_models import GenerativeModel
    except Exception as e:
        raise RuntimeError(f"Gemini ライブラリの読み込みに失敗しました: {e}")
    vertexai.init(project=project_id, location=location)
    model = GenerativeModel(model_name)
    resp = model.generate_content(base_prompt)
    return (getattr(resp, "text", "") or "").strip()

def choose_provider() -> Tuple[str, Dict[str, str]]:
    """
    戻り値:
      provider: "openai" or "gemini"
      info:     使用モデルやキーなど（ログ/ペイロード用）
    ルール:
      - PROVIDER_FLAG == 0: OpenAI を優先。キー不足なら Gemini にフォールバック
      - PROVIDER_FLAG == 1: Gemini を優先。設定不足なら OpenAI にフォールバック
      - PROVIDER_FLAG それ以外（例: -1）: 自動（OpenAI → Gemini の順で利用可否を判定）
    """
    # OpenAI 側の設定
    openai_api_key = os.getenv("OPENAI_API_KEY") or ""
    openai_model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
    openai_ready = bool(openai_api_key)

    # Gemini 側の設定
    gcp_project = os.getenv("GOOGLE_CLOUD_PROJECT") or os.getenv("GCP_PROJECT_ID") or ""
    gemini_model = os.getenv("GEMINI_MODEL", "gemini-1.5-pro")
    gemini_ready = bool(gcp_project and gemini_model)

    # 優先度決定
    pref = PROVIDER_FLAG
    order: List[str]
    if pref == 0:
        order = ["openai", "gemini"]
    elif pref == 1:
        order = ["gemini", "openai"]
    else:
        order = ["openai", "gemini"]  # 自動: OpenAI を先に試す

    for p in order:
        if p == "openai" and openai_ready:
            return "openai", {"model": openai_model, "OPENAI_API_KEY": openai_api_key}
        if p == "gemini" and gemini_ready:
            return "gemini", {
                "model": gemini_model,
                "GOOGLE_CLOUD_PROJECT": gcp_project,
            }

    # どちらも不可
    missing_list = []
    if not openai_ready:
        missing_list.append("OPENAI_API_KEY")
    if not gemini_ready:
        missing_list.append("GOOGLE_CLOUD_PROJECT or GEMINI_MODEL")
    raise RuntimeError(
        "どの生成APIも利用可能ではありません。不足: " + ", ".join(missing_list)
    )


def main():
    # === X(Twitter) 認証情報 ===
    x_api_key = os.getenv("X_API_KEY")
    x_api_secret = os.getenv("X_API_SECRET")
    x_access_token = os.getenv("X_ACCESS_TOKEN")
    x_access_token_secret = os.getenv("X_ACCESS_TOKEN_SECRET")

    missing_x = [
        k
        for k, v in {
            "X_API_KEY": x_api_key,
            "X_API_SECRET": x_api_secret,
            "X_ACCESS_TOKEN": x_access_token,
            "X_ACCESS_TOKEN_SECRET": x_access_token_secret,
        }.items()
        if not v
    ]
    if missing_x:
        logger.error("Missing env vars for X: %s", ", ".join(missing_x))
        return 2

    # === Dedup index 準備 ===
    index = load_existing_index()
    if not index:
        index = build_index_from_md()
        persist_index(index)
        logger.info("Dedup index initialized from MD. %d items.", len(index))
    else:
        md_texts = {normalize(t) for t in extract_past_texts_from_md()}
        known = {i["norm"] for i in index}
        new_norms = list(md_texts - known)
        if new_norms:
            for n in new_norms:
                grams = char_ngrams(n, 2)
                index.append({"norm": n, "simhash": simhash(grams)})
            persist_index(index)
            logger.info("Dedup index updated from MD (+%d).", len(new_norms))

    # === 生成 ===
    try:
        provider, info = choose_provider()
        base_prompt = (
            "140文字以内でテクノロジーに関する興味深い事実を投稿してください。\n"
            "冒頭にスクロールを止めるようなフックを入れてください。\n"
            "絵文字は控えめに、具体性と独自性を重視してください。\n"
        )

        MAX_ATTEMPTS = 5
        JACCARD_TH = 0.80
        HAMMING_TH = 3
        block_terms: List[str] = []
        chosen_text = ""
        last_text = ""

        for attempt in range(1, MAX_ATTEMPTS + 1):
            prompt = (
                add_blocklist_to_prompt(base_prompt, block_terms)
                if block_terms
                else base_prompt
            )

            if provider == "openai":
                raw = generate_with_openai(
                    prompt, info["model"], info["OPENAI_API_KEY"]
                )
            else:
                raw = generate_with_gemini(
                    prompt, info["GOOGLE_CLOUD_PROJECT"], info["model"]
                )

            last_text = sanitize_and_limit(raw, 140)

            jac, ham, nearest = most_similar_info(last_text, index)
            logger.info("Attempt %d [%s]: jac=%.3f ham=%d", attempt, provider, jac, ham)

            if jac < JACCARD_TH and ham > HAMMING_TH:
                chosen_text = last_text
                break

            sims = []
            if nearest:
                sims.append(nearest["norm"])
            block_terms = extract_block_terms(sims, top_k=8)

        if not chosen_text:
            logger.warning("Novel candidate not found; applying light mutation.")
            text = last_text or ""
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

        hashtags = None
        citations: List[str] = []

        payload = {
            "text": chosen_text,
            "provider": provider,
            "model": info["model"],
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "citations": citations,
            "hashtags": hashtags,
        }
        append_markdown_preview(chosen_text, hashtags, citations, posted_url=None)
        save_payload_json(payload)

        logger.info(
            "Prepared tweet text (%d chars) via %s/%s.",
            len(chosen_text),
            provider,
            info["model"],
        )

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

        payload["posted_at"] = datetime.now(timezone.utc).isoformat()
        payload["tweet_id"] = tweet_id
        payload["tweet_url"] = tweet_url
        save_payload_json(payload)
        append_markdown_preview(chosen_text, hashtags, citations, posted_url=tweet_url)

        logger.info("Tweet posted: %s", tweet_url)

        # Dedup 反映
        try:
            norm = normalize(chosen_text)
            grams = char_ngrams(norm, 2)
            index.append({"norm": norm, "simhash": simhash(grams)})
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
    raise SystemExit(exit_code)