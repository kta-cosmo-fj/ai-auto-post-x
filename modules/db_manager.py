# -*- coding: utf-8 -*-
"""
データベース操作を管理するモジュール

SQLiteデータベースへの接続、テーブル作成、CRUD操作を提供する
"""

import logging
import sqlite3
from contextlib import contextmanager
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any

logger = logging.getLogger(__name__)


class DBManager:
    """SQLiteデータベース操作を管理するクラス"""

    def __init__(self, db_path: str = "data/tweets.db"):
        """
        Args:
            db_path: データベースファイルのパス
        """
        self.db_path = Path(db_path)
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        self._init_db()

    @contextmanager
    def _get_connection(self):
        """データベース接続のコンテキストマネージャー"""
        conn = sqlite3.connect(self.db_path)
        conn.row_factory = sqlite3.Row  # 辞書形式でアクセス可能にする
        try:
            yield conn
            conn.commit()
        except Exception as e:
            conn.rollback()
            logger.error(f"Database error: {e}")
            raise
        finally:
            conn.close()

    def _init_db(self) -> None:
        """データベーステーブルを初期化する"""
        with self._get_connection() as conn:
            cursor = conn.cursor()

            # tweets テーブル
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS tweets (
                    tweet_id TEXT PRIMARY KEY,
                    content TEXT NOT NULL,
                    posted_at TIMESTAMP,
                    likes INTEGER DEFAULT 0,
                    retweets INTEGER DEFAULT 0,
                    replies INTEGER DEFAULT 0,
                    impressions INTEGER DEFAULT 0,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            """)

            # replies テーブル
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS replies (
                    reply_id TEXT PRIMARY KEY,
                    tweet_id TEXT,
                    author_id TEXT,
                    author_username TEXT,
                    content TEXT,
                    replied_at TIMESTAMP,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (tweet_id) REFERENCES tweets(tweet_id)
                )
            """)

            # engagement_snapshots テーブル (時系列データ)
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS engagement_snapshots (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    tweet_id TEXT,
                    likes INTEGER,
                    retweets INTEGER,
                    replies INTEGER,
                    impressions INTEGER,
                    snapshot_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (tweet_id) REFERENCES tweets(tweet_id)
                )
            """)

            # インデックス作成
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_tweets_posted_at
                ON tweets(posted_at DESC)
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_replies_tweet_id
                ON replies(tweet_id)
            """)
            cursor.execute("""
                CREATE INDEX IF NOT EXISTS idx_snapshots_tweet_id
                ON engagement_snapshots(tweet_id, snapshot_at DESC)
            """)

            logger.info(f"Database initialized at {self.db_path}")

    def insert_tweet(self, tweet_data: Dict[str, Any]) -> None:
        """
        ツイートデータを挿入または更新する

        Args:
            tweet_data: ツイートデータの辞書
                - tweet_id (str): ツイートID
                - content (str): ツイート本文
                - posted_at (str/datetime): 投稿日時
                - likes (int): いいね数
                - retweets (int): リツイート数
                - replies (int): 返信数
                - impressions (int): インプレッション数 (optional)
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO tweets (
                    tweet_id, content, posted_at, likes, retweets, replies, impressions, updated_at
                ) VALUES (?, ?, ?, ?, ?, ?, ?, CURRENT_TIMESTAMP)
                ON CONFLICT(tweet_id) DO UPDATE SET
                    content = excluded.content,
                    likes = excluded.likes,
                    retweets = excluded.retweets,
                    replies = excluded.replies,
                    impressions = excluded.impressions,
                    updated_at = CURRENT_TIMESTAMP
            """, (
                tweet_data['tweet_id'],
                tweet_data['content'],
                tweet_data.get('posted_at'),
                tweet_data.get('likes', 0),
                tweet_data.get('retweets', 0),
                tweet_data.get('replies', 0),
                tweet_data.get('impressions', 0),
            ))
            logger.debug(f"Inserted/updated tweet {tweet_data['tweet_id']}")

    def insert_reply(self, reply_data: Dict[str, Any]) -> None:
        """
        返信データを挿入する

        Args:
            reply_data: 返信データの辞書
                - reply_id (str): 返信ID
                - tweet_id (str): 元ツイートID
                - author_id (str): 返信者ID
                - author_username (str): 返信者ユーザー名
                - content (str): 返信本文
                - replied_at (str/datetime): 返信日時
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT OR IGNORE INTO replies (
                    reply_id, tweet_id, author_id, author_username, content, replied_at
                ) VALUES (?, ?, ?, ?, ?, ?)
            """, (
                reply_data['reply_id'],
                reply_data['tweet_id'],
                reply_data['author_id'],
                reply_data['author_username'],
                reply_data['content'],
                reply_data.get('replied_at'),
            ))
            logger.debug(f"Inserted reply {reply_data['reply_id']}")

    def insert_engagement_snapshot(self, tweet_id: str, engagement_data: Dict[str, int]) -> None:
        """
        エンゲージメントのスナップショットを記録する

        Args:
            tweet_id: ツイートID
            engagement_data: エンゲージメントデータ
                - likes (int): いいね数
                - retweets (int): リツイート数
                - replies (int): 返信数
                - impressions (int): インプレッション数 (optional)
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT INTO engagement_snapshots (
                    tweet_id, likes, retweets, replies, impressions
                ) VALUES (?, ?, ?, ?, ?)
            """, (
                tweet_id,
                engagement_data.get('likes', 0),
                engagement_data.get('retweets', 0),
                engagement_data.get('replies', 0),
                engagement_data.get('impressions', 0),
            ))
            logger.debug(f"Inserted engagement snapshot for tweet {tweet_id}")

    def get_tweet(self, tweet_id: str) -> Optional[Dict[str, Any]]:
        """
        ツイートIDでツイート情報を取得する

        Args:
            tweet_id: ツイートID

        Returns:
            ツイート情報の辞書、存在しない場合はNone
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT * FROM tweets WHERE tweet_id = ?", (tweet_id,))
            row = cursor.fetchone()
            return dict(row) if row else None

    def get_recent_tweets(self, limit: int = 100) -> List[Dict[str, Any]]:
        """
        最近のツイートを取得する

        Args:
            limit: 取得する最大件数

        Returns:
            ツイート情報の辞書のリスト
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM tweets
                ORDER BY posted_at DESC
                LIMIT ?
            """, (limit,))
            return [dict(row) for row in cursor.fetchall()]

    def get_replies(self, tweet_id: str) -> List[Dict[str, Any]]:
        """
        特定のツイートへの返信を取得する

        Args:
            tweet_id: ツイートID

        Returns:
            返信情報の辞書のリスト
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM replies
                WHERE tweet_id = ?
                ORDER BY replied_at DESC
            """, (tweet_id,))
            return [dict(row) for row in cursor.fetchall()]

    def get_engagement_history(self, tweet_id: str) -> List[Dict[str, Any]]:
        """
        ツイートのエンゲージメント履歴を取得する

        Args:
            tweet_id: ツイートID

        Returns:
            エンゲージメントスナップショットのリスト
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT * FROM engagement_snapshots
                WHERE tweet_id = ?
                ORDER BY snapshot_at ASC
            """, (tweet_id,))
            return [dict(row) for row in cursor.fetchall()]

    def get_tweets_without_recent_snapshot(self, hours: int = 24) -> List[Dict[str, Any]]:
        """
        最近スナップショットが取得されていないツイートを取得する

        Args:
            hours: 何時間以内のスナップショットがあればスキップするか

        Returns:
            ツイート情報の辞書のリスト
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT t.* FROM tweets t
                LEFT JOIN (
                    SELECT tweet_id, MAX(snapshot_at) as last_snapshot
                    FROM engagement_snapshots
                    GROUP BY tweet_id
                ) s ON t.tweet_id = s.tweet_id
                WHERE s.last_snapshot IS NULL
                   OR datetime(s.last_snapshot) < datetime('now', '-' || ? || ' hours')
                ORDER BY t.posted_at DESC
            """, (hours,))
            return [dict(row) for row in cursor.fetchall()]

    def get_statistics(self) -> Dict[str, Any]:
        """
        データベースの統計情報を取得する

        Returns:
            統計情報の辞書
        """
        with self._get_connection() as conn:
            cursor = conn.cursor()

            cursor.execute("SELECT COUNT(*) FROM tweets")
            total_tweets = cursor.fetchone()[0]

            cursor.execute("SELECT COUNT(*) FROM replies")
            total_replies = cursor.fetchone()[0]

            cursor.execute("SELECT COUNT(*) FROM engagement_snapshots")
            total_snapshots = cursor.fetchone()[0]

            cursor.execute("""
                SELECT
                    SUM(likes) as total_likes,
                    SUM(retweets) as total_retweets,
                    SUM(replies) as total_replies,
                    AVG(likes) as avg_likes,
                    AVG(retweets) as avg_retweets,
                    AVG(replies) as avg_replies
                FROM tweets
            """)
            engagement_stats = dict(cursor.fetchone())

            return {
                'total_tweets': total_tweets,
                'total_replies': total_replies,
                'total_snapshots': total_snapshots,
                **engagement_stats
            }
