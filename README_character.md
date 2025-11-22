# Character Manager - キャラクター管理システム

AI botのキャラクター設定を管理し、プロンプト生成に活用するモジュールです。

## 概要

Character Managerは、AI botに一貫した個性を持たせるための設定管理システムです。YAMLファイルでキャラクターの性格、話し方、興味分野、制約事項を定義し、それに基づいた動的なプロンプト生成を行います。

## 主な機能

- **キャラクター設定の管理**: YAMLファイルでキャラクター設定を一元管理
- **動的プロンプト生成**: キャラクター設定に基づいたシステムプロンプトと投稿プロンプトの生成
- **バリデーション**: 設定ファイルの妥当性チェック
- **複数テンプレート**: 異なるキャラクタータイプのテンプレートを提供
- **コンテキスト対応**: 過去の投稿パターンや時間帯を考慮したプロンプト生成

## インストール

```bash
pip install -r requirements.txt
```

必要なパッケージ:
- `pyyaml>=6.0`

## ファイル構成

```
ai-auto-post-x/
├── modules/
│   ├── __init__.py
│   └── character_manager.py      # Character Managerの実装
├── data/
│   ├── character.yaml             # デフォルトのキャラクター設定
│   └── templates/                 # キャラクターテンプレート集
│       ├── business_entrepreneur.yaml
│       ├── science_researcher.yaml
│       ├── casual_friendly.yaml
│       └── tech_professional.yaml
└── tests/
    └── test_character_manager.py  # テストケース
```

## 基本的な使い方

### 1. キャラクター設定の読み込み

```python
from modules.character_manager import CharacterManager

# デフォルトの設定ファイルを使用
manager = CharacterManager("data/character.yaml")

# キャラクター情報を取得
character = manager.get_character()
print(f"キャラクター名: {character.name}")
print(f"性格: {character.personality}")
```

### 2. システムプロンプトの生成

```python
# システムプロンプトを生成
system_prompt = manager.get_system_prompt()
print(system_prompt)

# LLMに送信する際に使用
# response = llm.chat([
#     {"role": "system", "content": system_prompt},
#     {"role": "user", "content": "投稿を作成してください"}
# ])
```

### 3. 投稿用プロンプトの生成

```python
# 基本的な投稿プロンプト
tweet_prompt = manager.generate_tweet_prompt()

# コンテキスト情報を含めた投稿プロンプト
context = {
    "successful_patterns": [
        "知ってました？AIは人間の感情を認識できるんです",
        "プログラミングのコツ：まず動くコードを書いて、それから最適化する"
    ],
    "recent_topics": ["AI", "機械学習", "Python"],
    "time_of_day": "09:30",
    "topic": "プログラミング",
    "post_type": "ハウツー"
}

tweet_prompt = manager.generate_tweet_prompt(context)
print(tweet_prompt)
```

### 4. キャラクター設定の更新

```python
# 性格の一部を更新
manager.update_character({
    "personality": "より活発で好奇心旺盛なキャラクター"
})

# 設定のバリデーション
if manager.validate_character_config():
    print("設定は有効です")
```

### 5. 設定の保存

```python
# 現在の設定を保存
manager.save_character("data/my_character.yaml")
```

## キャラクター設定ファイルの構造

```yaml
character:
  # 基本情報
  name: "AIちゃん"
  personality: "好奇心旺盛で親しみやすいテクノロジー愛好家"
  tone: "フレンドリーだが知的、カジュアルさと専門性のバランス"

  # 興味・関心分野
  interests:
    - AI・機械学習
    - クラウド技術
    - 開発者ツール
    - 業務効率化

  # 知識レベル
  knowledge_level: "中級〜上級エンジニア向け"

  # 話し方のスタイル
  speaking_style:
    sentence_ending:
      - "です"
      - "ます"
      - "だよ"
      - "ね"
    emoji_frequency: "moderate"  # low, moderate, high
    max_emoji_per_tweet: 2
    hashtag_usage: true

  # 制約事項
  constraints:
    max_tweet_length: 140
    avoid_topics:
      - "政治的発言"
      - "宗教的発言"
      - "攻撃的内容"
    preferred_time_slots:
      - "09:00-10:00"
      - "12:00-13:00"
      - "20:00-21:00"
```

## 用意されているテンプレート

### 1. デフォルト (character.yaml)
- **タイプ**: テクノロジー愛好家
- **特徴**: 技術に精通し、フレンドリーで親しみやすい
- **適用場面**: 技術系の情報発信

### 2. ビジネス・起業家 (business_entrepreneur.yaml)
- **タイプ**: ビジネスパーソン
- **特徴**: 実践的で結果重視、モチベーティング
- **適用場面**: ビジネス、起業、マーケティング関連

### 3. 科学・研究者 (science_researcher.yaml)
- **タイプ**: 科学愛好家
- **特徴**: 論理的で正確、科学的根拠を重視
- **適用場面**: 科学、研究、データサイエンス関連

### 4. カジュアル・フレンドリー (casual_friendly.yaml)
- **タイプ**: 友達のような存在
- **特徴**: 気さくで親しみやすい、日常的な話題
- **適用場面**: 一般的なライフハック、豆知識

### 5. テックプロフェッショナル (tech_professional.yaml)
- **タイプ**: ソフトウェアエンジニア
- **特徴**: 技術的に正確、ベストプラクティス重視
- **適用場面**: プログラミング、アーキテクチャ、開発手法

## テンプレートの使い方

```python
# テンプレートから読み込み
manager = CharacterManager("data/templates/business_entrepreneur.yaml")
character = manager.get_character()

# 必要に応じてカスタマイズ
manager.update_character({
    "name": "マイビジネスAI",
    "interests": ["SaaS", "スタートアップ", "グロースハック"]
})

# カスタマイズした設定を保存
manager.save_character("data/my_custom_character.yaml")
```

## 実装例: auto_post.py との統合

```python
from modules.character_manager import CharacterManager

# キャラクター設定を読み込み
char_manager = CharacterManager("data/character.yaml")

# 既存のgenerate_with_openai関数を拡張
def generate_with_character(base_prompt: str, model: str, api_key: str) -> str:
    """キャラクター設定を使った生成"""
    client = OpenAI(api_key=api_key)

    # キャラクターのシステムプロンプトを取得
    system_prompt = char_manager.get_system_prompt()

    resp = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": base_prompt},
        ],
        temperature=0.9,
        max_tokens=200,
    )
    return (resp.choices[0].message.content or "").strip()

# コンテキスト情報を使った高度なプロンプト生成
context = {
    "successful_patterns": extract_successful_tweets(),
    "recent_topics": extract_recent_topics(),
    "time_of_day": datetime.now().strftime("%H:%M")
}

tweet_prompt = char_manager.generate_tweet_prompt(context)
generated_text = generate_with_character(tweet_prompt, model, api_key)
```

## API リファレンス

### Character クラス

キャラクター設定を保持するデータクラス

**属性:**
- `name: str` - キャラクター名
- `personality: str` - 性格・個性
- `tone: str` - トーン・話し方の雰囲気
- `interests: List[str]` - 興味・関心分野
- `knowledge_level: str` - 知識レベル
- `speaking_style: Dict[str, Any]` - 話し方のスタイル
- `constraints: Dict[str, Any]` - 制約事項

**メソッド:**
- `to_dict() -> Dict[str, Any]` - 辞書形式に変換

### CharacterManager クラス

キャラクター設定を管理するクラス

**初期化:**
```python
CharacterManager(config_path: str = "data/character.yaml")
```

**主要メソッド:**

#### `load_character() -> Character`
キャラクター設定をYAMLファイルから読み込む

#### `get_character() -> Character`
現在のキャラクター設定を取得する

#### `get_system_prompt() -> str`
キャラクター設定に基づいたシステムプロンプトを生成する

#### `get_personality_description() -> str`
キャラクターの性格を簡潔に説明する文字列を返す

#### `update_character(updates: Dict[str, Any]) -> None`
キャラクター設定を部分的に更新する

#### `validate_character_config() -> bool`
現在のキャラクター設定が有効かどうかを検証する

#### `generate_tweet_prompt(context: Optional[Dict[str, Any]] = None) -> str`
キャラクター設定とコンテキストに基づいて投稿用プロンプトを生成する

**コンテキストパラメータ:**
- `successful_patterns: List[str]` - 過去の高エンゲージメントツイート
- `recent_topics: List[str]` - 最近の返信から抽出したトピック
- `time_of_day: str` - 投稿時刻 (例: "09:30")
- `topic: str` - 投稿トピック（任意）
- `post_type: str` - 投稿タイプ（任意）

#### `save_character(output_path: Optional[str] = None) -> None`
現在のキャラクター設定をYAMLファイルに保存する

## テスト

```bash
# すべてのテストを実行
python -m pytest tests/test_character_manager.py -v

# または unittest を使用
python tests/test_character_manager.py
```

## カスタマイズガイド

### 新しいキャラクターテンプレートの作成

1. `data/templates/` に新しいYAMLファイルを作成
2. 既存のテンプレートを参考に設定を記述
3. `CharacterManager` で読み込み

```yaml
character:
  name: "カスタムAI"
  personality: "あなたのキャラクターの性格"
  tone: "話し方のトーン"
  interests:
    - "興味1"
    - "興味2"
  knowledge_level: "知識レベル"
  speaking_style:
    sentence_ending: ["です", "ます"]
    emoji_frequency: "moderate"
    max_emoji_per_tweet: 2
  constraints:
    max_tweet_length: 140
    avoid_topics: ["避けるトピック"]
```

### プロンプト生成のカスタマイズ

`generate_tweet_prompt()` メソッドをオーバーライドまたは拡張することで、独自のプロンプト生成ロジックを実装できます。

## トラブルシューティング

### YAMLファイルが読み込めない

```python
# エラーメッセージを確認
try:
    manager = CharacterManager("data/character.yaml")
except FileNotFoundError as e:
    print(f"ファイルが見つかりません: {e}")
except ValueError as e:
    print(f"設定ファイルの形式が不正です: {e}")
```

### バリデーションエラー

```python
# バリデーション結果を確認
if not manager.validate_character_config():
    # ログを確認して問題を特定
    import logging
    logging.basicConfig(level=logging.DEBUG)
```

## ベストプラクティス

1. **一貫性**: キャラクター設定は定期的に見直し、一貫性を保つ
2. **テスト**: 新しい設定を追加した際は必ずテストを実行
3. **バージョン管理**: キャラクター設定ファイルをGitで管理
4. **ドキュメント**: カスタムキャラクターには説明を追加
5. **コンテキスト活用**: 過去の投稿パターンを分析し、コンテキストに反映

## ライセンス

このプロジェクトのライセンスに従います。

## 貢献

バグ報告や機能リクエストは、GitHubのIssuesでお願いします。
