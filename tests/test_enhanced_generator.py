# -*- coding: utf-8 -*-
"""
Tests for Enhanced Tweet Generator

EnhancedTweetGeneratorの統合テスト
"""

import os
import tempfile
import unittest
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

from modules.analyzer import EngagementAnalyzer
from modules.character_manager import CharacterManager
from modules.enhanced_generator import EnhancedTweetGenerator
from modules.knowledge_base import KnowledgeBase


class TestEnhancedTweetGenerator(unittest.TestCase):
    """EnhancedTweetGenerator のテスト"""

    def setUp(self):
        """テストのセットアップ"""
        # 一時ディレクトリの作成
        self.temp_dir = tempfile.mkdtemp()
        self.temp_path = Path(self.temp_dir)

        # テスト用のキャラクター設定ファイル
        self.character_config = self.temp_path / "character.yaml"
        self.character_config.write_text("""
character:
  name: "テストBot"
  personality: "フレンドリーで知識豊富なAIアシスタント"
  tone: "親しみやすく、わかりやすい言葉で説明する"
  interests:
    - "AI技術"
    - "プログラミング"
    - "データサイエンス"
  knowledge_level: "専門的な知識を持ちながら、初心者にも理解しやすく説明できる"
  speaking_style:
    sentence_ending:
      - "です"
      - "ます"
    emoji_frequency: "moderate"
    max_emoji_per_tweet: 2
    hashtag_usage: true
  constraints:
    max_tweet_length: 140
    preferred_time_slots:
      - "09:00-12:00"
      - "15:00-18:00"
    avoid_topics:
      - "政治"
      - "宗教"
""", encoding="utf-8")

        # テスト用のデータベースパス
        self.tweets_db = self.temp_path / "tweets.db"
        self.chroma_db = self.temp_path / "chroma_db"

        # モジュールの初期化
        self.char_mgr = CharacterManager(config_path=str(self.character_config))
        self.analyzer = EngagementAnalyzer(db_path=str(self.tweets_db))
        self.kb = KnowledgeBase(db_path=str(self.chroma_db))

        # テストデータの準備
        self._setup_test_data()

    def tearDown(self):
        """テストのクリーンアップ"""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    def _setup_test_data(self):
        """テストデータのセットアップ"""
        # サンプルツイートをデータベースに追加
        sample_tweets = [
            {
                "tweet_id": "1",
                "content": "AIの最新トレンドについて調べてみました。機械学習の進化が加速しています。",
                "likes": 150,
                "retweets": 45,
                "impressions": 1000,
            },
            {
                "tweet_id": "2",
                "content": "Pythonでデータ分析を始めるなら、pandasとmatplotlibがおすすめです。",
                "likes": 120,
                "retweets": 30,
                "impressions": 800,
            },
            {
                "tweet_id": "3",
                "content": "今日の開発は順調。新しいアルゴリズムを実装できました。",
                "likes": 80,
                "retweets": 20,
                "impressions": 500,
            },
        ]

        for tweet in sample_tweets:
            self.analyzer.add_tweet(**tweet)
            self.kb.add_successful_tweet(
                tweet_id=tweet["tweet_id"],
                content=tweet["content"],
                engagement={
                    "likes": tweet["likes"],
                    "retweets": tweet["retweets"],
                    "engagement_rate": (tweet["likes"] + tweet["retweets"]) / tweet["impressions"],
                },
            )

        # サンプル返信を知識ベースに追加
        sample_replies = [
            {
                "reply_id": "r1",
                "content": "AIについてもっと詳しく教えてください",
                "metadata": {"author": "user1", "sentiment": "positive"},
            },
            {
                "reply_id": "r2",
                "content": "プログラミング学習のコツは何ですか？",
                "metadata": {"author": "user2", "sentiment": "neutral"},
            },
        ]

        for reply in sample_replies:
            self.kb.add_reply(**reply)

    @patch.dict(os.environ, {"OPENAI_API_KEY": "test-key"})
    def test_initialization(self):
        """初期化のテスト"""
        generator = EnhancedTweetGenerator(
            character_manager=self.char_mgr,
            knowledge_base=self.kb,
            analyzer=self.analyzer,
            openai_api_key="test-key",
        )

        self.assertIsNotNone(generator)
        self.assertEqual(generator.character_manager, self.char_mgr)
        self.assertEqual(generator.knowledge_base, self.kb)
        self.assertEqual(generator.analyzer, self.analyzer)

    @patch.dict(os.environ, {"OPENAI_API_KEY": "test-key"})
    def test_build_dynamic_prompt(self):
        """動的プロンプト生成のテスト"""
        generator = EnhancedTweetGenerator(
            character_manager=self.char_mgr,
            knowledge_base=self.kb,
            analyzer=self.analyzer,
            openai_api_key="test-key",
        )

        # コンテキストありでプロンプト生成
        prompt = generator.build_dynamic_prompt(topic="AI技術", use_context=True)

        self.assertIsInstance(prompt, str)
        self.assertGreater(len(prompt), 0)
        self.assertIn("テストBot", prompt)

        # コンテキストなしでプロンプト生成
        prompt_no_context = generator.build_dynamic_prompt(use_context=False)
        self.assertIsInstance(prompt_no_context, str)

    @patch.dict(os.environ, {"OPENAI_API_KEY": "test-key"})
    def test_validate_tweet(self):
        """ツイート検証のテスト"""
        generator = EnhancedTweetGenerator(
            character_manager=self.char_mgr,
            knowledge_base=self.kb,
            analyzer=self.analyzer,
            openai_api_key="test-key",
        )

        # 有効なツイート
        valid_tweet = "今日はAI技術について学びました。とても興味深いです。"
        self.assertTrue(generator.validate_tweet(valid_tweet))

        # 空のツイート
        self.assertFalse(generator.validate_tweet(""))

        # 長すぎるツイート
        long_tweet = "あ" * 150
        self.assertFalse(generator.validate_tweet(long_tweet))

        # 禁止トピックを含むツイート
        banned_tweet = "政治について議論しましょう"
        self.assertFalse(generator.validate_tweet(banned_tweet))

        # 絵文字が多すぎるツイート
        emoji_tweet = "テスト😀😁😂🤣😃"
        self.assertFalse(generator.validate_tweet(emoji_tweet))

    @patch.dict(os.environ, {"OPENAI_API_KEY": "test-key"})
    @patch("modules.enhanced_generator.OpenAI")
    def test_generate_tweet_with_context(self, mock_openai):
        """コンテキストを活用したツイート生成のテスト"""
        # OpenAI APIのモック
        mock_response = Mock()
        mock_response.choices = [
            Mock(message=Mock(content="今日はAI技術について学びました。"))
        ]
        mock_client = Mock()
        mock_client.chat.completions.create.return_value = mock_response
        mock_openai.return_value = mock_client

        generator = EnhancedTweetGenerator(
            character_manager=self.char_mgr,
            knowledge_base=self.kb,
            analyzer=self.analyzer,
            openai_api_key="test-key",
        )

        # ツイート生成
        tweet = generator.generate_tweet_with_context(topic="AI技術")

        self.assertIsInstance(tweet, str)
        self.assertGreater(len(tweet), 0)
        mock_client.chat.completions.create.assert_called()

    @patch.dict(os.environ, {"OPENAI_API_KEY": "test-key"})
    def test_post_and_record_dry_run(self):
        """ドライランモードでの投稿テスト"""
        generator = EnhancedTweetGenerator(
            character_manager=self.char_mgr,
            knowledge_base=self.kb,
            analyzer=self.analyzer,
            openai_api_key="test-key",
        )

        tweet = "テスト投稿です。"
        result = generator.post_and_record(tweet, dry_run=True)

        self.assertTrue(result["success"])
        self.assertTrue(result["dry_run"])
        self.assertIsNotNone(result["tweet_id"])

    @patch.dict(os.environ, {
        "OPENAI_API_KEY": "test-key",
        "X_API_KEY": "x-key",
        "X_API_SECRET": "x-secret",
        "X_ACCESS_TOKEN": "x-token",
        "X_ACCESS_TOKEN_SECRET": "x-token-secret",
    })
    @patch("modules.enhanced_generator.tweepy.Client")
    def test_post_and_record_real(self, mock_tweepy_client):
        """実際の投稿のテスト（モック）"""
        # Tweepy APIのモック
        mock_response = Mock()
        mock_response.data = {"id": "123456789"}
        mock_client_instance = Mock()
        mock_client_instance.create_tweet.return_value = mock_response
        mock_tweepy_client.return_value = mock_client_instance

        generator = EnhancedTweetGenerator(
            character_manager=self.char_mgr,
            knowledge_base=self.kb,
            analyzer=self.analyzer,
            openai_api_key="test-key",
        )

        tweet = "テスト投稿です。"
        result = generator.post_and_record(tweet, dry_run=False)

        self.assertTrue(result["success"])
        self.assertEqual(result["tweet_id"], "123456789")
        self.assertIn("123456789", result["tweet_url"])
        mock_client_instance.create_tweet.assert_called_once_with(text=tweet)

    @patch.dict(os.environ, {"OPENAI_API_KEY": "test-key"})
    def test_get_generation_stats(self):
        """統計情報取得のテスト"""
        generator = EnhancedTweetGenerator(
            character_manager=self.char_mgr,
            knowledge_base=self.kb,
            analyzer=self.analyzer,
            openai_api_key="test-key",
        )

        stats = generator.get_generation_stats()

        self.assertIsInstance(stats, dict)
        self.assertIn("character_name", stats)
        self.assertIn("total_tweets", stats)
        self.assertIn("avg_likes", stats)
        self.assertIn("knowledge_base", stats)
        self.assertIn("model", stats)

        self.assertEqual(stats["character_name"], "テストBot")
        self.assertEqual(stats["total_tweets"], 3)

    @patch.dict(os.environ, {"OPENAI_API_KEY": "test-key"})
    @patch("modules.enhanced_generator.OpenAI")
    @patch("modules.enhanced_generator.tweepy.Client")
    def test_generate_and_post(self, mock_tweepy, mock_openai):
        """ツイート生成と投稿の統合テスト"""
        # OpenAI APIのモック
        mock_response = Mock()
        mock_response.choices = [
            Mock(message=Mock(content="AI技術の進化が素晴らしいです。"))
        ]
        mock_openai_client = Mock()
        mock_openai_client.chat.completions.create.return_value = mock_response
        mock_openai.return_value = mock_openai_client

        # Tweepy APIのモック
        mock_tweet_response = Mock()
        mock_tweet_response.data = {"id": "987654321"}
        mock_tweepy_instance = Mock()
        mock_tweepy_instance.create_tweet.return_value = mock_tweet_response
        mock_tweepy.return_value = mock_tweepy_instance

        generator = EnhancedTweetGenerator(
            character_manager=self.char_mgr,
            knowledge_base=self.kb,
            analyzer=self.analyzer,
            openai_api_key="test-key",
        )

        # ドライランで実行
        tweet, result = generator.generate_and_post(topic="AI", dry_run=True)

        self.assertIsInstance(tweet, str)
        self.assertGreater(len(tweet), 0)
        self.assertTrue(result["success"])


class TestEnhancedGeneratorIntegration(unittest.TestCase):
    """統合テスト"""

    def setUp(self):
        """テストのセットアップ"""
        self.temp_dir = tempfile.mkdtemp()
        self.temp_path = Path(self.temp_dir)

        # テスト用設定
        self.character_config = self.temp_path / "character.yaml"
        self.character_config.write_text("""
character:
  name: "統合テストBot"
  personality: "テスト用のBot"
  tone: "テスト"
  interests: ["テスト"]
  knowledge_level: "テストレベル"
  constraints:
    max_tweet_length: 140
""", encoding="utf-8")

        self.tweets_db = self.temp_path / "tweets.db"
        self.chroma_db = self.temp_path / "chroma_db"

    def tearDown(self):
        """テストのクリーンアップ"""
        import shutil
        shutil.rmtree(self.temp_dir, ignore_errors=True)

    @patch.dict(os.environ, {"OPENAI_API_KEY": "test-key"})
    def test_full_workflow(self):
        """完全なワークフローのテスト"""
        # モジュールの初期化
        char_mgr = CharacterManager(config_path=str(self.character_config))
        kb = KnowledgeBase(db_path=str(self.chroma_db))
        analyzer = EngagementAnalyzer(db_path=str(self.tweets_db))

        # ジェネレータの初期化
        generator = EnhancedTweetGenerator(
            character_manager=char_mgr,
            knowledge_base=kb,
            analyzer=analyzer,
            openai_api_key="test-key",
        )

        # 統計情報の取得
        stats = generator.get_generation_stats()
        self.assertEqual(stats["character_name"], "統合テストBot")

        # プロンプトの生成
        prompt = generator.build_dynamic_prompt(use_context=False)
        self.assertIn("統合テストBot", prompt)


if __name__ == "__main__":
    unittest.main()
