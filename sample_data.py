#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
サンプルデータ生成スクリプト

テスト用のサンプルツイートデータをデータベースに追加します
"""
from modules.analyzer import EngagementAnalyzer


def generate_sample_data():
    """サンプルデータを生成"""
    analyzer = EngagementAnalyzer(db_path="data/tweets.db")

    sample_tweets = [
        {
            "tweet_id": "1001",
            "content": "AI技術の進化について考える。機械学習は今後さらに重要になります。🤖",
            "likes": 150,
            "retweets": 30,
            "replies": 10,
            "impressions": 2000,
            "posted_at": "2025-01-15T09:00:00+00:00"
        },
        {
            "tweet_id": "1002",
            "content": "プログラミングの学習方法について？効率的な勉強法を3つ紹介します。",
            "likes": 120,
            "retweets": 25,
            "replies": 15,
            "impressions": 1800,
            "posted_at": "2025-01-15T12:00:00+00:00"
        },
        {
            "tweet_id": "1003",
            "content": "ビジネスで成功するための3つのポイント #起業 #マーケティング",
            "likes": 200,
            "retweets": 45,
            "replies": 12,
            "impressions": 2500,
            "posted_at": "2025-01-15T15:00:00+00:00"
        },
        {
            "tweet_id": "1004",
            "content": "生産性を上げる時間管理術🚀効率化のコツをシェアします",
            "likes": 180,
            "retweets": 35,
            "replies": 20,
            "impressions": 2200,
            "posted_at": "2025-01-15T20:00:00+00:00"
        },
        {
            "tweet_id": "1005",
            "content": "健康的な習慣を作るには？睡眠と運動が鍵です。",
            "likes": 90,
            "retweets": 15,
            "replies": 5,
            "impressions": 1200,
            "posted_at": "2025-01-16T09:00:00+00:00"
        },
        {
            "tweet_id": "1006",
            "content": "知ってました？人間の脳は1日に約3万5千回の決定を下しているそうです。",
            "likes": 250,
            "retweets": 60,
            "replies": 25,
            "impressions": 3000,
            "posted_at": "2025-01-16T10:00:00+00:00"
        },
        {
            "tweet_id": "1007",
            "content": "Pythonでデータ分析を始めたい人へ。おすすめのライブラリ5選",
            "likes": 140,
            "retweets": 28,
            "replies": 8,
            "impressions": 1900,
            "posted_at": "2025-01-16T14:00:00+00:00"
        },
        {
            "tweet_id": "1008",
            "content": "調査によると、週4日勤務の企業で生産性が20%向上したとの結果が。",
            "likes": 220,
            "retweets": 50,
            "replies": 18,
            "impressions": 2700,
            "posted_at": "2025-01-16T16:00:00+00:00"
        },
        {
            "tweet_id": "1009",
            "content": "テクノロジーとイノベーションの関係性。デジタル化が変える未来",
            "likes": 110,
            "retweets": 22,
            "replies": 6,
            "impressions": 1500,
            "posted_at": "2025-01-17T11:00:00+00:00"
        },
        {
            "tweet_id": "1010",
            "content": "成功する人と失敗する人の違い：習慣の力が全てを変える",
            "likes": 190,
            "retweets": 40,
            "replies": 14,
            "impressions": 2300,
            "posted_at": "2025-01-17T19:00:00+00:00"
        },
        {
            "tweet_id": "1011",
            "content": "AIによるコード生成ツールが開発者の生産性を3倍にする時代が来た",
            "likes": 160,
            "retweets": 32,
            "replies": 11,
            "impressions": 2100,
            "posted_at": "2025-01-17T21:00:00+00:00"
        },
        {
            "tweet_id": "1012",
            "content": "認知バイアスを理解すると、意思決定の質が格段に上がります",
            "likes": 130,
            "retweets": 26,
            "replies": 9,
            "impressions": 1700,
            "posted_at": "2025-01-18T10:00:00+00:00"
        },
        {
            "tweet_id": "1013",
            "content": "データが示すのは、朝型人間の方が夜型より生産性が高いということ？",
            "likes": 100,
            "retweets": 20,
            "replies": 22,
            "impressions": 1400,
            "posted_at": "2025-01-18T13:00:00+00:00"
        },
        {
            "tweet_id": "1014",
            "content": "実は、スタートアップの90%が5年以内に失敗する。成功の鍵は何か",
            "likes": 210,
            "retweets": 48,
            "replies": 16,
            "impressions": 2600,
            "posted_at": "2025-01-18T18:00:00+00:00"
        },
        {
            "tweet_id": "1015",
            "content": "科学研究によると、運動は記憶力を30%改善する効果があるそうです",
            "likes": 170,
            "retweets": 34,
            "replies": 13,
            "impressions": 2000,
            "posted_at": "2025-01-19T08:00:00+00:00"
        },
    ]

    for tweet in sample_tweets:
        analyzer.add_tweet(**tweet)

    print(f"✓ {len(sample_tweets)}件のサンプルツイートを追加しました")

    # 統計表示
    summary = analyzer.get_stats_summary()
    print(f"\n統計サマリー:")
    print(f"  総ツイート数: {summary['total_tweets']}")
    print(f"  平均いいね数: {summary['avg_likes']:.1f}")
    print(f"  最大いいね数: {summary['max_likes']}")
    print(f"  総インプレッション数: {summary['total_impressions']:,}")


if __name__ == "__main__":
    generate_sample_data()
