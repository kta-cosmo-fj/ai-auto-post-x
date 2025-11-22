# -*- coding: utf-8 -*-
"""
FeedbackCollectorのユニットテスト

モックAPIを使用してFeedbackCollectorの機能をテストする
"""

import os
import sqlite3
import tempfile
import unittest
from datetime import datetime, timezone
from pathlib import Path
from unittest.mock import MagicMock, Mock, patch

import tweepy

from modules.db_manager import DBManager
from modules.feedback_collector import FeedbackCollector


class TestDBManager(unittest.TestCase):
    """DBManagerクラスのテスト"""

    def setUp(self):
        """テスト前の準備"""
        # 一時ディレクトリにテスト用DBを作成
        self.temp_dir = tempfile.mkdtemp()
        self.db_path = os.path.join(self.temp_dir, "test_tweets.db")
        self.db = DBManager(self.db_path)

    def tearDown(self):
        """テスト後のクリーンアップ"""
        # 一時ファイルを削除
        if Path(self.db_path).exists():
            Path(self.db_path).unlink()
        Path(self.temp_dir).rmdir()

    def test_db_initialization(self):
        """データベースが正しく初期化されるかテスト"""
        self.assertTrue(Path(self.db_path).exists())

        # テーブルが作成されているか確認
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT name FROM sqlite_master
                WHERE type='table' AND name IN ('tweets', 'replies', 'engagement_snapshots')
            """)
            tables = [row[0] for row in cursor.fetchall()]
            self.assertIn('tweets', tables)
            self.assertIn('replies', tables)
            self.assertIn('engagement_snapshots', tables)

    def test_insert_tweet(self):
        """ツイートの挿入テスト"""
        tweet_data = {
            'tweet_id': '123456789',
            'content': 'Test tweet content',
            'posted_at': datetime.now(timezone.utc).isoformat(),
            'likes': 10,
            'retweets': 5,
            'replies': 2,
            'impressions': 100,
        }

        self.db.insert_tweet(tweet_data)

        # 挿入されたデータを確認
        tweet = self.db.get_tweet('123456789')
        self.assertIsNotNone(tweet)
        self.assertEqual(tweet['tweet_id'], '123456789')
        self.assertEqual(tweet['content'], 'Test tweet content')
        self.assertEqual(tweet['likes'], 10)

    def test_insert_reply(self):
        """返信の挿入テスト"""
        # まずツイートを挿入
        tweet_data = {
            'tweet_id': '123456789',
            'content': 'Original tweet',
            'posted_at': datetime.now(timezone.utc).isoformat(),
            'likes': 0,
            'retweets': 0,
            'replies': 0,
        }
        self.db.insert_tweet(tweet_data)

        # 返信を挿入
        reply_data = {
            'reply_id': '987654321',
            'tweet_id': '123456789',
            'author_id': '111',
            'author_username': 'testuser',
            'content': 'Test reply',
            'replied_at': datetime.now(timezone.utc).isoformat(),
        }
        self.db.insert_reply(reply_data)

        # 挿入されたデータを確認
        replies = self.db.get_replies('123456789')
        self.assertEqual(len(replies), 1)
        self.assertEqual(replies[0]['reply_id'], '987654321')
        self.assertEqual(replies[0]['author_username'], 'testuser')

    def test_insert_engagement_snapshot(self):
        """エンゲージメントスナップショットの挿入テスト"""
        # まずツイートを挿入
        tweet_data = {
            'tweet_id': '123456789',
            'content': 'Test tweet',
            'posted_at': datetime.now(timezone.utc).isoformat(),
            'likes': 0,
            'retweets': 0,
            'replies': 0,
        }
        self.db.insert_tweet(tweet_data)

        # スナップショットを挿入
        engagement_data = {
            'likes': 10,
            'retweets': 5,
            'replies': 2,
            'impressions': 100,
        }
        self.db.insert_engagement_snapshot('123456789', engagement_data)

        # 挿入されたデータを確認
        history = self.db.get_engagement_history('123456789')
        self.assertEqual(len(history), 1)
        self.assertEqual(history[0]['likes'], 10)
        self.assertEqual(history[0]['retweets'], 5)

    def test_get_statistics(self):
        """統計情報の取得テスト"""
        # テストデータを挿入
        for i in range(3):
            tweet_data = {
                'tweet_id': f'tweet_{i}',
                'content': f'Test tweet {i}',
                'posted_at': datetime.now(timezone.utc).isoformat(),
                'likes': i * 10,
                'retweets': i * 5,
                'replies': i * 2,
            }
            self.db.insert_tweet(tweet_data)

        stats = self.db.get_statistics()
        self.assertEqual(stats['total_tweets'], 3)
        self.assertEqual(stats['total_likes'], 30)  # 0 + 10 + 20
        self.assertEqual(stats['avg_likes'], 10.0)


class TestFeedbackCollector(unittest.TestCase):
    """FeedbackCollectorクラスのテスト"""

    def setUp(self):
        """テスト前の準備"""
        # 一時ディレクトリにテスト用DBを作成
        self.temp_dir = tempfile.mkdtemp()
        self.db_path = os.path.join(self.temp_dir, "test_tweets.db")

        # 環境変数をモック（Bearer Token + User ID）
        self.env_patcher = patch.dict(os.environ, {
            'X_BEARER_TOKEN': 'test_bearer_token',
            'X_USER_ID': '12345',
        })
        self.env_patcher.start()

    def tearDown(self):
        """テスト後のクリーンアップ"""
        self.env_patcher.stop()

        # 一時ファイルを削除
        if Path(self.db_path).exists():
            Path(self.db_path).unlink()
        Path(self.temp_dir).rmdir()

    @patch('modules.feedback_collector.tweepy.Client')
    def test_initialization(self, mock_client_class):
        """FeedbackCollectorの初期化テスト（Bearer Token + X_USER_ID）"""
        # モッククライアントの設定
        mock_client = MagicMock()
        mock_client_class.return_value = mock_client

        # FeedbackCollectorを初期化
        collector = FeedbackCollector(self.db_path)

        # クライアントが正しく初期化されたか確認
        mock_client_class.assert_called_once()
        # Bearer Token + X_USER_IDの場合、環境変数からuser_idを取得
        self.assertEqual(collector.user_id, '12345')
        # get_me()は呼ばれないはず
        mock_client.get_me.assert_not_called()

    @patch('modules.feedback_collector.tweepy.Client')
    def test_initialization_oauth(self, mock_client_class):
        """FeedbackCollectorの初期化テスト（OAuth 1.0a）"""
        # OAuth 1.0aの環境変数を設定
        with patch.dict(os.environ, {
            'X_API_KEY': 'test_api_key',
            'X_API_SECRET': 'test_api_secret',
            'X_ACCESS_TOKEN': 'test_access_token',
            'X_ACCESS_TOKEN_SECRET': 'test_access_token_secret',
        }, clear=True):
            # モッククライアントの設定
            mock_client = MagicMock()
            mock_user = Mock()
            mock_user.data.id = '67890'
            mock_client.get_me.return_value = mock_user
            mock_client_class.return_value = mock_client

            # FeedbackCollectorを初期化
            collector = FeedbackCollector(self.db_path)

            # OAuth 1.0aの場合、APIからuser_idを取得
            self.assertEqual(collector.user_id, '67890')
            # get_me()が呼ばれているはず
            mock_client.get_me.assert_called_once()

    @patch('modules.feedback_collector.tweepy.Client')
    def test_collect_recent_tweets(self, mock_client_class):
        """最近のツイート収集テスト"""
        # モッククライアントの設定
        mock_client = MagicMock()

        # モックツイートデータ
        mock_tweet = Mock()
        mock_tweet.id = '123456789'
        mock_tweet.text = 'Test tweet content'
        mock_tweet.created_at = datetime.now(timezone.utc)
        mock_tweet.public_metrics = {
            'like_count': 10,
            'retweet_count': 5,
            'reply_count': 2,
            'impression_count': 100,
        }

        mock_response = Mock()
        mock_response.data = [mock_tweet]
        mock_client.get_users_tweets.return_value = mock_response

        mock_client_class.return_value = mock_client

        # FeedbackCollectorを初期化
        collector = FeedbackCollector(self.db_path)

        # ツイートを収集
        tweets = collector.collect_recent_tweets(days=7)

        # 結果を確認
        self.assertEqual(len(tweets), 1)
        self.assertEqual(tweets[0]['tweet_id'], '123456789')
        self.assertEqual(tweets[0]['likes'], 10)
        self.assertEqual(tweets[0]['retweets'], 5)

        # データベースに保存されているか確認
        db_tweet = collector.db.get_tweet('123456789')
        self.assertIsNotNone(db_tweet)
        self.assertEqual(db_tweet['content'], 'Test tweet content')

    @patch('modules.feedback_collector.tweepy.Client')
    def test_collect_tweet_engagement(self, mock_client_class):
        """ツイートエンゲージメント収集テスト"""
        # モッククライアントの設定
        mock_client = MagicMock()

        # モックツイートデータ
        mock_tweet = Mock()
        mock_tweet.id = '123456789'
        mock_tweet.text = 'Test tweet content'
        mock_tweet.created_at = datetime.now(timezone.utc)
        mock_tweet.public_metrics = {
            'like_count': 15,
            'retweet_count': 8,
            'reply_count': 3,
            'impression_count': 150,
        }

        mock_response = Mock()
        mock_response.data = mock_tweet
        mock_client.get_tweet.return_value = mock_response

        mock_client_class.return_value = mock_client

        # FeedbackCollectorを初期化
        collector = FeedbackCollector(self.db_path)

        # エンゲージメントを収集
        engagement = collector.collect_tweet_engagement('123456789')

        # 結果を確認
        self.assertEqual(engagement['tweet_id'], '123456789')
        self.assertEqual(engagement['likes'], 15)
        self.assertEqual(engagement['retweets'], 8)

        # スナップショットが記録されているか確認
        history = collector.get_engagement_history('123456789')
        self.assertEqual(len(history), 1)
        self.assertEqual(history[0]['likes'], 15)

    @patch('modules.feedback_collector.tweepy.Client')
    @patch('modules.feedback_collector.time.sleep')
    def test_rate_limit_handling(self, mock_sleep, mock_client_class):
        """レート制限処理のテスト"""
        # モッククライアントの設定
        mock_client = MagicMock()

        # カスタム例外クラスを作成（tweepy.TooManyRequestsのモック）
        class MockRateLimitError(Exception):
            """レート制限エラーのモック"""
            pass

        # 1回目はエラー、2回目は成功
        call_count = [0]
        def mock_get_tweet(*args, **kwargs):
            call_count[0] += 1
            if call_count[0] == 1:
                # 1回目はレート制限エラー（tweepy.TooManyRequestsの代わり）
                raise MockRateLimitError("Rate limit exceeded")
            else:
                # 2回目は成功
                return Mock(data=Mock(
                    id='123',
                    text='Test',
                    created_at=datetime.now(timezone.utc),
                    public_metrics={'like_count': 0, 'retweet_count': 0, 'reply_count': 0, 'impression_count': 0}
                ))

        mock_client.get_tweet = mock_get_tweet
        mock_client_class.return_value = mock_client

        # FeedbackCollectorを初期化
        collector = FeedbackCollector(self.db_path)

        # tweepy.TooManyRequestsをMockRateLimitErrorに置き換え
        with patch('modules.feedback_collector.tweepy.TooManyRequests', MockRateLimitError):
            result = collector.collect_tweet_engagement('123')
            self.assertIsNotNone(result)
            # 2回呼ばれているはず（1回目失敗、2回目成功）
            self.assertEqual(call_count[0], 2)
            # sleepが1回呼ばれているはず（リトライ時）
            self.assertEqual(mock_sleep.call_count, 1)


def run_tests():
    """テストを実行する"""
    unittest.main(verbosity=2)


if __name__ == '__main__':
    run_tests()
