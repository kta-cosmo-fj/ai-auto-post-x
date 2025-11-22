# -*- coding: utf-8 -*-
# auto_post.py (OpenAI / Gemini 自動切替版)
import json
import logging
import os
import pathlib
import random
import re
import string
from collections import Counter
from datetime import datetime, timezone
from logging.handlers import RotatingFileHandler
from typing import Dict, Iterable, List, Optional, Tuple

import tweepy
from dotenv import load_dotenv
# OpenAI クライアント
from openai import OpenAI

# .env を読み込む
load_dotenv()

# ====== パス設定 ======
BASE_DIR = pathlib.Path(__file__).resolve().parent
OUT_DIR = BASE_DIR / "out_auto"
LOG_DIR = BASE_DIR / "logs_auto"
OUT_DIR.mkdir(parents=True, exist_ok=True)
LOG_DIR.mkdir(parents=True, exist_ok=True)

MD_PATH = OUT_DIR / "tweets_preview.md"
JSON_PATH = OUT_DIR / "tweets_payload.json"
LOG_PATH = LOG_DIR / "auto_post.log"
INDEX_PATH = OUT_DIR / "dedup_index.json"

# ====== ログ設定 ======
logger = logging.getLogger("auto_post")
logger.setLevel(logging.INFO)
handler = RotatingFileHandler(
    LOG_PATH, maxBytes=1_000_000, backupCount=5, encoding="utf-8"
)
formatter = logging.Formatter(
    "%(asctime)s [%(levelname)s] %(message)s", datefmt="%Y-%m-%d %H:%M:%S"
)
handler.setFormatter(formatter)
logger.addHandler(handler)

# ====== 生成バックエンド選択フラグ ======
# 0 = OpenAI, 1 = Gemini, -1 = 自動（環境変数の有無で選択）
PROVIDER_FLAG = int(os.getenv("PROVIDER_FLAG", "-1"))

# ====== 共通ユーティリティ ======
def sanitize_and_limit(text: str, limit: int = 140) -> str:
    """テキストを1行にまとめ、指定文字数以内に制限する"""
    if not text:
        return ""
    one_line = " ".join(text.split())
    if len(one_line) > limit:
        logger.warning("投稿テキストが%d文字を超えたため切り詰めます", limit)
        one_line = one_line[:limit]
    return one_line

def append_markdown_preview(
    text: str,
    hashtags: Optional[str],
    citations: Optional[List[str]],
    posted_url: Optional[str],
) -> None:
    """投稿内容をMarkdownファイルに追記する"""
    ts = datetime.now(timezone.utc).astimezone().isoformat(timespec="seconds")
    with MD_PATH.open("a", encoding="utf-8") as f:
        f.write(f"\n\n# Tweet Preview ({ts})\n\n")
        f.write(text.replace("\n", " ") + "\n\n")
        if hashtags:
            f.write(hashtags + "\n\n")
        if citations:
            for u in citations:
                f.write(f"- {u}\n")
            f.write("\n")
        if posted_url:
            f.write(f"Posted: {posted_url}\n")

def save_payload_json(payload: Dict) -> None:
    """投稿データをJSONファイルに保存する"""
    with JSON_PATH.open("w", encoding="utf-8") as f:
        json.dump(payload, f, ensure_ascii=False, indent=2)

# === 重複検出ユーティリティ ===
_PUNCT_TABLE = str.maketrans(
    {c: " " for c in (string.punctuation + "’“”‘「」『』（）()[]{}")}
)

def normalize(text: str) -> str:
    """テキストを正規化（小文字化、句読点削除、空白正規化）"""
    if not text:
        return ""
    t = text.strip().lower()
    t = re.sub(r"\s+", " ", t.translate(_PUNCT_TABLE))
    return t

def char_ngrams(s: str, n: int = 2) -> set:
    """文字列からn-gramセットを生成"""
    s = s.replace(" ", "")
    if len(s) < n:
        return {s} if s else set()
    return {s[i : i + n] for i in range(len(s) - n + 1)}

def jaccard(a: set, b: set) -> float:
    """2つの集合のJaccard係数を計算"""
    if not a or not b:
        return 0.0
    inter = len(a & b)
    if inter == 0:
        return 0.0
    return inter / len(a | b)


def simhash(tokens: Iterable[str]) -> int:
    """トークンリストからSimHashを計算"""
    v = [0] * 64
    for tok, cnt in Counter(tokens).items():
        h = hash(tok) & ((1 << 64) - 1)
        w = cnt
        for i in range(64):
            if (h >> i) & 1:
                v[i] += w
            else:
                v[i] -= w
    out = 0
    for i, val in enumerate(v):
        if val >= 0:
            out |= 1 << i
    return out


def hamming(a: int, b: int) -> int:
    """2つの整数のハミング距離を計算"""
    return (a ^ b).bit_count()

def load_existing_index() -> List[Dict]:
    """既存の重複検出インデックスをロードする"""
    if INDEX_PATH.exists():
        try:
            return json.loads(INDEX_PATH.read_text(encoding="utf-8"))
        except Exception:
            logger.warning(
                "%s の読み込みに失敗。MDファイルからインデックスを再構築します", INDEX_PATH.name
            )
    return []

def extract_past_texts_from_md(max_items: Optional[int] = None) -> List[str]:
    """Markdownファイルから過去の投稿テキストを抽出する"""
    if not MD_PATH.exists():
        return []
    lines = MD_PATH.read_text(encoding="utf-8", errors="ignore").splitlines()
    texts: List[str] = []
    i = 0
    while i < len(lines):
        if lines[i].startswith("# Tweet Preview"):
            j = i + 1
            while j < len(lines) and not lines[j].strip():
                j += 1
            if j < len(lines):
                texts.append(lines[j].strip())
                if max_items and len(texts) >= max_items:
                    break
            i = j
        else:
            i += 1
    return texts

def build_index_from_md() -> List[Dict]:
    """Markdownファイルから重複検出インデックスを構築する"""
    texts = extract_past_texts_from_md()
    index: List[Dict] = []
    for t in texts:
        norm = normalize(t)
        grams = char_ngrams(norm, 2)
        index.append({"norm": norm, "simhash": simhash(grams)})
    return index

def persist_index(index: List[Dict]) -> None:
    """インデックスをファイルに永続化する"""
    INDEX_PATH.write_text(
        json.dumps(index, ensure_ascii=False, indent=2), encoding="utf-8"
    )

def most_similar_info(
    candidate: str, index: List[Dict]
) -> Tuple[float, int, Optional[Dict]]:
    """候補テキストと最も類似する過去の投稿を見つける"""
    norm = normalize(candidate)
    grams = char_ngrams(norm, 2)
    sh = simhash(grams)
    best = (0.0, 64, None)
    for item in index:
        jac = jaccard(grams, char_ngrams(item["norm"], 2))
        ham = hamming(sh, int(item["simhash"]))
        if jac > best[0] or (jac == best[0] and ham < best[1]):
            best = (jac, ham, item)
    return best

def extract_block_terms(similar_norms: List[str], top_k: int = 8) -> List[str]:
    """類似テキストから回避すべきフレーズを抽出する"""
    cnt = Counter()
    for n in similar_norms:
        for g in char_ngrams(n, 2):
            cnt[g] += 1
    return [w for w, _ in cnt.most_common(top_k)]

def add_blocklist_to_prompt(prompt: str, block_terms: List[str]) -> str:
    """プロンプトに回避すべきフレーズを追加する"""
    if not block_terms:
        return prompt
    return (
        prompt
        + "\n次の短い文字列（話題・表現）に被らない新規性のある内容で書いてください:\n"
        + "、".join(block_terms[:12])
        + "\n"
    )

# ====== ポストバリエーション定義 ======
TOPICS = {
    "technology": {
        "name": "テクノロジー",
        "examples": ["AI", "プログラミング", "最新ガジェット", "セキュリティ", "クラウド", "Web開発"],
        "weight": 3,
    },
    "business": {
        "name": "ビジネス・起業",
        "examples": ["スタートアップ", "マーケティング", "生産性", "リーダーシップ", "経営戦略"],
        "weight": 2,
    },
    "psychology": {
        "name": "心理学・人間行動",
        "examples": ["認知バイアス", "習慣形成", "モチベーション", "意思決定", "コミュニケーション"],
        "weight": 2,
    },
    "science": {
        "name": "科学・自然",
        "examples": ["宇宙", "生物学", "物理学", "環境問題", "進化", "脳科学"],
        "weight": 2,
    },
    "history": {
        "name": "歴史・文化",
        "examples": ["世界史", "発明", "文化的発見", "歴史的事件", "人物伝"],
        "weight": 1,
    },
    "lifehack": {
        "name": "ライフハック・効率化",
        "examples": ["時間管理", "勉強法", "仕事術", "整理整頓", "習慣化"],
        "weight": 2,
    },
    "health": {
        "name": "健康・ウェルネス",
        "examples": ["睡眠", "運動", "栄養", "メンタルヘルス", "ストレス管理"],
        "weight": 1,
    },
}

POST_TYPES = {
    "fact": {
        "name": "事実・トリビア",
        "style": "意外な事実や興味深いトリビアを簡潔に紹介",
        "weight": 3,
    },
    "question": {
        "name": "質問形式",
        "style": "読者に問いかける形で興味を引く",
        "weight": 2,
    },
    "howto": {
        "name": "ハウツー・ティップス",
        "style": "実践的なアドバイスやコツを共有",
        "weight": 2,
    },
    "statistic": {
        "name": "統計・データ",
        "style": "具体的な数字やデータで説得力を持たせる",
        "weight": 2,
    },
    "comparison": {
        "name": "比較・対比",
        "style": "2つの概念やアイデアを対比させて気づきを与える",
        "weight": 2,
    },
    "story": {
        "name": "ストーリー・エピソード",
        "style": "短いエピソードや例え話で印象に残す",
        "weight": 1,
    },
    "quote": {
        "name": "洞察・金言",
        "style": "深い洞察や教訓を簡潔に伝える",
        "weight": 1,
    },
}

HOOKS = [
    # 質問系
    "知ってました？",
    "実は、",
    "意外かもしれませんが、",
    "なぜだと思いますか？",

    # 驚き系
    "信じられないけど、",
    "衝撃の事実：",
    "想像してみてください：",

    # 統計・数字系
    "調査によると、",
    "データが示すのは、",
    "○○%の人が知らない",

    # 対比系
    "多くの人は○○だと思ってるけど、実際は",
    "成功する人と失敗する人の違い：",

    # ストーリー系
    "ある研究で判明したこと：",
    "歴史が教えてくれること：",

    # 挑戦・行動喚起系
    "試してみて：",
    "今日から始められること：",
    "覚えておくべきこと：",

    # シンプル系（フックなし）
    "",
    "",
]

def generate_dynamic_prompt() -> str:
    """
    トピック、ポストタイプ、フックをランダムに選択して
    多様なプロンプトを生成する
    """
    # 重み付きランダム選択
    topic_keys = list(TOPICS.keys())
    topic_weights = [TOPICS[k]["weight"] for k in topic_keys]
    topic_key = random.choices(topic_keys, weights=topic_weights, k=1)[0]
    topic = TOPICS[topic_key]

    post_type_keys = list(POST_TYPES.keys())
    post_type_weights = [POST_TYPES[k]["weight"] for k in post_type_keys]
    post_type_key = random.choices(post_type_keys, weights=post_type_weights, k=1)[0]
    post_type = POST_TYPES[post_type_key]

    hook = random.choice(HOOKS)

    # プロンプトテンプレート
    prompt_parts = [
        f"以下の条件で140文字以内のXポストを作成してください：",
        f"",
        f"【トピック】{topic['name']}",
        f"（例：{', '.join(random.sample(topic['examples'], min(3, len(topic['examples']))))}）",
        f"",
        f"【スタイル】{post_type['name']} - {post_type['style']}",
    ]

    if hook:
        prompt_parts.append(f"【冒頭フック】「{hook}」で始めてください")

    prompt_parts.extend([
        "",
        "【要件】",
        "- 140文字以内",
        "- 具体性と独自性を重視",
        "- 絵文字は最小限（0-1個）",
        "- 読者の興味を引く内容",
        "- 自然で読みやすい日本語",
    ])

    return "\n".join(prompt_parts)

# ====== 生成バックエンド実装 ======
def generate_with_openai(base_prompt: str, model: str, api_key: str) -> str:
    """OpenAI APIを使用してテキストを生成する"""
    client = OpenAI(api_key=api_key)
    system_prompt = (
        "あなたはX（旧Twitter）の魅力的な投稿を生成する専門家です。\n"
        "読者の興味を引き、価値ある情報を簡潔に伝える投稿を作成してください。\n"
        "出力は純テキストのみで、余計な説明は不要です。"
    )
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

def generate_with_gemini(
    base_prompt: str, project_id: str, model_name: str, location: str = "us-central1"
) -> str:
    """Google Gemini APIを使用してテキストを生成する"""
    # 使う時だけ import（環境に vertexai が無い場合でも他経路は動かすため）
    try:
        import vertexai
        from vertexai.preview.generative_models import GenerativeModel
    except Exception as e:
        raise RuntimeError(f"Gemini ライブラリの読み込みに失敗しました: {e}")
    vertexai.init(project=project_id, location=location)
    model = GenerativeModel(model_name)
    resp = model.generate_content(base_prompt)
    return (getattr(resp, "text", "") or "").strip()

def choose_provider() -> Tuple[str, Dict[str, str]]:
    """
    使用するAIプロバイダーを選択する

    戻り値:
      provider: "openai" or "gemini"
      info:     使用モデルやキーなど（ログ/ペイロード用）

    ルール:
      - PROVIDER_FLAG == 0: OpenAI を優先。キー不足なら Gemini にフォールバック
      - PROVIDER_FLAG == 1: Gemini を優先。設定不足なら OpenAI にフォールバック
      - PROVIDER_FLAG それ以外（例: -1）: 自動（OpenAI → Gemini の順で利用可否を判定）
    """
    # OpenAI 側の設定
    openai_api_key = os.getenv("OPENAI_API_KEY") or ""
    openai_model = os.getenv("OPENAI_MODEL", "gpt-4o-mini")
    openai_ready = bool(openai_api_key)

    # Gemini 側の設定
    gcp_project = os.getenv("GOOGLE_CLOUD_PROJECT") or os.getenv("GCP_PROJECT_ID") or ""
    gemini_model = os.getenv("GEMINI_MODEL", "gemini-1.5-pro")
    gemini_ready = bool(gcp_project and gemini_model)

    # 優先度決定
    pref = PROVIDER_FLAG
    order: List[str]
    if pref == 0:
        order = ["openai", "gemini"]
    elif pref == 1:
        order = ["gemini", "openai"]
    else:
        order = ["openai", "gemini"]  # 自動: OpenAI を先に試す

    for p in order:
        if p == "openai" and openai_ready:
            return "openai", {"model": openai_model, "OPENAI_API_KEY": openai_api_key}
        if p == "gemini" and gemini_ready:
            return "gemini", {
                "model": gemini_model,
                "GOOGLE_CLOUD_PROJECT": gcp_project,
            }

    # どちらも不可
    missing_list = []
    if not openai_ready:
        missing_list.append("OPENAI_API_KEY")
    if not gemini_ready:
        missing_list.append("GOOGLE_CLOUD_PROJECT or GEMINI_MODEL")
    raise RuntimeError(
        "どの生成APIも利用可能ではありません。不足: " + ", ".join(missing_list)
    )


def main() -> int:
    """
    メイン処理：AI投稿を生成してXに投稿する

    Returns:
        int: 終了コード（0=成功、2=認証エラー、3=生成エラー、4=投稿エラー）
    """
    # === X(Twitter) 認証情報 ===
    x_api_key = os.getenv("X_API_KEY")
    x_api_secret = os.getenv("X_API_SECRET")
    x_access_token = os.getenv("X_ACCESS_TOKEN")
    x_access_token_secret = os.getenv("X_ACCESS_TOKEN_SECRET")

    missing_x = [
        k
        for k, v in {
            "X_API_KEY": x_api_key,
            "X_API_SECRET": x_api_secret,
            "X_ACCESS_TOKEN": x_access_token,
            "X_ACCESS_TOKEN_SECRET": x_access_token_secret,
        }.items()
        if not v
    ]
    if missing_x:
        logger.error("X API認証情報が不足しています: %s", ", ".join(missing_x))
        return 2

    # === 重複検出インデックスの準備 ===
    index = load_existing_index()
    if not index:
        index = build_index_from_md()
        persist_index(index)
        logger.info("重複検出インデックスを初期化しました (%d件)", len(index))
    else:
        md_texts = {normalize(t) for t in extract_past_texts_from_md()}
        known = {i["norm"] for i in index}
        new_norms = list(md_texts - known)
        if new_norms:
            for n in new_norms:
                grams = char_ngrams(n, 2)
                index.append({"norm": n, "simhash": simhash(grams)})
            persist_index(index)
            logger.info("重複検出インデックスを更新しました (+%d件)", len(new_norms))

    # === 生成 ===
    try:
        provider, info = choose_provider()
        # 動的プロンプト生成
        base_prompt = generate_dynamic_prompt()
        logger.info("Generated dynamic prompt for variety")

        MAX_ATTEMPTS = 5
        JACCARD_TH = 0.80
        HAMMING_TH = 3
        block_terms: List[str] = []
        chosen_text = ""
        last_text = ""

        for attempt in range(1, MAX_ATTEMPTS + 1):
            prompt = (
                add_blocklist_to_prompt(base_prompt, block_terms)
                if block_terms
                else base_prompt
            )

            if provider == "openai":
                raw = generate_with_openai(
                    prompt, info["model"], info["OPENAI_API_KEY"]
                )
            else:
                raw = generate_with_gemini(
                    prompt, info["GOOGLE_CLOUD_PROJECT"], info["model"]
                )

            last_text = sanitize_and_limit(raw, 140)

            jac, ham, nearest = most_similar_info(last_text, index)
            logger.info(
                "生成試行 %d/%d [%s]: 類似度=%.3f, ハミング距離=%d",
                attempt, MAX_ATTEMPTS, provider, jac, ham
            )

            if jac < JACCARD_TH and ham > HAMMING_TH:
                logger.info("✓ 新規性の高い投稿を生成しました")
                chosen_text = last_text
                break

            sims = []
            if nearest:
                sims.append(nearest["norm"])
            block_terms = extract_block_terms(sims, top_k=8)

        if not chosen_text:
            logger.warning("新規性の高い候補が見つからず、軽微な変更を適用します。")
            # 最後に生成されたテキストを使用し、軽微な調整を加える
            text = last_text or ""

            # 表現のバリエーションを増やすための置換候補
            variation_patterns = [
                (r"実は", "意外にも"),
                (r"知ってました", "ご存知でした"),
                (r"信じられない", "驚くべき"),
                (r"調査によると", "研究結果によると"),
                (r"データが示す", "統計から見えるのは"),
                (r"○○%", "約○割"),
            ]

            mutated = text
            # ランダムに1-2個の置換を適用
            for old, new in random.sample(variation_patterns, min(2, len(variation_patterns))):
                mutated = re.sub(old, new, mutated)

            chosen_text = sanitize_and_limit(mutated, 140)

        hashtags = None
        citations: List[str] = []

        payload = {
            "text": chosen_text,
            "provider": provider,
            "model": info["model"],
            "generated_at": datetime.now(timezone.utc).isoformat(),
            "citations": citations,
            "hashtags": hashtags,
        }
        append_markdown_preview(chosen_text, hashtags, citations, posted_url=None)
        save_payload_json(payload)

        logger.info(
            "投稿テキスト準備完了: %d文字 [%s/%s]",
            len(chosen_text),
            provider,
            info["model"],
        )

    except Exception as e:
        logger.exception("コンテンツ生成に失敗しました: %s", e)
        return 3

    # === X (Twitter) 投稿 ===
    try:
        client = tweepy.Client(
            consumer_key=x_api_key,
            consumer_secret=x_api_secret,
            access_token=x_access_token,
            access_token_secret=x_access_token_secret,
        )
        res = client.create_tweet(text=chosen_text)
        tweet_id = res.data.get("id")
        tweet_url = f"https://x.com/i/web/status/{tweet_id}" if tweet_id else None

        payload["posted_at"] = datetime.now(timezone.utc).isoformat()
        payload["tweet_id"] = tweet_id
        payload["tweet_url"] = tweet_url
        save_payload_json(payload)
        append_markdown_preview(chosen_text, hashtags, citations, posted_url=tweet_url)

        logger.info("✓ 投稿成功: %s", tweet_url)

        # 重複検出インデックスに追加
        try:
            norm = normalize(chosen_text)
            grams = char_ngrams(norm, 2)
            index.append({"norm": norm, "simhash": simhash(grams)})
            persist_index(index)
            logger.info("重複検出インデックスを更新しました (+1)")
        except Exception as e:
            logger.warning("重複検出インデックスの更新に失敗: %s", e)

        return 0

    except Exception as e:
        logger.exception("投稿に失敗しました: %s", e)
        return 4

if __name__ == "__main__":
    exit_code = main()
    raise SystemExit(exit_code)