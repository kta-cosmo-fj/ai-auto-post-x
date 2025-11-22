#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
auto_post_v2.py - Enhanced Tweet Auto Posting System

Task 1-4のモジュールを統合した強化版自動投稿システム。
EnhancedTweetGeneratorを使用し、キャラクター設定、過去の成功パターン、
フォロワーの関心を考慮した高度なツイート生成を行う。
"""

import json
import logging
import os
import pathlib
import sys
from datetime import datetime, timezone
from logging.handlers import RotatingFileHandler
from typing import Dict, Optional

from dotenv import load_dotenv

from modules.analyzer import EngagementAnalyzer
from modules.character_manager import CharacterManager
from modules.enhanced_generator import EnhancedTweetGenerator
from modules.knowledge_base import KnowledgeBase

# .env を読み込む
load_dotenv()

# ====== パス設定 ======
BASE_DIR = pathlib.Path(__file__).resolve().parent
OUT_DIR = BASE_DIR / "out_auto"
LOG_DIR = BASE_DIR / "logs_auto"
DATA_DIR = BASE_DIR / "data"

# ディレクトリ作成
OUT_DIR.mkdir(parents=True, exist_ok=True)
LOG_DIR.mkdir(parents=True, exist_ok=True)
DATA_DIR.mkdir(parents=True, exist_ok=True)

# ファイルパス
MD_PATH = OUT_DIR / "tweets_preview.md"
JSON_PATH = OUT_DIR / "tweets_payload.json"
LOG_PATH = LOG_DIR / "auto_post_v2.log"

# データファイルパス
CHARACTER_CONFIG = DATA_DIR / "character.yaml"
TWEETS_DB = DATA_DIR / "tweets.db"
CHROMA_DB = DATA_DIR / "chroma_db"

# ====== ログ設定 ======
logger = logging.getLogger("auto_post_v2")
logger.setLevel(logging.INFO)

# ファイルハンドラ
file_handler = RotatingFileHandler(
    LOG_PATH, maxBytes=1_000_000, backupCount=5, encoding="utf-8"
)
file_formatter = logging.Formatter(
    "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S"
)
file_handler.setFormatter(file_formatter)
logger.addHandler(file_handler)

# コンソールハンドラ
console_handler = logging.StreamHandler()
console_formatter = logging.Formatter(
    "%(asctime)s [%(levelname)s] %(message)s",
    datefmt="%H:%M:%S"
)
console_handler.setFormatter(console_formatter)
logger.addHandler(console_handler)


def append_markdown_preview(
    text: str,
    metadata: Dict,
    posted_url: Optional[str] = None,
) -> None:
    """投稿内容をMarkdownファイルに追記する"""
    ts = datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")
    with MD_PATH.open("a", encoding="utf-8") as f:
        f.write(f"\n\n## Tweet Preview ({ts})\n\n")
        f.write(f"**Content:**\n{text}\n\n")

        if metadata:
            f.write("**Metadata:**\n")
            for key, value in metadata.items():
                f.write(f"- {key}: {value}\n")
            f.write("\n")

        if posted_url:
            f.write(f"**Posted:** {posted_url}\n")


def save_payload_json(payload: Dict) -> None:
    """投稿データをJSONファイルに保存する"""
    with JSON_PATH.open("w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)


def check_dependencies() -> Dict[str, bool]:
    """
    必要な設定ファイルと環境変数をチェック

    Returns:
        チェック結果の辞書
    """
    checks = {
        "character_config": CHARACTER_CONFIG.exists(),
        "openai_api_key": bool(os.getenv("OPENAI_API_KEY")),
        "x_api_key": bool(os.getenv("X_API_KEY")),
        "x_api_secret": bool(os.getenv("X_API_SECRET")),
        "x_access_token": bool(os.getenv("X_ACCESS_TOKEN")),
        "x_access_token_secret": bool(os.getenv("X_ACCESS_TOKEN_SECRET")),
    }

    return checks


def initialize_modules() -> tuple:
    """
    必要なモジュールを初期化

    Returns:
        (CharacterManager, KnowledgeBase, EngagementAnalyzer)のタプル

    Raises:
        RuntimeError: 初期化に失敗した場合
    """
    try:
        # CharacterManagerの初期化
        logger.info("Initializing CharacterManager...")
        char_mgr = CharacterManager(config_path=str(CHARACTER_CONFIG))
        character = char_mgr.get_character()
        logger.info("Character loaded: %s", character.name)

        # KnowledgeBaseの初期化
        logger.info("Initializing KnowledgeBase...")
        kb = KnowledgeBase(db_path=str(CHROMA_DB))
        kb_stats = kb.get_stats()
        logger.info(
            "KnowledgeBase loaded: %d replies, %d tweets",
            kb_stats["replies_count"],
            kb_stats["tweets_count"],
        )

        # EngagementAnalyzerの初期化
        logger.info("Initializing EngagementAnalyzer...")
        analyzer = EngagementAnalyzer(db_path=str(TWEETS_DB))
        analyzer_stats = analyzer.get_stats_summary()
        logger.info(
            "EngagementAnalyzer loaded: %d total tweets",
            analyzer_stats["total_tweets"],
        )

        return char_mgr, kb, analyzer

    except Exception as e:
        logger.exception("Failed to initialize modules")
        raise RuntimeError(f"Module initialization failed: {e}")


def main() -> int:
    """
    メイン処理：強化版AI投稿を生成してXに投稿する

    Returns:
        int: 終了コード（0=成功、1=依存関係エラー、2=初期化エラー、3=生成エラー、4=投稿エラー）
    """
    logger.info("=" * 60)
    logger.info("Auto Post v2 - Enhanced Tweet Generator")
    logger.info("=" * 60)

    # === 依存関係チェック ===
    logger.info("Checking dependencies...")
    checks = check_dependencies()

    missing = [k for k, v in checks.items() if not v]
    if missing:
        logger.error("Missing dependencies: %s", ", ".join(missing))
        logger.error("Please check your .env file and data/character.yaml")
        return 1

    logger.info("✓ All dependencies satisfied")

    # === モジュール初期化 ===
    try:
        char_mgr, kb, analyzer = initialize_modules()
    except Exception as e:
        logger.error("Initialization failed: %s", e)
        return 2

    # === EnhancedTweetGeneratorの初期化 ===
    try:
        logger.info("Initializing EnhancedTweetGenerator...")
        generator = EnhancedTweetGenerator(
            character_manager=char_mgr,
            knowledge_base=kb,
            analyzer=analyzer,
        )
        logger.info("✓ EnhancedTweetGenerator initialized")
    except Exception as e:
        logger.exception("Failed to initialize EnhancedTweetGenerator")
        return 2

    # === 統計情報の表示 ===
    try:
        stats = generator.get_generation_stats()
        logger.info("Current Stats:")
        logger.info("  Character: %s", stats["character_name"])
        logger.info("  Total Tweets: %d", stats["total_tweets"])
        logger.info("  Avg Likes: %.2f", stats["avg_likes"])
        logger.info("  Model: %s", stats["model"])
    except Exception as e:
        logger.warning("Failed to retrieve stats: %s", e)

    # === ツイート生成 ===
    try:
        logger.info("=" * 60)
        logger.info("Generating tweet...")

        # トピックの指定（環境変数から取得可能）
        topic = os.getenv("TWEET_TOPIC")
        if topic:
            logger.info("Using specified topic: %s", topic)

        # ドライランモードのチェック
        dry_run = os.getenv("DRY_RUN", "false").lower() == "true"
        if dry_run:
            logger.info("DRY RUN MODE: Will not actually post to X")

        # ツイート生成と投稿
        tweet, result = generator.generate_and_post(
            topic=topic,
            dry_run=dry_run,
        )

        logger.info("=" * 60)
        logger.info("Generated Tweet:")
        logger.info("-" * 60)
        logger.info(tweet)
        logger.info("-" * 60)

        # メタデータの準備
        metadata = {
            "character": char_mgr.get_character().name,
            "model": generator.model,
            "generated_at": result["posted_at"],
            "topic": topic or "auto",
        }

        # 結果の保存
        posted_url = result.get("tweet_url")
        append_markdown_preview(tweet, metadata, posted_url)

        payload = {
            "text": tweet,
            "metadata": metadata,
            "result": result,
        }
        save_payload_json(payload)

        # 結果の表示
        if result["success"]:
            logger.info("✓ Tweet posted successfully!")
            if posted_url:
                logger.info("URL: %s", posted_url)
            return 0
        else:
            error = result.get("error", "Unknown error")
            logger.error("✗ Tweet posting failed: %s", error)
            return 4

    except Exception as e:
        logger.exception("Tweet generation/posting failed: %s", e)
        return 3


if __name__ == "__main__":
    try:
        exit_code = main()
        logger.info("=" * 60)
        logger.info("Exit code: %d", exit_code)
        sys.exit(exit_code)
    except KeyboardInterrupt:
        logger.info("\nInterrupted by user")
        sys.exit(130)
    except Exception as e:
        logger.exception("Unexpected error: %s", e)
        sys.exit(1)
