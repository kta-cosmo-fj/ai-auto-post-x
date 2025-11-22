# -*- coding: utf-8 -*-
"""
Engagement Analyzer Module

エンゲージメントデータを分析し、成功パターンを抽出するモジュール
"""
import re
import sqlite3
from collections import Counter, defaultdict
from dataclasses import dataclass
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional


@dataclass
class TweetStats:
    """ツイート統計情報"""
    tweet_id: str
    content: str
    likes: int
    retweets: int
    replies: int
    engagement_rate: float
    posted_at: datetime


class EngagementAnalyzer:
    """エンゲージメント分析クラス"""

    def __init__(self, db_path: str = "data/tweets.db"):
        """
        初期化

        Args:
            db_path: データベースファイルのパス
        """
        self.db_path = db_path
        self._ensure_database()

    def _ensure_database(self) -> None:
        """データベースとテーブルの存在を確認、必要なら作成"""
        Path(self.db_path).parent.mkdir(parents=True, exist_ok=True)

        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                CREATE TABLE IF NOT EXISTS tweets (
                    tweet_id TEXT PRIMARY KEY,
                    content TEXT NOT NULL,
                    likes INTEGER DEFAULT 0,
                    retweets INTEGER DEFAULT 0,
                    replies INTEGER DEFAULT 0,
                    impressions INTEGER DEFAULT 0,
                    posted_at TEXT,
                    created_at TEXT DEFAULT CURRENT_TIMESTAMP
                )
            """)
            conn.commit()

    def add_tweet(
        self,
        tweet_id: str,
        content: str,
        likes: int = 0,
        retweets: int = 0,
        replies: int = 0,
        impressions: int = 0,
        posted_at: Optional[str] = None
    ) -> None:
        """
        ツイートをデータベースに追加

        Args:
            tweet_id: ツイートID
            content: ツイート内容
            likes: いいね数
            retweets: リツイート数
            replies: 返信数
            impressions: インプレッション数
            posted_at: 投稿日時
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                INSERT OR REPLACE INTO tweets
                (tweet_id, content, likes, retweets, replies, impressions, posted_at)
                VALUES (?, ?, ?, ?, ?, ?, ?)
            """, (tweet_id, content, likes, retweets, replies, impressions, posted_at))
            conn.commit()

    def get_top_tweets(self, limit: int = 10, metric: str = "likes") -> List[Dict]:
        """
        指標に基づいてトップツイートを取得

        Args:
            limit: 取得件数
            metric: 並び替え指標 ("likes", "retweets", "replies", "engagement")

        Returns:
            トップツイートのリスト
        """
        valid_metrics = ["likes", "retweets", "replies", "engagement"]
        if metric not in valid_metrics:
            raise ValueError(f"metric must be one of {valid_metrics}")

        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()

            if metric == "engagement":
                # エンゲージメント率でソート
                query = """
                    SELECT
                        tweet_id, content, likes, retweets, replies, impressions, posted_at,
                        CASE
                            WHEN impressions > 0
                            THEN CAST(likes + retweets + replies AS FLOAT) / impressions
                            ELSE 0
                        END as engagement_rate
                    FROM tweets
                    WHERE impressions > 0
                    ORDER BY engagement_rate DESC
                    LIMIT ?
                """
            else:
                # 指定された指標でソート
                query = f"""
                    SELECT
                        tweet_id, content, likes, retweets, replies, impressions, posted_at,
                        CASE
                            WHEN impressions > 0
                            THEN CAST(likes + retweets + replies AS FLOAT) / impressions
                            ELSE 0
                        END as engagement_rate
                    FROM tweets
                    ORDER BY {metric} DESC
                    LIMIT ?
                """

            cursor.execute(query, (limit,))
            rows = cursor.fetchall()

            return [
                {
                    "tweet_id": row[0],
                    "content": row[1],
                    "likes": row[2],
                    "retweets": row[3],
                    "replies": row[4],
                    "impressions": row[5],
                    "posted_at": row[6],
                    "engagement_rate": row[7]
                }
                for row in rows
            ]

    def analyze_tweet_patterns(self, tweet_ids: List[str]) -> Dict:
        """
        指定されたツイートのパターンを分析

        Args:
            tweet_ids: 分析対象のツイートIDリスト

        Returns:
            パターン分析結果
        """
        if not tweet_ids:
            return {
                "avg_length": 0,
                "emoji_count": 0,
                "hashtag_count": 0,
                "question_tweets": 0,
                "statement_tweets": 0,
                "common_words": [],
                "topics": []
            }

        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            placeholders = ",".join("?" * len(tweet_ids))
            cursor.execute(
                f"SELECT content FROM tweets WHERE tweet_id IN ({placeholders})",
                tweet_ids
            )
            rows = cursor.fetchall()

        contents = [row[0] for row in rows]

        # 文字数の平均
        avg_length = sum(len(c) for c in contents) / len(contents) if contents else 0

        # 絵文字カウント
        emoji_pattern = re.compile(
            "["
            "\U0001F600-\U0001F64F"  # 顔文字
            "\U0001F300-\U0001F5FF"  # シンボル & ピクトグラム
            "\U0001F680-\U0001F6FF"  # 交通 & 地図記号
            "\U0001F1E0-\U0001F1FF"  # 国旗
            "\U00002702-\U000027B0"
            "\U000024C2-\U0001F251"
            "]+",
            flags=re.UNICODE
        )
        emoji_count = sum(len(emoji_pattern.findall(c)) for c in contents)

        # ハッシュタグカウント
        hashtag_count = sum(c.count("#") for c in contents)

        # 質問形式ツイート
        question_tweets = sum(1 for c in contents if "?" in c or "？" in c)
        statement_tweets = len(contents) - question_tweets

        # 頻出単語抽出（簡易版: 2文字以上のひらがな・カタカナ・漢字）
        word_pattern = re.compile(r"[ぁ-んァ-ヶー一-龥]{2,}")
        all_words = []
        for c in contents:
            all_words.extend(word_pattern.findall(c))

        common_words = [word for word, _ in Counter(all_words).most_common(10)]

        # トピック抽出（簡易版: キーワードベース）
        topics = self._extract_topics(contents)

        return {
            "avg_length": int(avg_length),
            "emoji_count": emoji_count,
            "hashtag_count": hashtag_count,
            "question_tweets": question_tweets,
            "statement_tweets": statement_tweets,
            "common_words": common_words,
            "topics": topics
        }

    def _extract_topics(self, contents: List[str]) -> List[str]:
        """
        簡易的なトピック抽出（キーワードベース）

        Args:
            contents: ツイート内容のリスト

        Returns:
            抽出されたトピックリスト
        """
        # トピックキーワード辞書
        topic_keywords = {
            "AI": ["AI", "人工知能", "機械学習", "ディープラーニング", "ChatGPT"],
            "プログラミング": ["プログラミング", "コード", "開発", "エンジニア", "Python", "JavaScript"],
            "ビジネス": ["ビジネス", "起業", "スタートアップ", "経営", "マーケティング"],
            "生産性": ["生産性", "効率", "時間管理", "習慣", "ライフハック"],
            "テクノロジー": ["テクノロジー", "技術", "イノベーション", "デジタル", "クラウド"],
            "心理学": ["心理", "認知", "行動", "モチベーション", "メンタル"],
            "科学": ["科学", "研究", "実験", "データ", "統計"],
            "健康": ["健康", "運動", "睡眠", "栄養", "ウェルネス"]
        }

        topic_counts = defaultdict(int)
        text = " ".join(contents)

        for topic, keywords in topic_keywords.items():
            for keyword in keywords:
                topic_counts[topic] += text.count(keyword)

        # カウント数でソートして上位を返す
        sorted_topics = sorted(topic_counts.items(), key=lambda x: x[1], reverse=True)
        return [topic for topic, count in sorted_topics if count > 0][:5]

    def extract_successful_features(self) -> Dict:
        """
        成功しているツイートの特徴を抽出

        Returns:
            成功パターンの特徴
        """
        # 上位20%のツイートを成功ツイートとして定義
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("SELECT COUNT(*) FROM tweets WHERE impressions > 0")
            total_count = cursor.fetchone()[0]

        if total_count == 0:
            return {
                "top_performing_pattern": {},
                "optimal_length": 0,
                "recommended_features": []
            }

        top_limit = max(10, int(total_count * 0.2))
        top_tweets = self.get_top_tweets(limit=top_limit, metric="engagement")

        if not top_tweets:
            return {
                "top_performing_pattern": {},
                "optimal_length": 0,
                "recommended_features": []
            }

        # パターン分析
        tweet_ids = [t["tweet_id"] for t in top_tweets]
        patterns = self.analyze_tweet_patterns(tweet_ids)

        # 推奨事項生成
        recommendations = []

        if patterns["avg_length"] > 0:
            recommendations.append(f"最適な文字数: {patterns['avg_length']}文字前後")

        if patterns["question_tweets"] > patterns["statement_tweets"]:
            recommendations.append("質問形式が効果的")
        else:
            recommendations.append("断定形式が効果的")

        if patterns["emoji_count"] > 0:
            avg_emoji = patterns["emoji_count"] / len(tweet_ids)
            recommendations.append(f"絵文字の使用: 平均{avg_emoji:.1f}個")

        if patterns["hashtag_count"] > 0:
            avg_hashtag = patterns["hashtag_count"] / len(tweet_ids)
            recommendations.append(f"ハッシュタグの使用: 平均{avg_hashtag:.1f}個")

        return {
            "top_performing_pattern": patterns,
            "optimal_length": patterns["avg_length"],
            "recommended_features": recommendations
        }

    def get_optimal_posting_time(self) -> List[str]:
        """
        過去のツイートの時間帯別エンゲージメント率を分析

        Returns:
            最適な投稿時間帯のリスト
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT posted_at, likes, retweets, replies, impressions
                FROM tweets
                WHERE posted_at IS NOT NULL AND impressions > 0
            """)
            rows = cursor.fetchall()

        if not rows:
            return []

        # 時間帯別のエンゲージメント率を計算
        hourly_engagement = defaultdict(list)

        for row in rows:
            posted_at_str = row[0]
            likes, retweets, replies, impressions = row[1], row[2], row[3], row[4]

            try:
                # ISO形式の日時をパース
                posted_at = datetime.fromisoformat(posted_at_str.replace("Z", "+00:00"))
                hour = posted_at.hour

                engagement_rate = (likes + retweets + replies) / impressions if impressions > 0 else 0
                hourly_engagement[hour].append(engagement_rate)
            except (ValueError, AttributeError):
                continue

        # 各時間帯の平均エンゲージメント率を計算
        avg_hourly_engagement = {
            hour: sum(rates) / len(rates)
            for hour, rates in hourly_engagement.items()
        }

        # エンゲージメント率でソート
        sorted_hours = sorted(
            avg_hourly_engagement.items(),
            key=lambda x: x[1],
            reverse=True
        )

        # 上位3つの時間帯を返す
        optimal_times = []
        for hour, _ in sorted_hours[:3]:
            start_hour = f"{hour:02d}:00"
            end_hour = f"{(hour + 1) % 24:02d}:00"
            optimal_times.append(f"{start_hour}-{end_hour}")

        return optimal_times

    def analyze_topic_performance(self) -> Dict:
        """
        トピック別のパフォーマンスを分析

        Returns:
            トピック別の統計情報
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT content, likes, retweets, replies
                FROM tweets
            """)
            rows = cursor.fetchall()

        if not rows:
            return {}

        # トピックキーワード辞書
        topic_keywords = {
            "AI": ["AI", "人工知能", "機械学習", "ディープラーニング", "ChatGPT"],
            "プログラミング": ["プログラミング", "コード", "開発", "エンジニア", "Python", "JavaScript"],
            "ビジネス": ["ビジネス", "起業", "スタートアップ", "経営", "マーケティング"],
            "生産性": ["生産性", "効率", "時間管理", "習慣", "ライフハック"],
            "テクノロジー": ["テクノロジー", "技術", "イノベーション", "デジタル", "クラウド"],
            "心理学": ["心理", "認知", "行動", "モチベーション", "メンタル"],
            "科学": ["科学", "研究", "実験", "データ", "統計"],
            "健康": ["健康", "運動", "睡眠", "栄養", "ウェルネス"]
        }

        topic_stats = defaultdict(lambda: {"count": 0, "total_likes": 0})

        for row in rows:
            content, likes, retweets, replies = row

            for topic, keywords in topic_keywords.items():
                if any(keyword in content for keyword in keywords):
                    topic_stats[topic]["count"] += 1
                    topic_stats[topic]["total_likes"] += likes

        # 平均いいね数を計算
        result = {}
        for topic, stats in topic_stats.items():
            if stats["count"] > 0:
                result[topic] = {
                    "count": stats["count"],
                    "avg_likes": stats["total_likes"] / stats["count"]
                }

        # 平均いいね数でソート
        return dict(sorted(result.items(), key=lambda x: x[1]["avg_likes"], reverse=True))

    def get_stats_summary(self) -> Dict:
        """
        全体統計サマリーを取得

        Returns:
            統計サマリー
        """
        with sqlite3.connect(self.db_path) as conn:
            cursor = conn.cursor()
            cursor.execute("""
                SELECT
                    COUNT(*) as total_tweets,
                    AVG(likes) as avg_likes,
                    AVG(retweets) as avg_retweets,
                    AVG(replies) as avg_replies,
                    MAX(likes) as max_likes,
                    SUM(impressions) as total_impressions
                FROM tweets
            """)
            row = cursor.fetchone()

        return {
            "total_tweets": row[0] or 0,
            "avg_likes": round(row[1] or 0, 2),
            "avg_retweets": round(row[2] or 0, 2),
            "avg_replies": round(row[3] or 0, 2),
            "max_likes": row[4] or 0,
            "total_impressions": row[5] or 0
        }
