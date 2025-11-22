#!/usr/bin/env python3
"""
Knowledge Base 初期化スクリプト

このスクリプトは、ChromaDBベースの知識ベースを初期化し、
サンプルデータを追加します。
"""

import os
import sys
from datetime import datetime, timedelta
from modules.knowledge_base import KnowledgeBase


def init_knowledge_base(reset: bool = False):
    """
    知識ベースを初期化

    Args:
        reset: Trueの場合、既存のデータを削除して再初期化
    """
    print("=" * 60)
    print("Knowledge Base Initialization")
    print("=" * 60)

    # KnowledgeBaseのインスタンス作成
    kb = KnowledgeBase()

    # リセットが指定された場合
    if reset:
        print("\n[WARNING] Resetting existing knowledge base...")
        confirm = input("Are you sure? This will delete all data. (yes/no): ")
        if confirm.lower() == 'yes':
            kb.reset()
            print("✓ Knowledge base has been reset.")
        else:
            print("✗ Reset cancelled.")
            return

    # 現在の統計情報を表示
    print("\n[INFO] Current Statistics:")
    stats = kb.get_stats()
    for key, value in stats.items():
        print(f"  - {key}: {value}")

    # サンプルデータの追加
    print("\n[INFO] Adding sample data...")

    # サンプル返信データ
    sample_replies = [
        {
            "reply_id": "reply_001",
            "content": "機械学習のモデル選定について、データの特性を考慮することが重要です。",
            "metadata": {
                "author": "ml_expert",
                "tweet_id": "tweet_001",
                "replied_at": (datetime.now() - timedelta(days=5)).isoformat(),
                "sentiment": "positive"
            }
        },
        {
            "reply_id": "reply_002",
            "content": "AIの倫理的な側面について議論することは非常に重要だと思います。",
            "metadata": {
                "author": "ai_researcher",
                "tweet_id": "tweet_002",
                "replied_at": (datetime.now() - timedelta(days=3)).isoformat(),
                "sentiment": "neutral"
            }
        },
        {
            "reply_id": "reply_003",
            "content": "Pythonでのデータ処理にはpandasとnumpyが欠かせませんね。",
            "metadata": {
                "author": "data_scientist",
                "tweet_id": "tweet_003",
                "replied_at": (datetime.now() - timedelta(days=2)).isoformat(),
                "sentiment": "positive"
            }
        },
    ]

    for reply in sample_replies:
        kb.add_reply(
            reply_id=reply["reply_id"],
            content=reply["content"],
            metadata=reply["metadata"]
        )
        print(f"  ✓ Added reply: {reply['reply_id']}")

    # サンプルツイートデータ
    sample_tweets = [
        {
            "tweet_id": "tweet_success_001",
            "content": "今日のAI開発は順調です。新しいモデルのパフォーマンスが予想以上に良好でした！",
            "engagement": {
                "likes": 150,
                "retweets": 45,
                "engagement_rate": 0.15,
                "posted_at": (datetime.now() - timedelta(days=4)).isoformat()
            }
        },
        {
            "tweet_id": "tweet_success_002",
            "content": "機械学習の最新論文を読んでいます。Transformerの新しい応用例が興味深い。",
            "engagement": {
                "likes": 230,
                "retweets": 67,
                "engagement_rate": 0.23,
                "posted_at": (datetime.now() - timedelta(days=3)).isoformat()
            }
        },
        {
            "tweet_id": "tweet_success_003",
            "content": "Pythonでデータ分析を効率化する小技を共有します。pandasのgroupby活用法について。",
            "engagement": {
                "likes": 310,
                "retweets": 89,
                "engagement_rate": 0.31,
                "posted_at": (datetime.now() - timedelta(days=1)).isoformat()
            }
        },
    ]

    for tweet in sample_tweets:
        kb.add_successful_tweet(
            tweet_id=tweet["tweet_id"],
            content=tweet["content"],
            engagement=tweet["engagement"]
        )
        print(f"  ✓ Added tweet: {tweet['tweet_id']}")

    # 更新後の統計情報を表示
    print("\n[INFO] Updated Statistics:")
    stats = kb.get_stats()
    for key, value in stats.items():
        print(f"  - {key}: {value}")

    # サンプル検索
    print("\n[INFO] Sample Search - Query: 'AI開発'")
    print("-" * 60)
    context = kb.get_context_for_generation(query="AI開発")
    print(context if context else "No results found.")

    print("\n" + "=" * 60)
    print("Initialization Complete!")
    print("=" * 60)


def main():
    """メイン関数"""
    # コマンドライン引数をチェック
    reset = "--reset" in sys.argv

    try:
        init_knowledge_base(reset=reset)
    except Exception as e:
        print(f"\n[ERROR] Initialization failed: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
