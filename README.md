# 🤖✨ AI Tweet Auto-Poster

> Gemini AIによる自動ツイート生成＆投稿システム with 重複検出

[![Python](https://img.shields.io/badge/Python-3.10%2B-blue.svg)](https://www.python.org/)
[![Google Cloud](https://img.shields.io/badge/Google%20Cloud-Vertex%20AI-4285F4.svg)](https://cloud.google.com/vertex-ai)
[![X API](https://img.shields.io/badge/X%20API-v2-000000.svg)](https://developer.x.com/)

## 概要

このスクリプトは以下の機能を提供します：

- **🤖 AI生成**: Google Vertex AI (Gemini) を使用して、テクノロジーに関する興味深いツイート内容を自動生成
- **🚀 自動投稿**: X (Twitter) APIを通じて生成されたツイートを自動投稿
- **🔍 重複検出**: 過去のツイートとの類似度をJaccard係数とSimHashで検出し、同じような内容の投稿を自動回避
- **📝 ログ管理**: ローテーション機能付きのログファイルで実行履歴を記録
- **💾 プレビュー保存**: 投稿内容をMarkdownとJSONの両形式で保存

## 📋 必要な環境

- **Python**: 3.10以上
- **ライブラリ**:
  - `tweepy` - X (Twitter) API クライアント
  - `vertexai` - Google Vertex AI SDK
  - `python-dotenv` - 環境変数管理
- **アカウント**:
  - Google Cloud Platform アカウント（Vertex AI API有効化済み）
  - X (Twitter) Developer アカウント（API アクセス権限付き）

## 🚀 インストール方法

### 1. リポジトリのクローン

```bash
git clone <your-repository-url>
cd twitter_ai
```

### 2. 依存関係のインストール

#### uvを使用する場合（推奨）:

```bash
uv sync
```

#### pipを使用する場合:

```bash
pip install tweepy google-cloud-aiplatform python-dotenv
```

## ⚙️ 環境設定

### 1. `.env`ファイルの作成

プロジェクトのルートディレクトリに`.env`ファイルを作成し、以下の環境変数を設定してください：

```env
# Google Cloud Platform
GOOGLE_CLOUD_PROJECT=your-gcp-project-id
GOOGLE_APPLICATION_CREDENTIALS=/your/path/to/adc/application_default_credentials.json
GOOGLE_CLOUD_LOCATION=global          # 任意。東京なら asia-northeast1
GEMINI_MODEL=gemini-2.5-flash
GOOGLE_GENAI_USE_VERTEXAI=True

# X (Twitter) API Credentials
X_API_KEY=your-api-key
X_API_SECRET=your-api-secret
X_ACCESS_TOKEN=your-access-token
X_ACCESS_TOKEN_SECRET=your-access-token-secret
```

### 2. 環境変数の詳細

| 変数名 | 説明 | 例 |
|--------|------|-----|
| `GOOGLE_CLOUD_PROJECT` | GCPプロジェクトID | `my-project-123456` |
| `GEMINI_MODEL` | 使用するGeminiモデル名 | `gemini-2.5-flash` |
| `GOOGLE_CLOUD_LOCATION` | GCPの利用するリージョン | `global` |
| `GOOGLE_APPLICATION_CREDENTIALS` | GCPのApplication Credentialsの格納場所 | `/your/path/to/adc/application_default_credentials.json` |
| `GOOGLE_GENAI_USE_VERTEXAI` | GCP Vertex AI API経由でGEMINIを利用する場合はTrue | `True` |
| `X_API_KEY` | Twitter API Key (Consumer Key) | `xxxxxxxxxxxxxxxxxxxx` |
| `X_API_SECRET` | Twitter API Secret (Consumer Secret) | `xxxxxxxxxxxxxxxxxxxx` |
| `X_ACCESS_TOKEN` | Twitter Access Token | `xxxxxxxxxxxxxxxxxxxx` |
| `X_ACCESS_TOKEN_SECRET` | Twitter Access Token Secret | `xxxxxxxxxxxxxxxxxxxx` |

### 3. Google Cloud Platform の認証設定

Application Default Credentials (ADC) を設定してください：

```bash
gcloud auth application-default login
```

または、サービスアカウントキーを使用する場合：

```bash
set GOOGLE_APPLICATION_CREDENTIALS=path\to\your\service-account-key.json
```

### 4. X (Twitter) Developer Portal の設定

1. [Twitter Developer Portal](https://developer.twitter.com/) にアクセス
2. プロジェクトとアプリを作成
3. API KeysとAccess Tokensを取得
4. App permissionsを「Read and Write」に設定

## 💻 使い方

### 基本的な実行方法

```bash
python auto_post.py
```

スクリプトは以下の処理を実行します：

1. Gemini AIに接続してツイート内容を生成
2. 生成された内容を140文字以内に調整
3. プレビューをMarkdownとJSONで保存
4. X (Twitter) に投稿
5. 投稿結果をログとファイルに記録

### 出力ファイル

実行後、以下のファイルが生成・更新されます：

#### `out_auto/tweets_preview.md`
投稿履歴を時系列で追記保存するMarkdownファイル：

```markdown
# Tweet Preview (2025-01-08T09:30:00+09:00)

AIの進化が加速中！量子コンピュータと組み合わせると、さらに驚異的な可能性が...

Posted: https://x.com/i/web/status/1234567890
```

#### `out_auto/tweets_payload.json`
最新の投稿データを常に上書き保存するJSONファイル：

```json
{
  "text": "AIの進化が加速中！量子コンピュータと組み合わせると...",
  "model": "gemini-1.5-flash-002",
  "generated_at": "2025-01-08T00:30:00.000000+00:00",
  "citations": [],
  "hashtags": null,
  "posted_at": "2025-01-08T00:30:05.123456+00:00",
  "tweet_id": "1234567890",
  "tweet_url": "https://x.com/i/web/status/1234567890"
}
```

#### `out_auto/dedup_index.json`
重複検出用のインデックスファイル（過去のツイートの軽量インデックス）：

```json
[
  {
    "norm": "あなたはxの投稿を生成するaiエージェントです",
    "simhash": 1234567890123456789
  }
]
```

このファイルには過去のツイートの正規化されたテキストとSimHashハッシュ値が保存され、新しいツイート生成時に類似度判定に使用されます。

#### `logs_auto/auto_post.log`
実行ログをローテーション保存（最大1MB、5世代保持）：

```
2025-01-08 09:30:00 [INFO] Prepared tweet text (138 chars).
2025-01-08 09:30:05 [INFO] Tweet posted: https://x.com/i/web/status/1234567890
```

## ⏰ 定期実行の設定

### Windows（タスクスケジューラ）

#### 1. タスクスケジューラを開く

```
Win + R → taskschd.msc → Enter
```

#### 2. 基本タスクの作成

1. 右側の「基本タスクの作成」をクリック
2. **名前**: `Twitter Auto Post`
3. **説明**: `Gemini AIを使用したツイート自動投稿`

#### 3. トリガーの設定

1. 「毎日」を選択
2. 開始日時と実行時刻を設定（例: 毎日 9:00）
3. 「詳細設定」で繰り返し間隔を設定可能（例: 3時間ごと）

#### 4. 操作の設定

1. 「プログラムの開始」を選択
2. **プログラム/スクリプト**:
   ```
   C:\path\to\twitter_ai\.venv\Scripts\python.exe
   ```
3. **引数の追加**:
   ```
   auto_post.py
   ```
4. **開始**:
   ```
   C:\path\to\twitter_ai
   ```

#### 5. 詳細オプション

- 「最上位の特権で実行する」をチェック
- 「タスクが失敗した場合の再起動の間隔」を設定（例: 5分）

### macOS/Linux（cron）

#### cronジョブの設定

```bash
crontab -e
```

以下を追加（毎日9時に実行）：

```cron
0 9 * * * cd /path/to/twitter_ai && /path/to/twitter_ai/.venv/bin/python auto_post.py
```

3時間ごとに実行する場合：

```cron
0 */3 * * * cd /path/to/twitter_ai && /path/to/twitter_ai/.venv/bin/python auto_post.py
```

#### launchdの使用（推奨）

`~/Library/LaunchAgents/com.user.twitter_ai.plist` を作成：

```xml
<?xml version="1.0" encoding="UTF-8"?>
<!DOCTYPE plist PUBLIC "-//Apple//DTD PLIST 1.0//EN" "http://www.apple.com/DTDs/PropertyList-1.0.dtd">
<plist version="1.0">
<dict>
    <key>Label</key>
    <string>com.user.twitter_ai</string>
    <key>ProgramArguments</key>
    <array>
        <string>/path/to/twitter_ai/.venv/bin/python</string>
        <string>/path/to/twitter_ai/auto_post.py</string>
    </array>
    <key>WorkingDirectory</key>
    <string>/path/to/twitter_ai</string>
    <key>StartCalendarInterval</key>
    <dict>
        <key>Hour</key>
        <integer>9</integer>
        <key>Minute</key>
        <integer>0</integer>
    </dict>
    <key>StandardOutPath</key>
    <string>/tmp/twitter_ai.out.log</string>
    <key>StandardErrorPath</key>
    <string>/tmp/twitter_ai.err.log</string>
</dict>
</plist>
```

読み込み：

```bash
launchctl load ~/Library/LaunchAgents/com.user.twitter_ai.plist
```

## 🎨 カスタマイズ

### プロンプトの変更

[`auto_post.py:275-280`](auto_post.py:275)のプロンプトを編集：

```python
base_prompt = (
    "あなたはXの投稿を生成するAIエージェントです。\n"
    "140文字以内でテクノロジーに関する興味深い事実を投稿してください。\n"
    "冒頭にスクロールを止めるようなフックを入れてください。\n"
    "絵文字は控えめに、具体性と独自性を重視してください。\n"
)
```

### 文字数制限の調整

[`auto_post.py:297`](auto_post.py:297)の`sanitize_and_limit()`の第2引数を変更：

```python
text = sanitize_and_limit(raw_text, 280)  # 280文字に変更
```

### 重複検出の調整

[`auto_post.py:284-285`](auto_post.py:284)で閾値を変更：

```python
JACCARD_TH = 0.80  # Jaccard係数の閾値（0.0-1.0、高いほど厳格）
HAMMING_TH = 3     # SimHashハミング距離の閾値（小さいほど厳格）
```

**パラメータの意味：**
- `JACCARD_TH`: 文字n-gramの重複率（0.80 = 80%以上一致で重複と判定）
- `HAMMING_TH`: SimHashのビット差分（3以下で類似と判定）

**調整例：**
- より厳格にする: `JACCARD_TH = 0.70`, `HAMMING_TH = 5`
- より緩くする: `JACCARD_TH = 0.90`, `HAMMING_TH = 2`

### ハッシュタグや出典URLの追加

[`auto_post.py:332-333`](auto_post.py:332)を編集：

```python
hashtags = "#AI #Tech #Innovation"
citations = [
    "https://example.com/source1",
    "https://example.com/source2"
]
```

### パス設定の変更

[`auto_post.py:22-24`](auto_post.py:22)を編集：

```python
BASE_DIR = pathlib.Path(r"C:\path\to\twitter_ai")
OUT_DIR = BASE_DIR / "output"  # 出力ディレクトリ名を変更
LOG_DIR = BASE_DIR / "logs"
```

## 🔧 トラブルシューティング

### よくあるエラーと対処法

#### `Missing env vars: GOOGLE_CLOUD_PROJECT`

**原因**: `.env`ファイルが読み込まれていない、または環境変数が設定されていない

**対処法**:
1. `.env`ファイルがプロジェクトルートに存在するか確認
2. 環境変数名のスペルミスがないか確認
3. `.env`ファイルの文字エンコーディングがUTF-8か確認

#### `Content generation failed`

**原因**: Vertex AI APIへの接続エラー、または認証エラー

**対処法**:
1. GCP認証が正しく設定されているか確認：
   ```bash
   gcloud auth application-default login
   ```
2. Vertex AI APIが有効化されているか確認
3. プロジェクトIDが正しいか確認
4. ネットワーク接続を確認

#### `Tweet post failed`

**原因**: X API認証エラー、または投稿制限

**対処法**:
1. X APIの認証情報が正しいか確認
2. App permissionsが「Read and Write」になっているか確認
3. APIレート制限に達していないか確認（15分待機）
4. 重複ツイートでないか確認

#### `Tweet text exceeded 140 chars; truncating`

**原因**: 生成されたテキストが140文字を超えた

**対処法**:
1. プロンプトに文字数制限をより明確に指示
2. [`sanitize_and_limit()`](auto_post.py:45)の`limit`引数を調整
3. 生成後に手動で編集したい場合は、投稿前にプレビューを確認

### ログの確認方法

#### Windows

```powershell
Get-Content logs\auto_post.log -Tail 20
```

または

```powershell
notepad logs\auto_post.log
```

#### macOS/Linux

```bash
tail -f logs/auto_post.log
```

### 終了コード

スクリプトは以下の終了コードを返します：

- `0`: 正常終了（投稿成功）
- `2`: 環境変数不足
- `3`: コンテンツ生成失敗
- `4`: ツイート投稿失敗

タスクスケジューラでこれらのコードを使用して、エラー時の通知や再試行を設定できます。

## ⚠️ 注意事項

### Twitter APIの利用制限

- **Free tier**: 1500ツイート/月（約50ツイート/日）
- **Basic tier**: 3000ツイート/月、10000リード/月
- レート制限: 15分あたり一定数の投稿制限あり

過度な投稿はアカウント停止につながる可能性があるため、適切な間隔を設定してください。

### 費用について

#### Google Cloud Platform (Vertex AI)

- Gemini 1.5 Flash: 入力 $0.075 / 100万トークン、出力 $0.30 / 100万トークン
- 1ツイート生成あたりの概算コスト: $0.001以下
- 月間1000ツイート生成でも $1程度

詳細は[Vertex AI料金ページ](https://cloud.google.com/vertex-ai/pricing)を参照してください。

#### X (Twitter) API

- Free tier: 無料
- Basic tier: $100/月
- Pro tier: $5000/月

### セキュリティ

1. **`.env`ファイルの管理**:
   - `.gitignore`に`.env`を追加済み
   - リポジトリに**絶対に**コミットしないこと
   - 定期的にAPIキーをローテーション

2. **ログファイルの取り扱い**:
   - ログには機密情報を含めない
   - 必要に応じてログディレクトリも`.gitignore`に追加

3. **アクセス制御**:
   - サービスアカウントには最小限の権限のみ付与
   - X APIキーは適切に保管

## ライセンス

このプロジェクトのライセンスについては、LICENSEファイルを参照してください。

## サポート

問題が発生した場合は、以下を確認してください：

1. `logs/auto_post.log`の内容
2. `out_auto/tweets_payload.json`の最終状態
3. 環境変数の設定

それでも解決しない場合は、GitHubのIssuesで報告してください。
