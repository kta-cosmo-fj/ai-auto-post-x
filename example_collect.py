#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Twitter Feedback Collector 使用例

このスクリプトは、FeedbackCollectorの基本的な使い方を示します。
"""

import argparse
import logging
import sys
from datetime import datetime

from modules.feedback_collector import FeedbackCollector

# ロギング設定
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)


def collect_recent_and_analyze(days: int = 7, max_tweets: int = 100):
    """
    最近のツイートを収集して分析する

    Args:
        days: 何日前までのツイートを収集するか
        max_tweets: 取得する最大件数
    """
    logger.info("=" * 60)
    logger.info("Starting Twitter Feedback Collection")
    logger.info("=" * 60)

    try:
        # FeedbackCollectorを初期化
        collector = FeedbackCollector()

        # 1. 最近のツイートを収集
        logger.info(f"\n[1/4] Collecting tweets from the last {days} days...")
        tweets = collector.collect_recent_tweets(days=days, max_results=max_tweets)

        if not tweets:
            logger.warning("No tweets found in the specified period.")
            return

        logger.info(f"✓ Found {len(tweets)} tweets")

        # 2. 各ツイートのエンゲージメント詳細を収集
        logger.info(f"\n[2/4] Collecting detailed engagement data...")
        for i, tweet in enumerate(tweets[:10], 1):  # 最大10件まで詳細収集
            tweet_id = tweet['tweet_id']
            logger.info(f"  [{i}/{min(10, len(tweets))}] Tweet {tweet_id}")

            try:
                # エンゲージメント情報を更新
                collector.collect_tweet_engagement(tweet_id)

                # 返信を収集（Free tierでは動作しない可能性あり）
                collector.collect_replies(tweet_id, max_results=5)

            except Exception as e:
                logger.warning(f"  Failed to collect data for tweet {tweet_id}: {e}")
                continue

        # 3. エンゲージメント履歴を表示
        logger.info(f"\n[3/4] Engagement history for top tweets...")
        for tweet in tweets[:3]:  # 上位3件の履歴を表示
            tweet_id = tweet['tweet_id']
            history = collector.get_engagement_history(tweet_id)

            logger.info(f"\n  Tweet {tweet_id}:")
            logger.info(f"  Content: {tweet['content'][:50]}...")
            logger.info(f"  Snapshots: {len(history)}")

            if history:
                latest = history[-1]
                logger.info(f"  Latest engagement:")
                logger.info(f"    Likes: {latest['likes']}")
                logger.info(f"    Retweets: {latest['retweets']}")
                logger.info(f"    Replies: {latest['replies']}")

        # 4. 統計情報を表示
        logger.info(f"\n[4/4] Database statistics...")
        stats = collector.get_statistics()
        logger.info("=" * 60)
        logger.info("Overall Statistics:")
        logger.info(f"  Total tweets in DB: {stats['total_tweets']}")
        logger.info(f"  Total replies in DB: {stats['total_replies']}")
        logger.info(f"  Total snapshots: {stats['total_snapshots']}")

        if stats['total_tweets'] > 0:
            logger.info(f"\n  Average engagement:")
            logger.info(f"    Likes: {stats['avg_likes']:.2f}")
            logger.info(f"    Retweets: {stats['avg_retweets']:.2f}")
            logger.info(f"    Replies: {stats['avg_replies']:.2f}")

        logger.info("=" * 60)
        logger.info("✓ Collection completed successfully!")

    except Exception as e:
        logger.error(f"Error during collection: {e}", exc_info=True)
        raise


def batch_update_old_tweets(hours: int = 24):
    """
    古いツイートのエンゲージメントを一括更新する

    Args:
        hours: 何時間更新されていないツイートを対象とするか
    """
    logger.info("=" * 60)
    logger.info("Starting Batch Engagement Update")
    logger.info("=" * 60)

    try:
        collector = FeedbackCollector()

        logger.info(f"Updating tweets not updated in the last {hours} hours...")
        updated_count = collector.batch_update_engagement(hours_since_last_update=hours)

        logger.info("=" * 60)
        logger.info(f"✓ Updated {updated_count} tweets")
        logger.info("=" * 60)

    except Exception as e:
        logger.error(f"Error during batch update: {e}", exc_info=True)
        raise


def show_tweet_details(tweet_id: str):
    """
    特定のツイートの詳細情報を表示する

    Args:
        tweet_id: ツイートID
    """
    logger.info("=" * 60)
    logger.info(f"Tweet Details: {tweet_id}")
    logger.info("=" * 60)

    try:
        collector = FeedbackCollector()

        # 最新のエンゲージメント情報を取得
        engagement = collector.collect_tweet_engagement(tweet_id)

        if not engagement:
            logger.warning("Tweet not found")
            return

        logger.info(f"\nContent: {engagement['content']}")
        logger.info(f"Posted at: {engagement['posted_at']}")
        logger.info(f"\nCurrent engagement:")
        logger.info(f"  Likes: {engagement['likes']}")
        logger.info(f"  Retweets: {engagement['retweets']}")
        logger.info(f"  Replies: {engagement['replies']}")
        logger.info(f"  Impressions: {engagement.get('impressions', 'N/A')}")

        # 返信を取得
        replies = collector.collect_replies(tweet_id, max_results=10)
        logger.info(f"\nReplies ({len(replies)}):")
        for reply in replies[:5]:
            logger.info(f"  @{reply['author_username']}: {reply['content'][:50]}...")

        # エンゲージメント履歴を表示
        history = collector.get_engagement_history(tweet_id)
        logger.info(f"\nEngagement history ({len(history)} snapshots):")
        for snapshot in history[-5:]:  # 最新5件
            logger.info(
                f"  {snapshot['snapshot_at']}: "
                f"Likes={snapshot['likes']}, "
                f"RT={snapshot['retweets']}, "
                f"Replies={snapshot['replies']}"
            )

        logger.info("=" * 60)

    except Exception as e:
        logger.error(f"Error getting tweet details: {e}", exc_info=True)
        raise


def main():
    """メイン処理"""
    parser = argparse.ArgumentParser(
        description="Twitter Feedback Collector - Collect engagement data from your tweets"
    )
    subparsers = parser.add_subparsers(dest='command', help='Commands')

    # collect コマンド
    collect_parser = subparsers.add_parser(
        'collect',
        help='Collect recent tweets and their engagement data'
    )
    collect_parser.add_argument(
        '--days',
        type=int,
        default=7,
        help='Number of days to look back (default: 7)'
    )
    collect_parser.add_argument(
        '--max-tweets',
        type=int,
        default=100,
        help='Maximum number of tweets to collect (default: 100)'
    )

    # update コマンド
    update_parser = subparsers.add_parser(
        'update',
        help='Batch update engagement data for old tweets'
    )
    update_parser.add_argument(
        '--hours',
        type=int,
        default=24,
        help='Update tweets not updated in the last N hours (default: 24)'
    )

    # show コマンド
    show_parser = subparsers.add_parser(
        'show',
        help='Show details for a specific tweet'
    )
    show_parser.add_argument(
        'tweet_id',
        type=str,
        help='Tweet ID to show details for'
    )

    args = parser.parse_args()

    if not args.command:
        parser.print_help()
        return 0

    try:
        if args.command == 'collect':
            collect_recent_and_analyze(days=args.days, max_tweets=args.max_tweets)
        elif args.command == 'update':
            batch_update_old_tweets(hours=args.hours)
        elif args.command == 'show':
            show_tweet_details(args.tweet_id)

        return 0

    except KeyboardInterrupt:
        logger.info("\nInterrupted by user")
        return 130
    except Exception as e:
        logger.error(f"Fatal error: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
