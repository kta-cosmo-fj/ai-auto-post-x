# Twitter Feedback Collector

Twitter API v2を使用して、自分の過去ツイートのエンゲージメントデータ（いいね、RT、返信）を効率的に収集し、SQLiteデータベースに蓄積するPythonモジュールです。

## 特徴

- **効率的なAPI利用**: Twitter API Free tier（月1,500リクエスト制限）に対応
- **自動レート制限処理**: APIレート制限を自動で処理しリトライ
- **時系列データ蓄積**: エンゲージメントの変化を追跡可能
- **バッチ処理対応**: 1日1回の定期実行に最適化
- **SQLite保存**: ローカルにデータを蓄積し分析可能

## インストール

### 1. 依存関係のインストール

```bash
pip install -r requirements.txt
```

必要なパッケージ:
- `tweepy>=4.14.0` - Twitter API v2クライアント
- `python-dotenv>=1.0.0` - 環境変数管理

### 2. 環境変数の設定

`.env` ファイルに以下の環境変数を追加してください：

```bash
# Twitter API v2 認証情報（いずれかが必要）

# オプション1: Bearer Token（推奨 - v2 API専用）
X_BEARER_TOKEN=your_bearer_token_here

# オプション2: OAuth 1.0a 認証情報（既存の認証情報を使用する場合）
X_API_KEY=your_api_key_here
X_API_SECRET=your_api_secret_here
X_ACCESS_TOKEN=your_access_token_here
X_ACCESS_TOKEN_SECRET=your_access_token_secret_here
```

#### Twitter API認証情報の取得方法

1. [Twitter Developer Portal](https://developer.twitter.com/en/portal/dashboard) にアクセス
2. プロジェクトとアプリを作成
3. "Keys and tokens" タブから以下を取得：
   - **Bearer Token** (推奨): v2 API専用のトークン
   - または **API Key & Secret** + **Access Token & Secret**: OAuth 1.0a認証

### 3. データベースの初期化

```bash
python init_db.py
```

データベースをリセットする場合：

```bash
python init_db.py --reset
```

統計情報を表示：

```bash
python init_db.py --stats
```

## 使い方

### 基本的な使い方

#### 1. 最近のツイートを収集

```bash
# 過去7日間のツイートを収集
python example_collect.py collect

# 過去30日間のツイートを収集
python example_collect.py collect --days 30

# 最大50件まで収集
python example_collect.py collect --days 7 --max-tweets 50
```

#### 2. 古いツイートのエンゲージメントを一括更新

```bash
# 24時間更新されていないツイートを更新
python example_collect.py update

# 48時間更新されていないツイートを更新
python example_collect.py update --hours 48
```

#### 3. 特定のツイートの詳細を表示

```bash
python example_collect.py show <tweet_id>
```

### Pythonコードでの使用例

```python
from modules.feedback_collector import FeedbackCollector

# FeedbackCollectorを初期化
collector = FeedbackCollector()

# 1. 最近のツイートを収集（過去7日間）
tweets = collector.collect_recent_tweets(days=7)
print(f"Collected {len(tweets)} tweets")

# 2. 各ツイートのエンゲージメント情報を収集
for tweet in tweets:
    tweet_id = tweet['tweet_id']

    # エンゲージメント情報を更新
    engagement = collector.collect_tweet_engagement(tweet_id)
    print(f"Tweet {tweet_id}: {engagement['likes']} likes, {engagement['retweets']} retweets")

    # 返信を収集（最大5件）
    replies = collector.collect_replies(tweet_id, max_results=5)
    print(f"  {len(replies)} replies")

# 3. エンゲージメント履歴を取得
history = collector.get_engagement_history(tweet_id)
for snapshot in history:
    print(f"Snapshot at {snapshot['snapshot_at']}: {snapshot['likes']} likes")

# 4. データベースの統計情報を取得
stats = collector.get_statistics()
print(f"Total tweets: {stats['total_tweets']}")
print(f"Average likes: {stats['avg_likes']:.2f}")
```

## データベーススキーマ

### tweets テーブル

ツイートの基本情報とエンゲージメント情報を保存します。

| カラム名 | 型 | 説明 |
|---------|-----|-----|
| tweet_id | TEXT | ツイートID（主キー） |
| content | TEXT | ツイート本文 |
| posted_at | TIMESTAMP | 投稿日時 |
| likes | INTEGER | いいね数 |
| retweets | INTEGER | リツイート数 |
| replies | INTEGER | 返信数 |
| impressions | INTEGER | インプレッション数 |
| created_at | TIMESTAMP | レコード作成日時 |
| updated_at | TIMESTAMP | レコード更新日時 |

### replies テーブル

ツイートへの返信情報を保存します。

| カラム名 | 型 | 説明 |
|---------|-----|-----|
| reply_id | TEXT | 返信ID（主キー） |
| tweet_id | TEXT | 元ツイートID（外部キー） |
| author_id | TEXT | 返信者のユーザーID |
| author_username | TEXT | 返信者のユーザー名 |
| content | TEXT | 返信本文 |
| replied_at | TIMESTAMP | 返信日時 |
| created_at | TIMESTAMP | レコード作成日時 |

### engagement_snapshots テーブル

エンゲージメントの時系列データを保存します。

| カラム名 | 型 | 説明 |
|---------|-----|-----|
| id | INTEGER | スナップショットID（主キー） |
| tweet_id | TEXT | ツイートID（外部キー） |
| likes | INTEGER | いいね数 |
| retweets | INTEGER | リツイート数 |
| replies | INTEGER | 返信数 |
| impressions | INTEGER | インプレッション数 |
| snapshot_at | TIMESTAMP | スナップショット取得日時 |

## API制限について

### Twitter API Free Tier の制限

- **月間リクエスト数**: 1,500リクエスト
- **推奨実行頻度**: 1日1回（約50リクエスト/日以内）

### リクエスト数の見積もり

1回の実行で使用するリクエスト数の例：

- `collect_recent_tweets()`: 1リクエスト
- `collect_tweet_engagement()`: 1リクエスト/ツイート
- `collect_replies()`: 1リクエスト/ツイート（※Free tierでは利用不可の可能性あり）

例：過去7日間の10ツイートを収集し、それぞれのエンゲージメントを更新する場合
- 合計: 1（ツイート収集） + 10（エンゲージメント） = 11リクエスト

### レート制限対応

- 自動リトライ機能により、レート制限に達した場合は自動的に待機して再試行します
- リトライ間隔: 1分 → 2分 → 3分（最大3回）

## エラーハンドリング

このモジュールは以下のエラーに対応しています：

1. **ネットワークエラー**: 自動リトライ
2. **APIレート制限**: 待機後に自動リトライ
3. **認証エラー**: エラーメッセージを表示して終了
4. **データベースエラー**: トランザクションのロールバック

## 定期実行の設定

### cron（Linux/Mac）

1日1回午前2時に実行する例：

```cron
0 2 * * * cd /path/to/ai-auto-post-x && /usr/bin/python3 example_collect.py collect >> logs_auto/feedback_collector.log 2>&1
```

### タスクスケジューラ（Windows）

1. タスクスケジューラを開く
2. 新しいタスクを作成
3. トリガー: 毎日午前2時
4. アクション: `python example_collect.py collect`

## テスト

ユニットテストを実行：

```bash
python -m pytest tests/test_feedback_collector.py -v
```

または：

```bash
python tests/test_feedback_collector.py
```

## トラブルシューティング

### エラー: "Twitter API credentials not found"

- `.env` ファイルに `X_BEARER_TOKEN` または OAuth 1.0a の認証情報が設定されているか確認してください

### エラー: "Rate limit exceeded"

- API制限に達しました。しばらく待ってから再度実行してください
- 1日のリクエスト数を減らすことを検討してください

### エラー: "403 Forbidden" (返信収集時)

- Free tierでは検索APIが利用できない可能性があります
- `collect_replies()` の使用を控え、`collect_tweet_engagement()` のみ使用してください

### データベースがロックされる

- 別のプロセスがデータベースにアクセスしている可能性があります
- すべてのプロセスを終了してから再度実行してください

## ライセンス

このプロジェクトは MIT License の下で公開されています。

## 参考資料

- [Tweepy Documentation](https://docs.tweepy.org/en/stable/client.html)
- [Twitter API v2 Documentation](https://developer.twitter.com/en/docs/twitter-api)
- [Twitter API Free Tier](https://developer.twitter.com/en/portal/products/free)
