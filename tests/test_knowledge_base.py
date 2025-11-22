"""Knowledge Base のユニットテスト"""

import os
import sys
import unittest
import tempfile
import shutil
from datetime import datetime

# プロジェクトルートをパスに追加
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from modules.knowledge_base import KnowledgeBase


class TestKnowledgeBase(unittest.TestCase):
    """KnowledgeBaseクラスのテストケース"""

    def setUp(self):
        """各テストの前に実行される準備処理"""
        # 一時ディレクトリを作成
        self.test_db_path = tempfile.mkdtemp()
        self.kb = KnowledgeBase(db_path=self.test_db_path)

    def tearDown(self):
        """各テストの後に実行されるクリーンアップ処理"""
        # 一時ディレクトリを削除
        if os.path.exists(self.test_db_path):
            shutil.rmtree(self.test_db_path)

    def test_initialization(self):
        """初期化テスト"""
        self.assertIsNotNone(self.kb)
        self.assertIsNotNone(self.kb.client)
        self.assertIsNotNone(self.kb.embedding_model)
        self.assertIsNotNone(self.kb.replies_collection)
        self.assertIsNotNone(self.kb.tweets_collection)

    def test_add_reply(self):
        """返信追加のテスト"""
        reply_id = "test_reply_001"
        content = "これはテスト返信です。"
        metadata = {
            "author": "test_user",
            "tweet_id": "test_tweet_001",
            "replied_at": datetime.now().isoformat(),
            "sentiment": "positive"
        }

        # 返信を追加
        self.kb.add_reply(reply_id, content, metadata)

        # 統計情報を確認
        stats = self.kb.get_stats()
        self.assertEqual(stats["replies_count"], 1)
        self.assertEqual(stats["tweets_count"], 0)

    def test_add_successful_tweet(self):
        """成功したツイート追加のテスト"""
        tweet_id = "test_tweet_success_001"
        content = "これはテストツイートです。"
        engagement = {
            "likes": 100,
            "retweets": 50,
            "engagement_rate": 0.15,
            "posted_at": datetime.now().isoformat()
        }

        # ツイートを追加
        self.kb.add_successful_tweet(tweet_id, content, engagement)

        # 統計情報を確認
        stats = self.kb.get_stats()
        self.assertEqual(stats["replies_count"], 0)
        self.assertEqual(stats["tweets_count"], 1)

    def test_search_similar_replies(self):
        """類似返信検索のテスト"""
        # テストデータを追加
        test_replies = [
            ("reply_001", "機械学習について教えてください", {"author": "user1"}),
            ("reply_002", "Pythonのデータ処理方法", {"author": "user2"}),
            ("reply_003", "AIの倫理について", {"author": "user3"}),
        ]

        for reply_id, content, metadata in test_replies:
            self.kb.add_reply(reply_id, content, metadata)

        # 検索を実行
        results = self.kb.search_similar_replies("機械学習", top_k=2)

        # 結果を検証
        self.assertIsInstance(results, list)
        self.assertGreater(len(results), 0)
        self.assertLessEqual(len(results), 2)

        # 最初の結果が最も関連性が高いことを確認
        if results:
            self.assertIn("content", results[0])
            self.assertIn("metadata", results[0])

    def test_search_similar_tweets(self):
        """類似ツイート検索のテスト"""
        # テストデータを追加
        test_tweets = [
            ("tweet_001", "AIの最新研究について", {"likes": 100}),
            ("tweet_002", "機械学習モデルの比較", {"likes": 150}),
            ("tweet_003", "データサイエンスの基礎", {"likes": 200}),
        ]

        for tweet_id, content, engagement in test_tweets:
            self.kb.add_successful_tweet(tweet_id, content, engagement)

        # 検索を実行
        results = self.kb.search_similar_tweets("AI", top_k=2)

        # 結果を検証
        self.assertIsInstance(results, list)
        self.assertGreater(len(results), 0)
        self.assertLessEqual(len(results), 2)

    def test_get_context_for_generation(self):
        """文脈生成のテスト"""
        # 返信を追加
        self.kb.add_reply(
            "reply_001",
            "機械学習について質問です",
            {"author": "user1", "sentiment": "neutral"}
        )

        # ツイートを追加
        self.kb.add_successful_tweet(
            "tweet_001",
            "AIの最新トレンド",
            {"likes": 100, "retweets": 50}
        )

        # 文脈を取得
        context = self.kb.get_context_for_generation("機械学習")

        # 結果を検証
        self.assertIsInstance(context, str)
        # データがある場合は空でないはず
        if self.kb.get_stats()["total_count"] > 0:
            self.assertGreater(len(context), 0)

    def test_empty_search(self):
        """空のデータベースでの検索テスト"""
        # データが空の状態で検索
        results = self.kb.search_similar_replies("test query")
        self.assertEqual(results, [])

        results = self.kb.search_similar_tweets("test query")
        self.assertEqual(results, [])

    def test_get_stats(self):
        """統計情報取得のテスト"""
        # 初期状態
        stats = self.kb.get_stats()
        self.assertEqual(stats["replies_count"], 0)
        self.assertEqual(stats["tweets_count"], 0)
        self.assertEqual(stats["total_count"], 0)

        # データ追加後
        self.kb.add_reply("r1", "test", {})
        self.kb.add_successful_tweet("t1", "test", {})

        stats = self.kb.get_stats()
        self.assertEqual(stats["replies_count"], 1)
        self.assertEqual(stats["tweets_count"], 1)
        self.assertEqual(stats["total_count"], 2)

    def test_update_existing_reply(self):
        """既存の返信更新のテスト"""
        reply_id = "reply_update_test"
        content_v1 = "最初の内容"
        content_v2 = "更新された内容"

        # 最初の追加
        self.kb.add_reply(reply_id, content_v1, {"author": "user1"})
        stats_v1 = self.kb.get_stats()

        # 同じIDで再度追加（更新）
        self.kb.add_reply(reply_id, content_v2, {"author": "user1"})
        stats_v2 = self.kb.get_stats()

        # カウントが増えていないことを確認
        self.assertEqual(stats_v1["replies_count"], stats_v2["replies_count"])

    def test_reset(self):
        """リセット機能のテスト"""
        # データを追加
        self.kb.add_reply("r1", "test reply", {})
        self.kb.add_successful_tweet("t1", "test tweet", {})

        # データが存在することを確認
        stats_before = self.kb.get_stats()
        self.assertGreater(stats_before["total_count"], 0)

        # リセット
        self.kb.reset()

        # データが削除されたことを確認
        stats_after = self.kb.get_stats()
        self.assertEqual(stats_after["replies_count"], 0)
        self.assertEqual(stats_after["tweets_count"], 0)


class TestKnowledgeBaseIntegration(unittest.TestCase):
    """KnowledgeBaseの統合テスト"""

    def setUp(self):
        """テスト準備"""
        self.test_db_path = tempfile.mkdtemp()
        self.kb = KnowledgeBase(db_path=self.test_db_path)

    def tearDown(self):
        """クリーンアップ"""
        if os.path.exists(self.test_db_path):
            shutil.rmtree(self.test_db_path)

    def test_full_workflow(self):
        """完全なワークフローのテスト"""
        # 1. 複数の返信を追加
        replies = [
            ("r1", "機械学習のモデル選定", {"sentiment": "positive"}),
            ("r2", "データ前処理の方法", {"sentiment": "neutral"}),
            ("r3", "AIの倫理問題", {"sentiment": "neutral"}),
        ]

        for reply_id, content, metadata in replies:
            self.kb.add_reply(reply_id, content, metadata)

        # 2. 複数のツイートを追加
        tweets = [
            ("t1", "今日のAI開発", {"likes": 100, "retweets": 30}),
            ("t2", "機械学習の最新論文", {"likes": 200, "retweets": 60}),
        ]

        for tweet_id, content, engagement in tweets:
            self.kb.add_successful_tweet(tweet_id, content, engagement)

        # 3. 統計情報を確認
        stats = self.kb.get_stats()
        self.assertEqual(stats["replies_count"], 3)
        self.assertEqual(stats["tweets_count"], 2)
        self.assertEqual(stats["total_count"], 5)

        # 4. 類似検索
        similar_replies = self.kb.search_similar_replies("機械学習", top_k=2)
        self.assertGreater(len(similar_replies), 0)

        similar_tweets = self.kb.search_similar_tweets("AI", top_k=2)
        self.assertGreater(len(similar_tweets), 0)

        # 5. 文脈生成
        context = self.kb.get_context_for_generation("機械学習とAI")
        self.assertIsInstance(context, str)
        self.assertGreater(len(context), 0)


def run_tests():
    """テストを実行"""
    # テストスイートを作成
    loader = unittest.TestLoader()
    suite = unittest.TestSuite()

    # テストケースを追加
    suite.addTests(loader.loadTestsFromTestCase(TestKnowledgeBase))
    suite.addTests(loader.loadTestsFromTestCase(TestKnowledgeBaseIntegration))

    # テストを実行
    runner = unittest.TextTestRunner(verbosity=2)
    result = runner.run(suite)

    # 結果を返す
    return result.wasSuccessful()


if __name__ == "__main__":
    success = run_tests()
    sys.exit(0 if success else 1)
