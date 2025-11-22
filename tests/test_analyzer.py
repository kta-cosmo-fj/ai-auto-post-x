# -*- coding: utf-8 -*-
"""
Tests for EngagementAnalyzer

Usage:
    pytest tests/test_analyzer.py -v
"""
import os
import sqlite3
import tempfile
from datetime import datetime, timezone

import pytest

from modules.analyzer import EngagementAnalyzer


@pytest.fixture
def temp_db():
    """テスト用の一時データベースを作成"""
    with tempfile.NamedTemporaryFile(suffix=".db", delete=False) as f:
        db_path = f.name

    yield db_path

    # クリーンアップ
    if os.path.exists(db_path):
        os.unlink(db_path)


@pytest.fixture
def analyzer(temp_db):
    """テスト用のEngagementAnalyzerインスタンスを作成"""
    return EngagementAnalyzer(db_path=temp_db)


@pytest.fixture
def sample_tweets(analyzer):
    """サンプルツイートデータを挿入"""
    tweets = [
        {
            "tweet_id": "1",
            "content": "AI技術の進化について考える。機械学習は今後さらに重要になります。",
            "likes": 100,
            "retweets": 20,
            "replies": 5,
            "impressions": 1000,
            "posted_at": "2025-01-01T09:00:00+00:00"
        },
        {
            "tweet_id": "2",
            "content": "プログラミングの学習方法について？効率的な勉強法を紹介します。",
            "likes": 80,
            "retweets": 15,
            "replies": 10,
            "impressions": 800,
            "posted_at": "2025-01-01T12:00:00+00:00"
        },
        {
            "tweet_id": "3",
            "content": "ビジネスで成功するための3つのポイント #起業 #マーケティング",
            "likes": 150,
            "retweets": 30,
            "replies": 8,
            "impressions": 1200,
            "posted_at": "2025-01-01T15:00:00+00:00"
        },
        {
            "tweet_id": "4",
            "content": "生産性を上げる時間管理術🚀効率化のコツをシェアします",
            "likes": 120,
            "retweets": 25,
            "replies": 12,
            "impressions": 1100,
            "posted_at": "2025-01-01T20:00:00+00:00"
        },
        {
            "tweet_id": "5",
            "content": "健康的な習慣を作るには？睡眠と運動が鍵です。",
            "likes": 60,
            "retweets": 10,
            "replies": 3,
            "impressions": 600,
            "posted_at": "2025-01-02T09:00:00+00:00"
        },
    ]

    for tweet in tweets:
        analyzer.add_tweet(**tweet)

    return tweets


class TestEngagementAnalyzer:
    """EngagementAnalyzerのテストクラス"""

    def test_init_creates_database(self, temp_db):
        """データベースとテーブルが正しく作成されるかテスト"""
        analyzer = EngagementAnalyzer(db_path=temp_db)

        # データベースファイルが存在することを確認
        assert os.path.exists(temp_db)

        # テーブルが作成されていることを確認
        with sqlite3.connect(temp_db) as conn:
            cursor = conn.cursor()
            cursor.execute(
                "SELECT name FROM sqlite_master WHERE type='table' AND name='tweets'"
            )
            result = cursor.fetchone()
            assert result is not None
            assert result[0] == "tweets"

    def test_add_tweet(self, analyzer):
        """ツイート追加のテスト"""
        analyzer.add_tweet(
            tweet_id="test123",
            content="テストツイート",
            likes=10,
            retweets=2,
            replies=1,
            impressions=100,
            posted_at="2025-01-01T00:00:00+00:00"
        )

        # データが正しく追加されたか確認
        with sqlite3.connect(analyzer.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM tweets WHERE tweet_id = ?", ("test123",))
            row = cursor.fetchone()

        assert row is not None
        assert row[0] == "test123"
        assert row[1] == "テストツイート"
        assert row[2] == 10
        assert row[3] == 2
        assert row[4] == 1

    def test_get_top_tweets_by_likes(self, analyzer, sample_tweets):
        """いいね数でトップツイートを取得するテスト"""
        top_tweets = analyzer.get_top_tweets(limit=3, metric="likes")

        assert len(top_tweets) == 3
        assert top_tweets[0]["tweet_id"] == "3"  # 150 likes
        assert top_tweets[1]["tweet_id"] == "4"  # 120 likes
        assert top_tweets[2]["tweet_id"] == "1"  # 100 likes

    def test_get_top_tweets_by_retweets(self, analyzer, sample_tweets):
        """リツイート数でトップツイートを取得するテスト"""
        top_tweets = analyzer.get_top_tweets(limit=2, metric="retweets")

        assert len(top_tweets) == 2
        assert top_tweets[0]["tweet_id"] == "3"  # 30 retweets
        assert top_tweets[1]["tweet_id"] == "4"  # 25 retweets

    def test_get_top_tweets_by_engagement(self, analyzer, sample_tweets):
        """エンゲージメント率でトップツイートを取得するテスト"""
        top_tweets = analyzer.get_top_tweets(limit=3, metric="engagement")

        assert len(top_tweets) == 3
        # エンゲージメント率を計算
        # tweet_id "3": (150+30+8)/1200 = 0.1567
        # tweet_id "4": (120+25+12)/1100 = 0.1427
        # tweet_id "1": (100+20+5)/1000 = 0.1250
        assert top_tweets[0]["tweet_id"] == "3"

    def test_get_top_tweets_invalid_metric(self, analyzer, sample_tweets):
        """無効な指標でエラーが発生するかテスト"""
        with pytest.raises(ValueError):
            analyzer.get_top_tweets(limit=5, metric="invalid_metric")

    def test_analyze_tweet_patterns(self, analyzer, sample_tweets):
        """ツイートパターン分析のテスト"""
        tweet_ids = ["1", "2", "3"]
        patterns = analyzer.analyze_tweet_patterns(tweet_ids)

        assert "avg_length" in patterns
        assert "emoji_count" in patterns
        assert "hashtag_count" in patterns
        assert "question_tweets" in patterns
        assert "statement_tweets" in patterns
        assert "common_words" in patterns
        assert "topics" in patterns

        # 質問ツイート（tweet_id "2"）があることを確認
        assert patterns["question_tweets"] == 1
        assert patterns["statement_tweets"] == 2

        # ハッシュタグ（tweet_id "3"）があることを確認
        assert patterns["hashtag_count"] == 2

    def test_analyze_tweet_patterns_empty(self, analyzer):
        """空のツイートリストでパターン分析するテスト"""
        patterns = analyzer.analyze_tweet_patterns([])

        assert patterns["avg_length"] == 0
        assert patterns["emoji_count"] == 0
        assert patterns["hashtag_count"] == 0
        assert patterns["question_tweets"] == 0
        assert patterns["statement_tweets"] == 0
        assert patterns["common_words"] == []
        assert patterns["topics"] == []

    def test_extract_successful_features(self, analyzer, sample_tweets):
        """成功パターン抽出のテスト"""
        features = analyzer.extract_successful_features()

        assert "top_performing_pattern" in features
        assert "optimal_length" in features
        assert "recommended_features" in features

        assert isinstance(features["optimal_length"], int)
        assert isinstance(features["recommended_features"], list)

    def test_get_optimal_posting_time(self, analyzer, sample_tweets):
        """最適投稿時間分析のテスト"""
        optimal_times = analyzer.get_optimal_posting_time()

        assert isinstance(optimal_times, list)
        assert len(optimal_times) > 0

        # 時間帯フォーマットの確認
        for time_range in optimal_times:
            assert "-" in time_range
            start, end = time_range.split("-")
            assert ":" in start
            assert ":" in end

    def test_analyze_topic_performance(self, analyzer, sample_tweets):
        """トピックパフォーマンス分析のテスト"""
        topic_performance = analyzer.analyze_topic_performance()

        assert isinstance(topic_performance, dict)

        # AI トピックが含まれているはず（tweet_id "1"）
        if "AI" in topic_performance:
            assert "count" in topic_performance["AI"]
            assert "avg_likes" in topic_performance["AI"]
            assert topic_performance["AI"]["count"] > 0

    def test_get_stats_summary(self, analyzer, sample_tweets):
        """統計サマリー取得のテスト"""
        summary = analyzer.get_stats_summary()

        assert "total_tweets" in summary
        assert "avg_likes" in summary
        assert "avg_retweets" in summary
        assert "avg_replies" in summary
        assert "max_likes" in summary
        assert "total_impressions" in summary

        assert summary["total_tweets"] == 5
        assert summary["max_likes"] == 150
        assert summary["total_impressions"] == 4700

    def test_empty_database(self, analyzer):
        """空のデータベースでの統計取得テスト"""
        summary = analyzer.get_stats_summary()

        assert summary["total_tweets"] == 0
        assert summary["avg_likes"] == 0
        assert summary["max_likes"] == 0


if __name__ == "__main__":
    pytest.main([__file__, "-v"])
