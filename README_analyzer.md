# Engagement Analyzer

エンゲージメントデータを分析し、成功パターンを抽出するモジュール

## 📋 概要

Engagement Analyzerは、X (Twitter) の投稿データを分析し、以下の機能を提供します：

- トップパフォーマンスツイートの抽出
- ツイートパターンの分析
- 成功パターンの特徴抽出
- 最適投稿時間の分析
- トピック別パフォーマンス分析

## 🚀 クイックスタート

### インストール

必要な依存ライブラリをインストールします：

```bash
pip install -r requirements.txt
```

### 基本的な使い方

```python
from modules.analyzer import EngagementAnalyzer

# アナライザーの初期化
analyzer = EngagementAnalyzer(db_path="data/tweets.db")

# ツイートデータの追加
analyzer.add_tweet(
    tweet_id="1234567890",
    content="AIの未来について考える",
    likes=100,
    retweets=20,
    replies=5,
    impressions=1000,
    posted_at="2025-01-01T12:00:00+00:00"
)

# トップツイートの取得
top_tweets = analyzer.get_top_tweets(limit=10, metric="likes")

# 成功パターンの抽出
features = analyzer.extract_successful_features()
print(features)
```

## 📚 主要機能

### 1. トップツイートの取得

```python
# いいね数でトップ10を取得
top_by_likes = analyzer.get_top_tweets(limit=10, metric="likes")

# エンゲージメント率でトップ10を取得
top_by_engagement = analyzer.get_top_tweets(limit=10, metric="engagement")

# リツイート数でトップ10を取得
top_by_retweets = analyzer.get_top_tweets(limit=10, metric="retweets")
```

**利用可能な指標:**
- `likes`: いいね数
- `retweets`: リツイート数
- `replies`: 返信数
- `engagement`: エンゲージメント率 `(likes + retweets + replies) / impressions`

### 2. ツイートパターンの分析

```python
# トップツイートのIDリストを取得
top_tweets = analyzer.get_top_tweets(limit=10, metric="likes")
tweet_ids = [t["tweet_id"] for t in top_tweets]

# パターンを分析
patterns = analyzer.analyze_tweet_patterns(tweet_ids)

print(f"平均文字数: {patterns['avg_length']}")
print(f"絵文字使用数: {patterns['emoji_count']}")
print(f"ハッシュタグ数: {patterns['hashtag_count']}")
print(f"質問形式: {patterns['question_tweets']}件")
print(f"頻出キーワード: {patterns['common_words']}")
print(f"主要トピック: {patterns['topics']}")
```

**分析結果:**
```python
{
    "avg_length": 120,
    "emoji_count": 5,
    "hashtag_count": 3,
    "question_tweets": 2,
    "statement_tweets": 8,
    "common_words": ["AI", "技術", "未来", ...],
    "topics": ["AI", "プログラミング", "ビジネス"]
}
```

### 3. 成功パターンの抽出

```python
features = analyzer.extract_successful_features()

print(f"最適文字数: {features['optimal_length']}")
print("推奨事項:")
for rec in features['recommended_features']:
    print(f"  - {rec}")
```

**出力例:**
```
最適文字数: 125
推奨事項:
  - 最適な文字数: 125文字前後
  - 質問形式が効果的
  - 絵文字の使用: 平均0.5個
  - ハッシュタグの使用: 平均0.3個
```

### 4. 最適投稿時間の分析

```python
optimal_times = analyzer.get_optimal_posting_time()

print("エンゲージメントが高い時間帯:")
for time_range in optimal_times:
    print(f"  - {time_range}")
```

**出力例:**
```
エンゲージメントが高い時間帯:
  - 09:00-10:00
  - 20:00-21:00
  - 12:00-13:00
```

### 5. トピック別パフォーマンス分析

```python
topic_performance = analyzer.analyze_topic_performance()

for topic, stats in topic_performance.items():
    print(f"{topic}: {stats['count']}件, 平均{stats['avg_likes']:.1f}いいね")
```

**出力例:**
```
AI: 15件, 平均120.5いいね
プログラミング: 12件, 平均95.3いいね
ビジネス: 10件, 平均85.0いいね
```

### 6. 統計サマリーの取得

```python
summary = analyzer.get_stats_summary()

print(f"総ツイート数: {summary['total_tweets']}")
print(f"平均いいね数: {summary['avg_likes']}")
print(f"最大いいね数: {summary['max_likes']}")
```

## 📊 レポート生成

分析レポートを自動生成できます：

```bash
# 標準出力にレポートを表示
python generate_report.py

# ファイルに保存
python generate_report.py --output reports/analysis.md

# カスタムデータベースを使用
python generate_report.py --db-path custom/path/tweets.db --output reports/custom_analysis.md
```

レポートには以下の情報が含まれます：

- 📊 全体統計
- 🏆 トップパフォーマンスツイート
- 🎯 成功パターン分析
- ⏰ 最適投稿時間
- 📚 トピック別パフォーマンス

## 🧪 テスト

テストスイートを実行：

```bash
# すべてのテストを実行
pytest tests/test_analyzer.py -v

# カバレッジ付きで実行
pytest tests/test_analyzer.py --cov=modules.analyzer --cov-report=html
```

## 📦 データベーススキーマ

```sql
CREATE TABLE tweets (
    tweet_id TEXT PRIMARY KEY,
    content TEXT NOT NULL,
    likes INTEGER DEFAULT 0,
    retweets INTEGER DEFAULT 0,
    replies INTEGER DEFAULT 0,
    impressions INTEGER DEFAULT 0,
    posted_at TEXT,
    created_at TEXT DEFAULT CURRENT_TIMESTAMP
);
```

## 🔧 依存ライブラリ

- `pandas>=2.0.0` (オプション: より高度な分析用)
- `numpy>=1.24.0` (オプション: 統計計算用)

基本機能は標準ライブラリのみで動作します。

## 💡 使用例

### 例1: データ収集と分析

```python
from modules.analyzer import EngagementAnalyzer

# 初期化
analyzer = EngagementAnalyzer()

# X API から取得したデータを追加
tweets_data = [
    {
        "tweet_id": "123",
        "content": "AI技術の最新トレンド",
        "likes": 150,
        "retweets": 30,
        "replies": 10,
        "impressions": 2000,
        "posted_at": "2025-01-15T10:00:00+00:00"
    },
    # ... more tweets
]

for tweet in tweets_data:
    analyzer.add_tweet(**tweet)

# 分析実行
top_tweets = analyzer.get_top_tweets(limit=10, metric="engagement")
features = analyzer.extract_successful_features()
optimal_times = analyzer.get_optimal_posting_time()

print("成功パターン:", features)
print("最適時間:", optimal_times)
```

### 例2: 定期的な分析レポート

```python
from modules.analyzer import EngagementAnalyzer
from datetime import datetime

def generate_weekly_report():
    analyzer = EngagementAnalyzer()

    # 統計取得
    summary = analyzer.get_stats_summary()
    top_tweets = analyzer.get_top_tweets(limit=5, metric="engagement")
    features = analyzer.extract_successful_features()

    # レポート生成
    report = f"""
    週次エンゲージメントレポート
    生成日時: {datetime.now()}

    総ツイート数: {summary['total_tweets']}
    平均いいね数: {summary['avg_likes']:.1f}

    トップ5ツイート:
    """

    for i, tweet in enumerate(top_tweets, 1):
        report += f"{i}. {tweet['content'][:50]}... ({tweet['likes']} likes)\n"

    print(report)

# 毎週実行
generate_weekly_report()
```

## 🤝 統合

### auto_post.py との統合例

```python
# auto_post.py に追加
from modules.analyzer import EngagementAnalyzer

def save_to_database(tweet_id, content, posted_at):
    """投稿後にデータベースに保存"""
    analyzer = EngagementAnalyzer()
    analyzer.add_tweet(
        tweet_id=tweet_id,
        content=content,
        likes=0,  # 初期値
        retweets=0,
        replies=0,
        impressions=0,
        posted_at=posted_at
    )

# 投稿成功後に呼び出す
# save_to_database(tweet_id, chosen_text, datetime.now(timezone.utc).isoformat())
```

## 📈 今後の拡張案

- [ ] リアルタイムエンゲージメント追跡
- [ ] 感情分析の統合
- [ ] A/Bテスト機能
- [ ] 予測モデルの実装
- [ ] ダッシュボードUI
- [ ] 詳細な自然言語処理 (MeCab等の統合)

## 📄 ライセンス

このプロジェクトはMITライセンスの下で公開されています。

## 🐛 トラブルシューティング

### データベースが見つからない

```python
# データベースディレクトリを作成
import os
os.makedirs("data", exist_ok=True)

# 初期化
analyzer = EngagementAnalyzer(db_path="data/tweets.db")
```

### データがない場合

レポート生成時にデータがない場合、まずツイートを追加してください：

```python
analyzer = EngagementAnalyzer()
analyzer.add_tweet(
    tweet_id="test123",
    content="テストツイート",
    likes=10,
    retweets=2,
    replies=1,
    impressions=100
)
```

## 📞 サポート

問題が発生した場合は、GitHubのIssueで報告してください。
