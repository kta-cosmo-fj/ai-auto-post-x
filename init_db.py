#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
データベース初期化スクリプト

tweets.dbを初期化または再作成する
"""

import argparse
import logging
import sys
from pathlib import Path

from modules.db_manager import DBManager

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(message)s',
    datefmt='%Y-%m-%d %H:%M:%S'
)
logger = logging.getLogger(__name__)


def main():
    parser = argparse.ArgumentParser(
        description="Initialize or reset the tweets database"
    )
    parser.add_argument(
        "--db-path",
        type=str,
        default="data/tweets.db",
        help="Path to the database file (default: data/tweets.db)"
    )
    parser.add_argument(
        "--reset",
        action="store_true",
        help="Reset the database (delete existing file)"
    )
    parser.add_argument(
        "--stats",
        action="store_true",
        help="Show database statistics"
    )

    args = parser.parse_args()

    db_path = Path(args.db_path)

    # リセットオプションが指定された場合
    if args.reset:
        if db_path.exists():
            confirm = input(f"Are you sure you want to delete {db_path}? (yes/no): ")
            if confirm.lower() == 'yes':
                db_path.unlink()
                logger.info(f"Deleted existing database: {db_path}")
            else:
                logger.info("Reset cancelled")
                return 0

    # データベースを初期化
    try:
        db = DBManager(str(db_path))
        logger.info(f"Database initialized successfully at {db_path}")

        # 統計情報を表示
        if args.stats or db_path.exists():
            stats = db.get_statistics()
            logger.info("=" * 50)
            logger.info("Database Statistics:")
            logger.info(f"  Total tweets: {stats['total_tweets']}")
            logger.info(f"  Total replies: {stats['total_replies']}")
            logger.info(f"  Total snapshots: {stats['total_snapshots']}")
            if stats['total_tweets'] > 0:
                logger.info(f"  Average likes: {stats['avg_likes']:.2f}")
                logger.info(f"  Average retweets: {stats['avg_retweets']:.2f}")
                logger.info(f"  Average replies: {stats['avg_replies']:.2f}")
            logger.info("=" * 50)

        return 0

    except Exception as e:
        logger.error(f"Failed to initialize database: {e}")
        return 1


if __name__ == "__main__":
    sys.exit(main())
