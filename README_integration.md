# Enhanced Tweet Generator - 統合ガイド

## 概要

Task 1-4のモジュールを統合した **Enhanced Tweet Generator** システムの統合ガイドです。

このシステムは以下のモジュールを統合しています：

- **Task 1**: Feedback Collector & Database Manager（フィードバック収集）
- **Task 2**: Character Manager（キャラクター設定管理）
- **Task 3**: Knowledge Base（RAG / ベクトル検索）
- **Task 4**: Engagement Analyzer（エンゲージメント分析）
- **Task 5**: Enhanced Tweet Generator（統合ジェネレータ）

## アーキテクチャ

```
┌─────────────────────────────────────────────────────┐
│        Enhanced Tweet Generator (Task 5)            │
│                                                     │
│  ┌──────────────┐  ┌──────────────┐  ┌──────────┐ │
│  │  Character   │  │  Knowledge   │  │ Analyzer │ │
│  │  Manager     │  │  Base (RAG)  │  │          │ │
│  │  (Task 2)    │  │  (Task 3)    │  │ (Task 4) │ │
│  └──────────────┘  └──────────────┘  └──────────┘ │
│         │                 │                 │      │
└─────────┼─────────────────┼─────────────────┼──────┘
          │                 │                 │
          ▼                 ▼                 ▼
    character.yaml    chroma_db/        tweets.db
                      (ChromaDB)         (SQLite)
```

## ファイル構成

```
ai-auto-post-x/
├── modules/
│   ├── enhanced_generator.py     [Task 5] 統合ジェネレータ
│   ├── character_manager.py      [Task 2] キャラクター管理
│   ├── knowledge_base.py          [Task 3] RAG / ベクトル検索
│   ├── analyzer.py                [Task 4] エンゲージメント分析
│   ├── feedback_collector.py      [Task 1] フィードバック収集
│   └── db_manager.py              [Task 1] データベース管理
│
├── auto_post_v2.py                [Task 5] 新バージョン自動投稿
├── auto_post.py                   [既存] 旧バージョン（互換性維持）
│
├── tests/
│   └── test_enhanced_generator.py [Task 5] 統合テスト
│
├── data/
│   ├── character.yaml             キャラクター設定
│   ├── tweets.db                  ツイートデータベース
│   └── chroma_db/                 ベクトルデータベース
│
└── README_integration.md          このドキュメント
```

## セットアップ

### 1. 依存関係のインストール

```bash
pip install -r requirements.txt
```

### 2. データディレクトリの作成

```bash
mkdir -p data
```

### 3. キャラクター設定ファイルの作成

`data/character.yaml` を作成します：

```yaml
character:
  name: "AI Assistant Bot"
  personality: "フレンドリーで知識豊富なAIアシスタント"
  tone: "親しみやすく、わかりやすい言葉で説明する"
  interests:
    - "AI技術"
    - "プログラミング"
    - "データサイエンス"
  knowledge_level: "専門的な知識を持ちながら、初心者にも理解しやすく説明できる"

  speaking_style:
    sentence_ending:
      - "です"
      - "ます"
    emoji_frequency: "moderate"  # low, moderate, high
    max_emoji_per_tweet: 2
    hashtag_usage: true

  constraints:
    max_tweet_length: 140
    preferred_time_slots:
      - "09:00-12:00"
      - "15:00-18:00"
      - "20:00-22:00"
    avoid_topics:
      - "政治"
      - "宗教"
```

### 4. 環境変数の設定

`.env` ファイルを作成：

```env
# OpenAI API
OPENAI_API_KEY=your_openai_api_key
OPENAI_MODEL=gpt-4o-mini

# X (Twitter) API
X_API_KEY=your_x_api_key
X_API_SECRET=your_x_api_secret
X_ACCESS_TOKEN=your_x_access_token
X_ACCESS_TOKEN_SECRET=your_x_access_token_secret

# オプション設定
TWEET_TOPIC=AI技術
DRY_RUN=false
```

## 使い方

### 基本的な使い方

#### 1. コマンドラインから実行

```bash
# 通常の投稿
python auto_post_v2.py

# ドライラン（投稿せずにテスト）
DRY_RUN=true python auto_post_v2.py

# トピックを指定
TWEET_TOPIC="AI技術" python auto_post_v2.py
```

#### 2. Pythonスクリプトから使用

```python
from modules.enhanced_generator import EnhancedTweetGenerator
from modules.character_manager import CharacterManager
from modules.knowledge_base import KnowledgeBase
from modules.analyzer import EngagementAnalyzer

# モジュールの初期化
char_mgr = CharacterManager(config_path="data/character.yaml")
kb = KnowledgeBase(db_path="data/chroma_db")
analyzer = EngagementAnalyzer(db_path="data/tweets.db")

# ジェネレータの作成
generator = EnhancedTweetGenerator(
    character_manager=char_mgr,
    knowledge_base=kb,
    analyzer=analyzer
)

# ツイート生成と投稿
tweet, result = generator.generate_and_post(
    topic="AI技術",
    dry_run=True  # テストモード
)

print(f"Generated: {tweet}")
print(f"Result: {result}")
```

### 高度な使い方

#### カスタムプロンプトの構築

```python
# コンテキスト情報を活用したプロンプト生成
prompt = generator.build_dynamic_prompt(
    topic="機械学習",
    use_context=True  # 過去の成功パターンを活用
)

# ツイート生成
tweet = generator.generate_tweet_with_context(
    topic="機械学習",
    temperature=0.8,  # 創造性の調整
    max_attempts=5    # 最大試行回数
)
```

#### ツイートの検証

```python
# 生成されたツイートを検証
is_valid = generator.validate_tweet(tweet)

if is_valid:
    print("✓ Tweet is valid")
else:
    print("✗ Tweet validation failed")
```

#### 統計情報の取得

```python
# システムの統計情報を取得
stats = generator.get_generation_stats()
print(f"Character: {stats['character_name']}")
print(f"Total Tweets: {stats['total_tweets']}")
print(f"Avg Likes: {stats['avg_likes']}")
```

## マイグレーションガイド

### `auto_post.py` から `auto_post_v2.py` への移行

#### 主な違い

| 機能 | auto_post.py | auto_post_v2.py |
|------|--------------|-----------------|
| プロンプト生成 | 固定テンプレート | 動的（キャラクター設定 + コンテキスト） |
| 過去のデータ活用 | 重複検出のみ | 成功パターン分析 + RAG検索 |
| キャラクター設定 | なし | YAML設定ファイルで管理 |
| エンゲージメント分析 | なし | 時間帯・トピック別分析 |
| 知識ベース | なし | ChromaDBによるベクトル検索 |

#### 移行手順

**Step 1**: データのバックアップ

```bash
cp -r out_auto out_auto_backup
cp -r logs_auto logs_auto_backup
```

**Step 2**: キャラクター設定の作成

現在の投稿スタイルを分析して `data/character.yaml` を作成します。

**Step 3**: 既存データの移行（オプション）

既存の `tweets_preview.md` からデータベースにインポート：

```python
from modules.analyzer import EngagementAnalyzer

analyzer = EngagementAnalyzer()

# 既存のツイートをインポート
# （実装例は scripts/migrate_data.py を参照）
```

**Step 4**: テスト実行

```bash
# ドライランでテスト
DRY_RUN=true python auto_post_v2.py
```

**Step 5**: 本番移行

```bash
# 本番環境で実行
python auto_post_v2.py
```

### 既存の `auto_post.py` との併用

両方を併用することも可能です：

```bash
# 旧バージョン
python auto_post.py

# 新バージョン
python auto_post_v2.py
```

出力ディレクトリは共有されるため、両方のログが同じ場所に保存されます。

## トラブルシューティング

### 問題: キャラクター設定が読み込めない

**原因**: `data/character.yaml` が存在しないか、形式が不正

**解決策**:
```bash
# 設定ファイルの確認
cat data/character.yaml

# サンプルからコピー
cp data/character.yaml.example data/character.yaml
```

### 問題: ChromaDB のエラー

**原因**: ChromaDB のバージョン不整合またはデータ破損

**解決策**:
```bash
# ChromaDBのリセット
rm -rf data/chroma_db
python -c "from modules.knowledge_base import KnowledgeBase; kb = KnowledgeBase()"
```

### 問題: OpenAI API エラー

**原因**: APIキーが無効または使用量制限

**解決策**:
```bash
# APIキーの確認
echo $OPENAI_API_KEY

# .envファイルの再読み込み
source .env
```

### 問題: ツイートが投稿されない

**原因**: X API認証情報の不足またはドライランモード

**解決策**:
```bash
# 環境変数の確認
env | grep X_

# ドライランモードの確認
echo $DRY_RUN

# ドライランモードの解除
unset DRY_RUN
```

## テスト

### ユニットテストの実行

```bash
# 全テストの実行
python -m pytest tests/

# 特定のテストのみ実行
python -m pytest tests/test_enhanced_generator.py

# カバレッジ付きで実行
python -m pytest --cov=modules tests/
```

### 手動テスト

```bash
# ドライランモードでテスト
DRY_RUN=true python auto_post_v2.py

# ログの確認
tail -f logs_auto/auto_post_v2.log
```

## パフォーマンスチューニング

### プロンプト生成の最適化

```python
# コンテキストを無効化して高速化
prompt = generator.build_dynamic_prompt(use_context=False)

# 取得するツイート数を調整
top_tweets = analyzer.get_top_tweets(limit=3)  # デフォルト: 5
```

### データベースの最適化

```bash
# SQLiteデータベースの最適化
sqlite3 data/tweets.db "VACUUM;"
```

### ChromaDBのメンテナンス

```python
from modules.knowledge_base import KnowledgeBase

kb = KnowledgeBase()
stats = kb.get_stats()

# 古いデータの削除（必要に応じて）
# kb.reset()  # 注意: 全データ削除
```

## ベストプラクティス

### 1. 定期的なデータ収集

```bash
# 毎日実行（例: cron）
0 */6 * * * cd /path/to/ai-auto-post-x && python scripts/collect_feedback.py
```

### 2. キャラクター設定の定期見直し

- 月1回、エンゲージメントデータを分析
- 成功パターンに基づいて `character.yaml` を更新

### 3. バックアップ戦略

```bash
# 日次バックアップスクリプト
#!/bin/bash
DATE=$(date +%Y%m%d)
tar -czf backup_${DATE}.tar.gz data/ out_auto/ logs_auto/
```

### 4. ログのモニタリング

```bash
# エラーログの監視
grep ERROR logs_auto/auto_post_v2.log

# 成功率の確認
grep "posted successfully" logs_auto/auto_post_v2.log | wc -l
```

## API リファレンス

### EnhancedTweetGenerator

```python
class EnhancedTweetGenerator:
    """統合型ツイートジェネレータ"""

    def __init__(
        self,
        character_manager: CharacterManager,
        knowledge_base: KnowledgeBase,
        analyzer: EngagementAnalyzer,
        openai_api_key: Optional[str] = None
    )

    def build_dynamic_prompt(
        self,
        topic: Optional[str] = None,
        use_context: bool = True
    ) -> str
        """動的プロンプトを構築"""

    def generate_tweet_with_context(
        self,
        topic: Optional[str] = None,
        temperature: float = 0.9,
        max_attempts: int = 3
    ) -> str
        """コンテキストを活用してツイートを生成"""

    def validate_tweet(self, tweet: str) -> bool
        """生成されたツイートを検証"""

    def post_and_record(
        self,
        tweet: str,
        x_credentials: Optional[Dict[str, str]] = None,
        dry_run: bool = False
    ) -> Dict
        """ツイートを投稿し、結果を記録"""

    def generate_and_post(
        self,
        topic: Optional[str] = None,
        dry_run: bool = False
    ) -> Tuple[str, Dict]
        """ツイートを生成して投稿"""

    def get_generation_stats(self) -> Dict
        """生成システムの統計情報を取得"""
```

## よくある質問（FAQ）

### Q1: auto_post.py と auto_post_v2.py のどちらを使うべきですか？

**A**: 新規プロジェクトでは `auto_post_v2.py` を推奨します。より高度な機能と拡張性を提供します。

### Q2: キャラクター設定をどのように調整すればよいですか？

**A**: `modules/analyzer.py` の分析結果を参考に、成功しているツイートのパターンを `character.yaml` に反映させてください。

### Q3: コストを抑えるにはどうすればよいですか？

**A**:
- `OPENAI_MODEL=gpt-4o-mini` を使用（デフォルト）
- `use_context=False` でプロンプトを簡素化
- `max_attempts=1` で試行回数を制限

### Q4: データはどこに保存されますか？

**A**:
- ツイートデータ: `data/tweets.db` (SQLite)
- 知識ベース: `data/chroma_db/` (ChromaDB)
- ログ: `logs_auto/`
- プレビュー: `out_auto/`

## サポート

問題が発生した場合は、以下を確認してください：

1. ログファイル: `logs_auto/auto_post_v2.log`
2. 環境変数の設定: `.env`
3. キャラクター設定: `data/character.yaml`

## ライセンス

このプロジェクトのライセンスについては、プロジェクトルートの LICENSE ファイルを参照してください。

---

**最終更新**: 2025-11-22
**バージョン**: 2.0.0
