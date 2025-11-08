# -*- coding: utf-8 -*-
# auto_post.py
import json
import logging
import os
import pathlib
from datetime import datetime, timezone
from logging.handlers import RotatingFileHandler

import tweepy
import vertexai
from dotenv import load_dotenv
from vertexai.preview.generative_models import GenerativeModel

# .envファイルを読み込む
load_dotenv()
# ====== パス設定 ======
BASE_DIR = pathlib.Path(__file__).resolve().parent
OUT_DIR = BASE_DIR / "out_auto"
LOG_DIR = BASE_DIR / "logs"
OUT_DIR.mkdir(parents=True, exist_ok=True)
LOG_DIR.mkdir(parents=True, exist_ok=True)

MD_PATH = OUT_DIR / "tweets_preview.md"       # 追記されるMarkdown
JSON_PATH = OUT_DIR / "tweets_payload.json"   # 常に最新で上書き
LOG_PATH = LOG_DIR / "auto_post.log"          # ローテーションログ

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

    # === Vertex AI 初期化 & 生成 ===
    try:
        vertexai.init(project=project_id, location=location)
        model = GenerativeModel(gemini_model)

        prompt = (
            "あなたはXの投稿を生成するAIエージェントです。\n"
            "140文字以内でテクノロジーに関する興味深い事実を投稿してください。\n"
            "冒頭にスクロールを止めるようなフックを入れてください。\n"
        )
        resp = model.generate_content(prompt)
        raw_text = (resp.text or "").strip()
        text = sanitize_and_limit(raw_text, 140)

        # ここで独自にハッシュタグや出典URLを組み立てたい場合は編集
        hashtags = None  # 例: "#AI #Tech"
        citations: list[str] = []  # 例: ["https://example.com/source1"]

        # 送信前プレビューの保存（Markdown追記 & JSON上書き）
        payload = {
            "text": text,
            "model": gemini_model,
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "citations": citations,
            "hashtags": hashtags,
        }
        append_markdown_preview(text, hashtags, citations, posted_url=None)
        save_payload_json(payload)

        logger.info("Prepared tweet text (%d chars).", len(text))

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
        res = client.create_tweet(text=text)
        tweet_id = res.data.get("id")
        # 汎用の閲覧URL（ユーザー名が不明でも動く形式）
        tweet_url = f"https://x.com/i/web/status/{tweet_id}" if tweet_id else None

        # 投稿結果をMarkdownに追記、payloadも更新
        # append_markdown_preview(text, hashtags, citations, posted_url=tweet_url)
        payload["posted_at"] = datetime.now(timezone.utc).isoformat()
        payload["tweet_id"] = tweet_id
        payload["tweet_url"] = tweet_url
        save_payload_json(payload)

        logger.info("Tweet posted: %s", tweet_url)
        return 0

    except Exception as e:
        logger.exception("Tweet post failed: %s", e)
        return 4

if __name__ == "__main__":
    exit_code = main()
    # タスクスケジューラ用に終了コードを明示
    raise SystemExit(exit_code)