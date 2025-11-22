# -*- coding: utf-8 -*-
"""
Enhanced Tweet Generator Module

Task 1-4のモジュールを統合し、記憶とフィードバックを活用した
強化版ツイート生成システム
"""

import logging
import os
import re
from datetime import datetime, timezone
from typing import Dict, List, Optional, Tuple

import tweepy
from openai import OpenAI

from modules.analyzer import EngagementAnalyzer
from modules.character_manager import CharacterManager
from modules.knowledge_base import KnowledgeBase

logger = logging.getLogger(__name__)


class EnhancedTweetGenerator:
    """
    統合型ツイートジェネレータ

    CharacterManager、KnowledgeBase、EngagementAnalyzer を統合し、
    過去の成功パターンとフォロワーの関心を考慮したツイート生成を行う
    """

    def __init__(
        self,
        character_manager: CharacterManager,
        knowledge_base: KnowledgeBase,
        analyzer: EngagementAnalyzer,
        openai_api_key: Optional[str] = None,
    ):
        """
        EnhancedTweetGeneratorを初期化

        Args:
            character_manager: キャラクター管理インスタンス
            knowledge_base: 知識ベースインスタンス
            analyzer: エンゲージメント分析インスタンス
            openai_api_key: OpenAI APIキー（環境変数から取得する場合はNone）
        """
        self.character_manager = character_manager
        self.knowledge_base = knowledge_base
        self.analyzer = analyzer
        self.openai_api_key = openai_api_key or os.getenv("OPENAI_API_KEY")

        if not self.openai_api_key:
            raise ValueError("OpenAI APIキーが設定されていません")

        self.openai_client = OpenAI(api_key=self.openai_api_key)
        self.model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")

        logger.info("EnhancedTweetGenerator initialized with model: %s", self.model)

    def build_dynamic_prompt(
        self,
        topic: Optional[str] = None,
        use_context: bool = True,
    ) -> str:
        """
        動的プロンプトを構築

        キャラクター設定、高エンゲージメントツイート、
        最近のフォロワー関心、時間帯を考慮したプロンプトを生成

        Args:
            topic: 投稿トピック（指定しない場合は自動選択）
            use_context: コンテキスト情報を使用するか

        Returns:
            構築されたプロンプト
        """
        try:
            # 1. キャラクター設定を読み込み
            character = self.character_manager.get_character()
            logger.info("Character loaded: %s", character.name)

            # 2. コンテキスト情報を収集
            context = {}

            if use_context:
                # 高エンゲージメントツイートを取得
                top_tweets = self.analyzer.get_top_tweets(limit=5, metric="engagement")
                if top_tweets:
                    context["successful_patterns"] = [
                        f"{t['content']} (❤️{t['likes']} RT{t['retweets']})"
                        for t in top_tweets[:3]
                    ]
                    logger.info("Top tweets retrieved: %d", len(top_tweets))

                # 最近の返信トピックを取得
                # クエリなしで全体から検索
                recent_replies = self.knowledge_base.search_similar_replies(
                    query="", top_k=5
                )
                if recent_replies:
                    context["recent_topics"] = [
                        reply["content"] for reply in recent_replies
                    ]
                    logger.info("Recent replies retrieved: %d", len(recent_replies))

                # 最適な投稿時間帯を取得
                optimal_times = self.analyzer.get_optimal_posting_time()
                if optimal_times:
                    context["time_of_day"] = f"最適な投稿時間: {', '.join(optimal_times)}"
                    logger.info("Optimal posting times: %s", optimal_times)

            # トピックの指定
            if topic:
                context["topic"] = topic

            # 3. CharacterManagerのgenerate_tweet_promptを使用
            prompt = self.character_manager.generate_tweet_prompt(context=context)

            logger.info("Dynamic prompt built successfully")
            return prompt

        except Exception as e:
            logger.error("Error building dynamic prompt: %s", e)
            # フォールバック: 基本的なシステムプロンプト
            return self.character_manager.get_system_prompt()

    def generate_tweet_with_context(
        self,
        topic: Optional[str] = None,
        temperature: float = 0.9,
        max_attempts: int = 3,
    ) -> str:
        """
        コンテキストを活用してツイートを生成

        Args:
            topic: 投稿トピック（任意）
            temperature: 生成時の温度パラメータ
            max_attempts: 最大試行回数

        Returns:
            生成されたツイート

        Raises:
            RuntimeError: 生成に失敗した場合
        """
        prompt = self.build_dynamic_prompt(topic=topic, use_context=True)

        for attempt in range(1, max_attempts + 1):
            try:
                logger.info("Generating tweet (attempt %d/%d)", attempt, max_attempts)

                response = self.openai_client.chat.completions.create(
                    model=self.model,
                    messages=[
                        {
                            "role": "system",
                            "content": "あなたは魅力的なX（旧Twitter）投稿を生成する専門家です。"
                                       "指示に従って、純粋な投稿テキストのみを出力してください。",
                        },
                        {"role": "user", "content": prompt},
                    ],
                    temperature=temperature,
                    max_tokens=200,
                )

                tweet = (response.choices[0].message.content or "").strip()

                # 基本的な検証
                if self.validate_tweet(tweet):
                    logger.info("Tweet generated successfully: %s", tweet[:50])
                    return tweet
                else:
                    logger.warning(
                        "Generated tweet failed validation (attempt %d)", attempt
                    )

            except Exception as e:
                logger.error("Error generating tweet (attempt %d): %s", attempt, e)

        raise RuntimeError(
            f"Failed to generate valid tweet after {max_attempts} attempts"
        )

    def validate_tweet(self, tweet: str) -> bool:
        """
        生成されたツイートを検証

        Args:
            tweet: 検証対象のツイート

        Returns:
            検証結果（True=有効、False=無効）
        """
        if not tweet:
            logger.warning("Validation failed: Empty tweet")
            return False

        # 文字数チェック
        character = self.character_manager.get_character()
        max_length = character.constraints.get("max_tweet_length", 140)

        if len(tweet) > max_length:
            logger.warning(
                "Validation failed: Tweet too long (%d > %d)", len(tweet), max_length
            )
            return False

        # 禁止トピックチェック
        avoid_topics = character.constraints.get("avoid_topics", [])
        for topic in avoid_topics:
            if topic.lower() in tweet.lower():
                logger.warning("Validation failed: Contains avoided topic '%s'", topic)
                return False

        # 絵文字の数をチェック
        max_emoji = character.speaking_style.get("max_emoji_per_tweet", 2)
        emoji_pattern = re.compile(
            "["
            "\U0001F600-\U0001F64F"  # 顔文字
            "\U0001F300-\U0001F5FF"  # シンボル & ピクトグラム
            "\U0001F680-\U0001F6FF"  # 交通 & 地図記号
            "\U0001F1E0-\U0001F1FF"  # 国旗
            "\U00002702-\U000027B0"
            "\U000024C2-\U0001F251"
            "]+",
            flags=re.UNICODE,
        )
        emoji_count = len(emoji_pattern.findall(tweet))
        if emoji_count > max_emoji:
            logger.warning(
                "Validation failed: Too many emojis (%d > %d)", emoji_count, max_emoji
            )
            return False

        logger.info("Tweet validation passed")
        return True

    def post_and_record(
        self,
        tweet: str,
        x_credentials: Optional[Dict[str, str]] = None,
        dry_run: bool = False,
    ) -> Dict:
        """
        ツイートを投稿し、結果を記録

        Args:
            tweet: 投稿するツイート
            x_credentials: X API認証情報
                {
                    "api_key": "...",
                    "api_secret": "...",
                    "access_token": "...",
                    "access_token_secret": "..."
                }
            dry_run: Trueの場合、実際には投稿せずに記録のみ行う

        Returns:
            投稿結果の辞書
            {
                "success": bool,
                "tweet_id": str or None,
                "tweet_url": str or None,
                "posted_at": str,
                "error": str or None
            }

        Raises:
            ValueError: 認証情報が不足している場合
        """
        result = {
            "success": False,
            "tweet_id": None,
            "tweet_url": None,
            "posted_at": datetime.now(timezone.utc).isoformat(),
            "error": None,
            "dry_run": dry_run,
        }

        # ドライランモードの場合
        if dry_run:
            logger.info("DRY RUN: Would post tweet: %s", tweet)
            result["success"] = True
            result["tweet_id"] = f"dry_run_{datetime.now().timestamp()}"
            return result

        # 認証情報の取得
        if x_credentials is None:
            x_credentials = {
                "api_key": os.getenv("X_API_KEY"),
                "api_secret": os.getenv("X_API_SECRET"),
                "access_token": os.getenv("X_ACCESS_TOKEN"),
                "access_token_secret": os.getenv("X_ACCESS_TOKEN_SECRET"),
            }

        # 認証情報のチェック
        missing = [k for k, v in x_credentials.items() if not v]
        if missing:
            error_msg = f"X API credentials missing: {', '.join(missing)}"
            logger.error(error_msg)
            result["error"] = error_msg
            raise ValueError(error_msg)

        # 投稿
        try:
            client = tweepy.Client(
                consumer_key=x_credentials["api_key"],
                consumer_secret=x_credentials["api_secret"],
                access_token=x_credentials["access_token"],
                access_token_secret=x_credentials["access_token_secret"],
            )

            response = client.create_tweet(text=tweet)
            tweet_id = response.data.get("id")

            if tweet_id:
                result["success"] = True
                result["tweet_id"] = tweet_id
                result["tweet_url"] = f"https://x.com/i/web/status/{tweet_id}"
                logger.info("Tweet posted successfully: %s", result["tweet_url"])

                # データベースに記録
                try:
                    self.analyzer.add_tweet(
                        tweet_id=str(tweet_id),
                        content=tweet,
                        posted_at=result["posted_at"],
                    )
                    logger.info("Tweet recorded in database")
                except Exception as e:
                    logger.warning("Failed to record tweet in database: %s", e)

            else:
                result["error"] = "No tweet ID returned"
                logger.error("Tweet posting failed: No ID returned")

        except Exception as e:
            result["error"] = str(e)
            logger.exception("Error posting tweet: %s", e)

        return result

    def generate_and_post(
        self,
        topic: Optional[str] = None,
        dry_run: bool = False,
    ) -> Tuple[str, Dict]:
        """
        ツイートを生成して投稿（一連の流れを実行）

        Args:
            topic: 投稿トピック（任意）
            dry_run: Trueの場合、実際には投稿しない

        Returns:
            (生成されたツイート, 投稿結果)のタプル
        """
        # ツイート生成
        tweet = self.generate_tweet_with_context(topic=topic)
        logger.info("Generated tweet: %s", tweet)

        # 投稿と記録
        result = self.post_and_record(tweet, dry_run=dry_run)

        # 成功した場合、知識ベースに追加
        if result["success"] and result["tweet_id"]:
            try:
                self.knowledge_base.add_successful_tweet(
                    tweet_id=result["tweet_id"],
                    content=tweet,
                    engagement={
                        "likes": 0,
                        "retweets": 0,
                        "engagement_rate": 0.0,
                        "posted_at": result["posted_at"],
                    },
                )
                logger.info("Tweet added to knowledge base")
            except Exception as e:
                logger.warning("Failed to add tweet to knowledge base: %s", e)

        return tweet, result

    def get_generation_stats(self) -> Dict:
        """
        生成システムの統計情報を取得

        Returns:
            統計情報の辞書
        """
        analyzer_stats = self.analyzer.get_stats_summary()
        kb_stats = self.knowledge_base.get_stats()
        character = self.character_manager.get_character()

        return {
            "character_name": character.name,
            "total_tweets": analyzer_stats.get("total_tweets", 0),
            "avg_likes": analyzer_stats.get("avg_likes", 0),
            "knowledge_base": kb_stats,
            "model": self.model,
        }


# 使用例
if __name__ == "__main__":
    # ロギング設定
    logging.basicConfig(
        level=logging.INFO,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
    )

    # 各モジュールの初期化
    char_mgr = CharacterManager(config_path="data/character.yaml")
    kb = KnowledgeBase(db_path="data/chroma_db")
    analyzer = EngagementAnalyzer(db_path="data/tweets.db")

    # EnhancedTweetGeneratorの初期化
    generator = EnhancedTweetGenerator(
        character_manager=char_mgr,
        knowledge_base=kb,
        analyzer=analyzer,
    )

    # ツイート生成（ドライラン）
    try:
        tweet, result = generator.generate_and_post(dry_run=True)
        print("\n=== Generated Tweet ===")
        print(tweet)
        print("\n=== Result ===")
        print(result)

        # 統計情報の表示
        print("\n=== Stats ===")
        stats = generator.get_generation_stats()
        for key, value in stats.items():
            print(f"{key}: {value}")

    except Exception as e:
        print(f"Error: {e}")
        logger.exception("Error in main")
