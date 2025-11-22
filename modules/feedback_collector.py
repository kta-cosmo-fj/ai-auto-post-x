# -*- coding: utf-8 -*-
"""
Twitter Feedback Collector

Twitter API v2を使用して、自分の過去ツイートのエンゲージメントデータを収集する
"""

import logging
import os
import time
from datetime import datetime, timedelta, timezone
from typing import Dict, List, Optional, Any

import tweepy
from dotenv import load_dotenv

from .db_manager import DBManager

# .env を読み込む
load_dotenv()

logger = logging.getLogger(__name__)


class FeedbackCollector:
    """Twitter API v2を使用してエンゲージメントデータを収集するクラス"""

    def __init__(self, db_path: str = "data/tweets.db"):
        """
        Args:
            db_path: データベースファイルのパス
        """
        self.db = DBManager(db_path)
        self._init_api_client()

    def _init_api_client(self) -> None:
        """Twitter API v2クライアントを初期化する"""
        # v2 API用のBearer Token
        bearer_token = os.getenv("X_BEARER_TOKEN")

        # v1.1互換のOAuth 1.0a認証情報
        api_key = os.getenv("X_API_KEY")
        api_secret = os.getenv("X_API_SECRET")
        access_token = os.getenv("X_ACCESS_TOKEN")
        access_token_secret = os.getenv("X_ACCESS_TOKEN_SECRET")

        # ユーザーIDの取得（環境変数または後でAPIから取得）
        user_id_from_env = os.getenv("X_USER_ID")

        # OAuth 1.0aの認証情報が揃っている場合（ユーザーコンテキストあり）
        has_oauth = all([api_key, api_secret, access_token, access_token_secret])

        # クライアントの初期化
        if has_oauth:
            # OAuth 1.0aを使用（ユーザーコンテキストあり、get_me()が使える）
            self.client = tweepy.Client(
                consumer_key=api_key,
                consumer_secret=api_secret,
                access_token=access_token,
                access_token_secret=access_token_secret,
            )
            logger.info("Initialized Twitter API v2 client with OAuth 1.0a")
        elif bearer_token:
            # Bearer Tokenのみ（アプリのみ認証、get_me()は使えない）
            self.client = tweepy.Client(bearer_token=bearer_token)
            logger.info("Initialized Twitter API v2 client with Bearer Token")
        else:
            raise ValueError(
                "Twitter API credentials not found. "
                "Set (X_API_KEY, X_API_SECRET, X_ACCESS_TOKEN, X_ACCESS_TOKEN_SECRET) "
                "or X_BEARER_TOKEN"
            )

        # ユーザーIDを取得
        if user_id_from_env:
            # 環境変数から取得（Bearer Token使用時に推奨）
            self.user_id = user_id_from_env
            logger.info(f"Using user ID from environment: {self.user_id}")
        elif has_oauth:
            # OAuth 1.0aの場合はAPIから取得可能
            try:
                me = self.client.get_me()
                if me and me.data:
                    self.user_id = me.data.id
                    logger.info(f"Authenticated as user ID: {self.user_id}")
                else:
                    raise ValueError("Failed to get user information from API")
            except Exception as e:
                logger.error(f"Failed to get user ID from API: {e}")
                raise ValueError(
                    "Failed to get user ID from API. "
                    "Please set X_USER_ID in your .env file"
                ) from e
        else:
            # Bearer TokenのみでユーザーIDが指定されていない場合
            raise ValueError(
                "X_USER_ID is required when using Bearer Token authentication. "
                "Get your user ID from https://tweeterid.com/ or your Twitter profile, "
                "and set it in your .env file as X_USER_ID=your_user_id_here"
            )

    def _handle_rate_limit(self, func, *args, max_retries: int = 3, **kwargs):
        """
        レート制限を処理して関数を実行する

        Args:
            func: 実行する関数
            max_retries: 最大リトライ回数
            *args, **kwargs: 関数に渡す引数

        Returns:
            関数の実行結果
        """
        for attempt in range(max_retries):
            try:
                return func(*args, **kwargs)
            except tweepy.TooManyRequests as e:
                if attempt < max_retries - 1:
                    wait_time = 60 * (attempt + 1)  # 1分、2分、3分...
                    logger.warning(
                        f"Rate limit exceeded. Waiting {wait_time} seconds... (attempt {attempt + 1}/{max_retries})"
                    )
                    time.sleep(wait_time)
                else:
                    logger.error("Rate limit exceeded. Max retries reached.")
                    raise
            except tweepy.errors.TwitterServerError as e:
                if attempt < max_retries - 1:
                    wait_time = 5 * (attempt + 1)
                    logger.warning(f"Twitter server error. Retrying in {wait_time} seconds...")
                    time.sleep(wait_time)
                else:
                    raise
        return None

    def collect_recent_tweets(self, days: int = 7, max_results: int = 100) -> List[Dict[str, Any]]:
        """
        最近のツイートを収集する

        Args:
            days: 何日前までのツイートを収集するか
            max_results: 取得する最大件数（1-100）

        Returns:
            ツイート情報の辞書のリスト
        """
        try:
            # 開始日時を計算
            start_time = datetime.now(timezone.utc) - timedelta(days=days)

            # ツイートを取得
            # tweet_fields: 取得するツイートのフィールド
            # max_results: 1リクエストで取得する最大件数（5-100）
            response = self._handle_rate_limit(
                self.client.get_users_tweets,
                id=self.user_id,
                start_time=start_time,
                tweet_fields=['created_at', 'public_metrics', 'text'],
                max_results=min(max_results, 100),
                exclude=['retweets', 'replies']  # 自分のオリジナルツイートのみ
            )

            if not response or not response.data:
                logger.info(f"No tweets found in the last {days} days")
                return []

            tweets = []
            for tweet in response.data:
                tweet_data = {
                    'tweet_id': str(tweet.id),
                    'content': tweet.text,
                    'posted_at': tweet.created_at.isoformat() if tweet.created_at else None,
                    'likes': tweet.public_metrics.get('like_count', 0) if tweet.public_metrics else 0,
                    'retweets': tweet.public_metrics.get('retweet_count', 0) if tweet.public_metrics else 0,
                    'replies': tweet.public_metrics.get('reply_count', 0) if tweet.public_metrics else 0,
                    'impressions': tweet.public_metrics.get('impression_count', 0) if tweet.public_metrics else 0,
                }
                tweets.append(tweet_data)

                # データベースに保存
                self.db.insert_tweet(tweet_data)

            logger.info(f"Collected {len(tweets)} tweets from the last {days} days")
            return tweets

        except Exception as e:
            logger.error(f"Error collecting recent tweets: {e}")
            raise

    def collect_tweet_engagement(self, tweet_id: str) -> Dict[str, Any]:
        """
        特定のツイートのエンゲージメント情報を収集する

        Args:
            tweet_id: ツイートID

        Returns:
            エンゲージメント情報の辞書
        """
        try:
            # ツイート情報を取得
            response = self._handle_rate_limit(
                self.client.get_tweet,
                id=tweet_id,
                tweet_fields=['created_at', 'public_metrics', 'text']
            )

            if not response or not response.data:
                logger.warning(f"Tweet {tweet_id} not found")
                return {}

            tweet = response.data
            tweet_data = {
                'tweet_id': str(tweet.id),
                'content': tweet.text,
                'posted_at': tweet.created_at.isoformat() if tweet.created_at else None,
                'likes': tweet.public_metrics.get('like_count', 0) if tweet.public_metrics else 0,
                'retweets': tweet.public_metrics.get('retweet_count', 0) if tweet.public_metrics else 0,
                'replies': tweet.public_metrics.get('reply_count', 0) if tweet.public_metrics else 0,
                'impressions': tweet.public_metrics.get('impression_count', 0) if tweet.public_metrics else 0,
            }

            # データベースに保存
            self.db.insert_tweet(tweet_data)

            # エンゲージメントスナップショットを記録
            engagement_data = {
                'likes': tweet_data['likes'],
                'retweets': tweet_data['retweets'],
                'replies': tweet_data['replies'],
                'impressions': tweet_data['impressions'],
            }
            self.db.insert_engagement_snapshot(tweet_id, engagement_data)

            logger.info(f"Collected engagement for tweet {tweet_id}")
            return tweet_data

        except Exception as e:
            logger.error(f"Error collecting engagement for tweet {tweet_id}: {e}")
            raise

    def collect_replies(self, tweet_id: str, max_results: int = 10) -> List[Dict[str, Any]]:
        """
        特定のツイートへの返信を収集する

        Args:
            tweet_id: ツイートID
            max_results: 取得する最大件数（1-100）

        Returns:
            返信情報の辞書のリスト
        """
        try:
            # Twitter API v2の検索クエリを使用して返信を取得
            # conversation_id フィールドを使用
            query = f"conversation_id:{tweet_id} is:reply"

            response = self._handle_rate_limit(
                self.client.search_recent_tweets,
                query=query,
                tweet_fields=['created_at', 'author_id', 'text', 'conversation_id'],
                expansions=['author_id'],
                user_fields=['username'],
                max_results=min(max_results, 100)
            )

            if not response or not response.data:
                logger.info(f"No replies found for tweet {tweet_id}")
                return []

            # ユーザー情報をマッピング
            users = {}
            if response.includes and 'users' in response.includes:
                for user in response.includes['users']:
                    users[user.id] = user.username

            replies = []
            for reply in response.data:
                reply_data = {
                    'reply_id': str(reply.id),
                    'tweet_id': tweet_id,
                    'author_id': str(reply.author_id),
                    'author_username': users.get(reply.author_id, 'unknown'),
                    'content': reply.text,
                    'replied_at': reply.created_at.isoformat() if reply.created_at else None,
                }
                replies.append(reply_data)

                # データベースに保存
                self.db.insert_reply(reply_data)

            logger.info(f"Collected {len(replies)} replies for tweet {tweet_id}")
            return replies

        except Exception as e:
            logger.error(f"Error collecting replies for tweet {tweet_id}: {e}")
            # 検索APIが使えない場合（Free tierの制限など）はエラーをログに記録して空リストを返す
            if "403" in str(e) or "Forbidden" in str(e):
                logger.warning(
                    f"Search API not available (likely Free tier limitation). "
                    f"Cannot collect replies for tweet {tweet_id}"
                )
                return []
            raise

    def save_to_db(self, data: Dict[str, Any]) -> None:
        """
        汎用的なデータ保存メソッド（後方互換性のため）

        Args:
            data: 保存するデータ
        """
        if 'tweet_id' in data and 'content' in data:
            self.db.insert_tweet(data)
        elif 'reply_id' in data:
            self.db.insert_reply(data)
        else:
            logger.warning("Unknown data format. Cannot save to database.")

    def get_engagement_history(self, tweet_id: str) -> List[Dict[str, Any]]:
        """
        ツイートのエンゲージメント履歴を取得する

        Args:
            tweet_id: ツイートID

        Returns:
            エンゲージメントスナップショットのリスト
        """
        return self.db.get_engagement_history(tweet_id)

    def batch_update_engagement(self, hours_since_last_update: int = 24) -> int:
        """
        最近更新されていないツイートのエンゲージメントを一括更新する

        Args:
            hours_since_last_update: 何時間更新されていないツイートを対象とするか

        Returns:
            更新したツイート数
        """
        tweets = self.db.get_tweets_without_recent_snapshot(hours=hours_since_last_update)

        if not tweets:
            logger.info("No tweets to update")
            return 0

        updated_count = 0
        for tweet in tweets:
            try:
                self.collect_tweet_engagement(tweet['tweet_id'])
                updated_count += 1
                # レート制限を考慮して少し待機
                time.sleep(1)
            except Exception as e:
                logger.error(f"Failed to update tweet {tweet['tweet_id']}: {e}")
                continue

        logger.info(f"Updated engagement for {updated_count}/{len(tweets)} tweets")
        return updated_count

    def get_statistics(self) -> Dict[str, Any]:
        """
        データベースの統計情報を取得する

        Returns:
            統計情報の辞書
        """
        return self.db.get_statistics()
