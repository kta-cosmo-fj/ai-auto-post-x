"""
Knowledge Base (RAG) Module

ChromaDBを使用したベクトルデータベースによるRAGシステム。
過去の返信内容や成功したツイートを保存し、関連する文脈を検索する。
"""

import os
from datetime import datetime
from typing import Dict, List, Optional
import chromadb
from chromadb.config import Settings
from sentence_transformers import SentenceTransformer


class KnowledgeBase:
    """
    ベクトルデータベースを使用した知識ベースクラス

    ChromaDBを使用して、過去の返信やツイートを保存・検索する。
    sentence-transformersを使って軽量な埋め込みを生成。
    """

    def __init__(self, db_path: str = "data/chroma_db"):
        """
        KnowledgeBaseの初期化

        Args:
            db_path: ChromaDBの保存先パス
        """
        self.db_path = db_path

        # ChromaDBクライアントの初期化
        self.client = chromadb.PersistentClient(
            path=db_path,
            settings=Settings(
                anonymized_telemetry=False,
                allow_reset=True
            )
        )

        # 軽量な埋め込みモデルの初期化
        # all-MiniLM-L6-v2: 384次元、高速、多言語対応
        self.embedding_model = SentenceTransformer('sentence-transformers/all-MiniLM-L6-v2')

        # コレクションの取得または作成
        self._initialize_collections()

    def _initialize_collections(self):
        """コレクションの初期化"""
        # 返信用コレクション
        try:
            self.replies_collection = self.client.get_collection(name="replies")
        except Exception:
            self.replies_collection = self.client.create_collection(
                name="replies",
                metadata={"description": "User replies and interactions"}
            )

        # 成功したツイート用コレクション
        try:
            self.tweets_collection = self.client.get_collection(name="successful_tweets")
        except Exception:
            self.tweets_collection = self.client.create_collection(
                name="successful_tweets",
                metadata={"description": "High engagement tweets"}
            )

    def add_reply(self, reply_id: str, content: str, metadata: Dict):
        """
        返信を知識ベースに追加

        Args:
            reply_id: 返信の一意なID
            content: 返信の内容
            metadata: メタデータ (author, tweet_id, replied_at, sentiment)
        """
        # 埋め込みの生成
        embedding = self.embedding_model.encode(content).tolist()

        # メタデータの準備（ChromaDBは文字列のみサポート）
        chroma_metadata = {
            "reply_id": str(reply_id),
            "tweet_id": str(metadata.get("tweet_id", "")),
            "author": str(metadata.get("author", "")),
            "replied_at": str(metadata.get("replied_at", datetime.now().isoformat())),
            "sentiment": str(metadata.get("sentiment", "neutral"))
        }

        try:
            # コレクションに追加
            self.replies_collection.add(
                ids=[reply_id],
                embeddings=[embedding],
                documents=[content],
                metadatas=[chroma_metadata]
            )
        except Exception as e:
            print(f"Error adding reply: {e}")
            # 既存の場合は更新
            try:
                self.replies_collection.update(
                    ids=[reply_id],
                    embeddings=[embedding],
                    documents=[content],
                    metadatas=[chroma_metadata]
                )
            except Exception as update_error:
                print(f"Error updating reply: {update_error}")

    def add_successful_tweet(self, tweet_id: str, content: str, engagement: Dict):
        """
        成功したツイートを知識ベースに追加

        Args:
            tweet_id: ツイートの一意なID
            content: ツイートの内容
            engagement: エンゲージメント情報 (likes, retweets, engagement_rate, posted_at)
        """
        # 埋め込みの生成
        embedding = self.embedding_model.encode(content).tolist()

        # メタデータの準備
        chroma_metadata = {
            "tweet_id": str(tweet_id),
            "likes": str(engagement.get("likes", 0)),
            "retweets": str(engagement.get("retweets", 0)),
            "engagement_rate": str(engagement.get("engagement_rate", 0.0)),
            "posted_at": str(engagement.get("posted_at", datetime.now().isoformat()))
        }

        try:
            # コレクションに追加
            self.tweets_collection.add(
                ids=[tweet_id],
                embeddings=[embedding],
                documents=[content],
                metadatas=[chroma_metadata]
            )
        except Exception as e:
            print(f"Error adding tweet: {e}")
            # 既存の場合は更新
            try:
                self.tweets_collection.update(
                    ids=[tweet_id],
                    embeddings=[embedding],
                    documents=[content],
                    metadatas=[chroma_metadata]
                )
            except Exception as update_error:
                print(f"Error updating tweet: {update_error}")

    def search_similar_replies(self, query: str, top_k: int = 5) -> List[Dict]:
        """
        類似する返信を検索

        Args:
            query: 検索クエリ
            top_k: 取得する件数

        Returns:
            類似する返信のリスト
        """
        # クエリの埋め込みを生成
        query_embedding = self.embedding_model.encode(query).tolist()

        # コレクションが空の場合は空リストを返す
        try:
            count = self.replies_collection.count()
            if count == 0:
                return []
        except Exception:
            return []

        # 類似検索
        try:
            results = self.replies_collection.query(
                query_embeddings=[query_embedding],
                n_results=min(top_k, count)
            )

            # 結果を整形
            similar_replies = []
            if results and results['documents'] and len(results['documents']) > 0:
                for i, doc in enumerate(results['documents'][0]):
                    similar_replies.append({
                        "content": doc,
                        "metadata": results['metadatas'][0][i] if results['metadatas'] else {},
                        "distance": results['distances'][0][i] if results.get('distances') else None
                    })

            return similar_replies
        except Exception as e:
            print(f"Error searching similar replies: {e}")
            return []

    def search_similar_tweets(self, query: str, top_k: int = 5) -> List[Dict]:
        """
        類似するツイートを検索

        Args:
            query: 検索クエリ
            top_k: 取得する件数

        Returns:
            類似するツイートのリスト
        """
        # クエリの埋め込みを生成
        query_embedding = self.embedding_model.encode(query).tolist()

        # コレクションが空の場合は空リストを返す
        try:
            count = self.tweets_collection.count()
            if count == 0:
                return []
        except Exception:
            return []

        # 類似検索
        try:
            results = self.tweets_collection.query(
                query_embeddings=[query_embedding],
                n_results=min(top_k, count)
            )

            # 結果を整形
            similar_tweets = []
            if results and results['documents'] and len(results['documents']) > 0:
                for i, doc in enumerate(results['documents'][0]):
                    similar_tweets.append({
                        "content": doc,
                        "metadata": results['metadatas'][0][i] if results['metadatas'] else {},
                        "distance": results['distances'][0][i] if results.get('distances') else None
                    })

            return similar_tweets
        except Exception as e:
            print(f"Error searching similar tweets: {e}")
            return []

    def get_context_for_generation(self, query: str = None, max_replies: int = 3, max_tweets: int = 2) -> str:
        """
        生成AIのための文脈を取得

        Args:
            query: 検索クエリ（Noneの場合は最新のものを取得）
            max_replies: 取得する返信の最大数
            max_tweets: 取得するツイートの最大数

        Returns:
            フォーマットされた文脈文字列
        """
        context_parts = []

        if query:
            # クエリベースの検索
            similar_replies = self.search_similar_replies(query, top_k=max_replies)
            similar_tweets = self.search_similar_tweets(query, top_k=max_tweets)
        else:
            # 最新のデータを取得
            similar_replies = []
            similar_tweets = []

        # 返信の文脈を追加
        if similar_replies:
            context_parts.append("## 関連する過去の返信:")
            for i, reply in enumerate(similar_replies, 1):
                context_parts.append(f"\n{i}. {reply['content']}")
                if reply.get('metadata'):
                    metadata = reply['metadata']
                    if metadata.get('sentiment'):
                        context_parts.append(f"   (感情: {metadata['sentiment']})")

        # ツイートの文脈を追加
        if similar_tweets:
            context_parts.append("\n## 成功したツイート例:")
            for i, tweet in enumerate(similar_tweets, 1):
                context_parts.append(f"\n{i}. {tweet['content']}")
                if tweet.get('metadata'):
                    metadata = tweet['metadata']
                    likes = metadata.get('likes', '0')
                    retweets = metadata.get('retweets', '0')
                    context_parts.append(f"   (❤️ {likes} RT {retweets})")

        return "\n".join(context_parts) if context_parts else ""

    def get_stats(self) -> Dict:
        """
        知識ベースの統計情報を取得

        Returns:
            統計情報の辞書
        """
        try:
            replies_count = self.replies_collection.count()
        except Exception:
            replies_count = 0

        try:
            tweets_count = self.tweets_collection.count()
        except Exception:
            tweets_count = 0

        return {
            "replies_count": replies_count,
            "tweets_count": tweets_count,
            "total_count": replies_count + tweets_count,
            "db_path": self.db_path
        }

    def reset(self):
        """
        知識ベースをリセット（全データ削除）

        警告: この操作は元に戻せません
        """
        try:
            self.client.delete_collection(name="replies")
            self.client.delete_collection(name="successful_tweets")
            self._initialize_collections()
            print("Knowledge base has been reset.")
        except Exception as e:
            print(f"Error resetting knowledge base: {e}")


# 使用例
if __name__ == "__main__":
    # KnowledgeBaseの初期化
    kb = KnowledgeBase()

    # 統計情報の表示
    print("Knowledge Base Stats:")
    stats = kb.get_stats()
    for key, value in stats.items():
        print(f"  {key}: {value}")

    # 返信の追加例
    kb.add_reply(
        reply_id="test_reply_001",
        content="機械学習のモデル選定について教えてください",
        metadata={
            "author": "user123",
            "tweet_id": "tweet_001",
            "replied_at": datetime.now().isoformat(),
            "sentiment": "neutral"
        }
    )

    # 成功したツイートの追加例
    kb.add_successful_tweet(
        tweet_id="tweet_success_001",
        content="今日のAI開発は順調です。新しいモデルのパフォーマンスが予想以上に良好でした！",
        engagement={
            "likes": 150,
            "retweets": 45,
            "engagement_rate": 0.15,
            "posted_at": datetime.now().isoformat()
        }
    )

    # 関連する文脈の取得例
    print("\n\nContext for 'AI開発':")
    context = kb.get_context_for_generation(query="AI開発")
    print(context)

    # 更新された統計情報
    print("\n\nUpdated Stats:")
    stats = kb.get_stats()
    for key, value in stats.items():
        print(f"  {key}: {value}")
