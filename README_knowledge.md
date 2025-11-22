# Knowledge Base (RAG) システム

## 概要

このプロジェクトのKnowledge Baseは、**RAG (Retrieval-Augmented Generation)** を実装したシステムです。過去の返信内容や高エンゲージメントのツイートをベクトルデータベースに保存し、関連する文脈を検索して AI生成の品質を向上させます。

## 主な特徴

- **ローカル動作**: ChromaDBを使用し、外部サービス不要
- **軽量**: `sentence-transformers/all-MiniLM-L6-v2` (384次元) を使用
- **高速検索**: ベクトル類似度検索による高速な関連コンテンツ取得
- **多言語対応**: 日本語・英語の両方に対応

## アーキテクチャ

```
┌─────────────────────────────────────────────┐
│         Knowledge Base System               │
├─────────────────────────────────────────────┤
│                                             │
│  ┌──────────────┐      ┌──────────────┐   │
│  │   Replies    │      │   Tweets     │   │
│  │  Collection  │      │  Collection  │   │
│  └──────────────┘      └──────────────┘   │
│         │                      │           │
│         └──────────┬───────────┘           │
│                    │                        │
│         ┌──────────▼──────────┐            │
│         │   ChromaDB Client   │            │
│         └─────────────────────┘            │
│                                             │
│  ┌──────────────────────────────────────┐  │
│  │  Sentence Transformer Embeddings     │  │
│  │  (all-MiniLM-L6-v2)                  │  │
│  └──────────────────────────────────────┘  │
└─────────────────────────────────────────────┘
```

## インストール

### 1. 依存関係のインストール

```bash
pip install -r requirements.txt
```

必要なライブラリ:
- `chromadb>=0.4.0` - ベクトルデータベース
- `sentence-transformers>=2.2.0` - 埋め込みモデル

### 2. 初期化

```bash
python init_knowledge_base.py
```

サンプルデータ付きで初期化する場合:
```bash
python init_knowledge_base.py
```

既存のデータをリセットして初期化:
```bash
python init_knowledge_base.py --reset
```

## 使い方

### 基本的な使用例

```python
from modules.knowledge_base import KnowledgeBase
from datetime import datetime

# KnowledgeBaseの初期化
kb = KnowledgeBase()

# 1. 返信を追加
kb.add_reply(
    reply_id="reply_12345",
    content="機械学習のモデル選定について教えてください",
    metadata={
        "author": "user_name",
        "tweet_id": "tweet_67890",
        "replied_at": datetime.now().isoformat(),
        "sentiment": "neutral"
    }
)

# 2. 成功したツイートを追加
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

# 3. 類似する返信を検索
similar_replies = kb.search_similar_replies("機械学習", top_k=5)
for reply in similar_replies:
    print(f"Content: {reply['content']}")
    print(f"Distance: {reply['distance']}")

# 4. 類似するツイートを検索
similar_tweets = kb.search_similar_tweets("AI開発", top_k=5)
for tweet in similar_tweets:
    print(f"Content: {tweet['content']}")
    print(f"Likes: {tweet['metadata']['likes']}")

# 5. AI生成のための文脈を取得
context = kb.get_context_for_generation(query="AI開発")
print(context)

# 6. 統計情報を取得
stats = kb.get_stats()
print(f"Replies: {stats['replies_count']}")
print(f"Tweets: {stats['tweets_count']}")
print(f"Total: {stats['total_count']}")
```

## API リファレンス

### `KnowledgeBase` クラス

#### `__init__(db_path: str = "data/chroma_db")`
KnowledgeBaseを初期化します。

**パラメータ:**
- `db_path`: ChromaDBの保存先パス（デフォルト: "data/chroma_db"）

---

#### `add_reply(reply_id: str, content: str, metadata: Dict)`
返信を知識ベースに追加します。

**パラメータ:**
- `reply_id`: 返信の一意なID
- `content`: 返信の内容
- `metadata`: メタデータ
  - `author`: 返信者
  - `tweet_id`: 元ツイートのID
  - `replied_at`: 返信日時（ISO形式）
  - `sentiment`: 感情分析結果（positive/neutral/negative）

**使用例:**
```python
kb.add_reply(
    reply_id="r123",
    content="素晴らしい記事ですね！",
    metadata={
        "author": "user_abc",
        "tweet_id": "t456",
        "replied_at": "2025-01-15T10:30:00",
        "sentiment": "positive"
    }
)
```

---

#### `add_successful_tweet(tweet_id: str, content: str, engagement: Dict)`
高エンゲージメントのツイートを知識ベースに追加します。

**パラメータ:**
- `tweet_id`: ツイートの一意なID
- `content`: ツイートの内容
- `engagement`: エンゲージメント情報
  - `likes`: いいね数
  - `retweets`: リツイート数
  - `engagement_rate`: エンゲージメント率
  - `posted_at`: 投稿日時（ISO形式）

**使用例:**
```python
kb.add_successful_tweet(
    tweet_id="t789",
    content="AI技術の最新トレンド",
    engagement={
        "likes": 250,
        "retweets": 80,
        "engagement_rate": 0.25,
        "posted_at": "2025-01-15T14:20:00"
    }
)
```

---

#### `search_similar_replies(query: str, top_k: int = 5) -> List[Dict]`
クエリに類似する返信を検索します。

**パラメータ:**
- `query`: 検索クエリ
- `top_k`: 取得する件数（デフォルト: 5）

**戻り値:**
```python
[
    {
        "content": "返信の内容",
        "metadata": {"author": "...", ...},
        "distance": 0.123  # 類似度（小さいほど類似）
    },
    ...
]
```

---

#### `search_similar_tweets(query: str, top_k: int = 5) -> List[Dict]`
クエリに類似するツイートを検索します。

**パラメータ:**
- `query`: 検索クエリ
- `top_k`: 取得する件数（デフォルト: 5）

**戻り値:**
```python
[
    {
        "content": "ツイートの内容",
        "metadata": {"likes": 100, "retweets": 30, ...},
        "distance": 0.234
    },
    ...
]
```

---

#### `get_context_for_generation(query: str = None, max_replies: int = 3, max_tweets: int = 2) -> str`
AI生成のための文脈を取得します。

**パラメータ:**
- `query`: 検索クエリ（Noneの場合は最新のものを取得）
- `max_replies`: 取得する返信の最大数（デフォルト: 3）
- `max_tweets`: 取得するツイートの最大数（デフォルト: 2）

**戻り値:**
フォーマットされた文脈文字列

**使用例:**
```python
context = kb.get_context_for_generation(query="機械学習")
# 出力:
# ## 関連する過去の返信:
#
# 1. 機械学習のモデル選定について教えてください
#    (感情: neutral)
#
# ## 成功したツイート例:
#
# 1. 今日のAI開発は順調です...
#    (❤️ 150 RT 45)
```

---

#### `get_stats() -> Dict`
知識ベースの統計情報を取得します。

**戻り値:**
```python
{
    "replies_count": 10,
    "tweets_count": 5,
    "total_count": 15,
    "db_path": "data/chroma_db"
}
```

---

#### `reset()`
知識ベースをリセット（全データ削除）します。

**警告:** この操作は元に戻せません。

## データ構造

### 返信のメタデータ

```python
reply_metadata = {
    "reply_id": "r12345",           # 返信ID
    "tweet_id": "t67890",           # 元ツイートのID
    "author": "user_name",          # 返信者
    "replied_at": "2025-01-15T...", # 返信日時（ISO形式）
    "sentiment": "positive"         # 感情（positive/neutral/negative）
}
```

### ツイートのメタデータ

```python
tweet_metadata = {
    "tweet_id": "t12345",           # ツイートID
    "likes": 150,                   # いいね数
    "retweets": 45,                 # リツイート数
    "engagement_rate": 0.15,        # エンゲージメント率
    "posted_at": "2025-01-15T..."   # 投稿日時（ISO形式）
}
```

## テスト

テストを実行:

```bash
python -m pytest tests/test_knowledge_base.py -v
```

または:

```bash
python tests/test_knowledge_base.py
```

## パフォーマンス

### 埋め込みモデル

- **モデル**: `sentence-transformers/all-MiniLM-L6-v2`
- **次元数**: 384次元
- **速度**: 高速（CPUでも実用的）
- **サイズ**: 約80MB
- **言語**: 多言語対応（日本語・英語）

### ベクトルデータベース

- **DB**: ChromaDB
- **ストレージ**: ローカルファイルシステム
- **検索速度**: O(log n)
- **メモリ効率**: 高い

## ディレクトリ構造

```
ai-auto-post-x/
├── modules/
│   ├── __init__.py
│   └── knowledge_base.py        # KnowledgeBaseクラス
├── tests/
│   ├── __init__.py
│   └── test_knowledge_base.py   # ユニットテスト
├── data/
│   └── chroma_db/               # ChromaDBの保存先
├── init_knowledge_base.py       # 初期化スクリプト
├── requirements.txt             # 依存関係
└── README_knowledge.md          # このファイル
```

## トラブルシューティング

### Q: ChromaDBが初期化できない

**A:** 既存のデータベースが壊れている可能性があります。以下を試してください:

```bash
# データベースをリセット
python init_knowledge_base.py --reset

# または手動で削除
rm -rf data/chroma_db
python init_knowledge_base.py
```

### Q: 検索結果が空

**A:** データベースが空の可能性があります。統計情報を確認してください:

```python
kb = KnowledgeBase()
print(kb.get_stats())
```

### Q: メモリ不足エラー

**A:** `top_k` パラメータを小さくするか、バッチ処理を検討してください:

```python
# 取得件数を減らす
results = kb.search_similar_replies("query", top_k=3)
```

## 今後の拡張

- [ ] バッチ処理APIの追加
- [ ] 感情分析の自動化
- [ ] エンゲージメント予測機能
- [ ] 複数モデルのサポート
- [ ] クラウドストレージ連携

## ライセンス

MITライセンス

## 参考資料

- [ChromaDB Documentation](https://docs.trychroma.com/)
- [Sentence Transformers](https://www.sbert.net/)
- [RAG (Retrieval-Augmented Generation)](https://arxiv.org/abs/2005.11401)
