#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Character Manager と auto_post.py の統合例

CharacterManagerを既存のauto_post.pyと統合する方法を示すサンプルコード
"""

import sys
from pathlib import Path

# プロジェクトルートをパスに追加
sys.path.insert(0, str(Path(__file__).parent))

from modules.character_manager import CharacterManager


def example_1_basic_integration():
    """例1: 基本的な統合 - システムプロンプトの置き換え"""
    print("=" * 70)
    print("例1: システムプロンプトの置き換え")
    print("=" * 70)
    print()

    # CharacterManagerを初期化
    char_manager = CharacterManager("data/character.yaml")

    # 既存のauto_post.pyのgenerate_with_openai関数を拡張する例
    print("【変更前】auto_post.pyのシステムプロンプト:")
    print("-" * 70)
    old_system_prompt = (
        "あなたはX（旧Twitter）の魅力的な投稿を生成する専門家です。\n"
        "読者の興味を引き、価値ある情報を簡潔に伝える投稿を作成してください。\n"
        "出力は純テキストのみで、余計な説明は不要です。"
    )
    print(old_system_prompt)
    print("-" * 70)
    print()

    print("【変更後】CharacterManagerのシステムプロンプト:")
    print("-" * 70)
    new_system_prompt = char_manager.get_system_prompt()
    print(new_system_prompt)
    print("-" * 70)
    print()

    print("【統合コード例】")
    print(
        """
def generate_with_openai_enhanced(base_prompt: str, model: str, api_key: str) -> str:
    client = OpenAI(api_key=api_key)

    # CharacterManagerからシステムプロンプトを取得
    char_manager = CharacterManager("data/character.yaml")
    system_prompt = char_manager.get_system_prompt()

    resp = client.chat.completions.create(
        model=model,
        messages=[
            {"role": "system", "content": system_prompt},  # ここが変更点
            {"role": "user", "content": base_prompt},
        ],
        temperature=0.9,
        max_tokens=200,
    )
    return (resp.choices[0].message.content or "").strip()
"""
    )
    print()


def example_2_context_aware_generation():
    """例2: コンテキスト対応の投稿生成"""
    print("=" * 70)
    print("例2: コンテキスト対応の投稿生成")
    print("=" * 70)
    print()

    char_manager = CharacterManager("data/character.yaml")

    # 過去の成功パターンを模擬
    successful_patterns = [
        "知ってました？Pythonは世界で最も人気のあるプログラミング言語の1つです",
        "AIの進化が止まらない！最新の研究では、AIが人間の感情を理解できるように",
    ]

    # 最近のトピックを模擬
    recent_topics = ["AI", "機械学習", "Python", "クラウド技術"]

    # コンテキスト情報
    context = {
        "successful_patterns": successful_patterns,
        "recent_topics": recent_topics,
        "time_of_day": "09:30",
    }

    # コンテキスト付きプロンプトを生成
    tweet_prompt = char_manager.generate_tweet_prompt(context)

    print("生成されたコンテキスト対応プロンプト:")
    print("-" * 70)
    print(tweet_prompt[:500] + "...")
    print("-" * 70)
    print()

    print("【統合コード例】")
    print(
        """
def main_enhanced():
    # CharacterManagerの初期化
    char_manager = CharacterManager("data/character.yaml")

    # 過去の成功パターンを抽出
    successful_patterns = extract_successful_tweets_from_md()

    # 最近のトピックを抽出
    recent_topics = extract_topics_from_recent_replies()

    # コンテキストを構築
    context = {
        "successful_patterns": successful_patterns[:3],
        "recent_topics": recent_topics[:5],
        "time_of_day": datetime.now().strftime("%H:%M")
    }

    # キャラクター設定とコンテキストに基づいたプロンプトを生成
    tweet_prompt = char_manager.generate_tweet_prompt(context)

    # AI生成
    generated_text = generate_with_openai_enhanced(tweet_prompt, model, api_key)

    return generated_text
"""
    )
    print()


def example_3_dynamic_character_switching():
    """例3: 動的なキャラクター切り替え"""
    print("=" * 70)
    print("例3: 動的なキャラクター切り替え")
    print("=" * 70)
    print()

    # 時間帯に応じてキャラクターを切り替える例
    import datetime

    current_hour = datetime.datetime.now().hour

    if 7 <= current_hour < 12:
        character_path = "data/templates/business_entrepreneur.yaml"
        time_context = "朝のビジネスパーソン向け"
    elif 12 <= current_hour < 18:
        character_path = "data/character.yaml"
        time_context = "昼の技術者向け"
    else:
        character_path = "data/templates/casual_friendly.yaml"
        time_context = "夜のリラックスタイム向け"

    print(f"現在時刻: {current_hour}時")
    print(f"選択されたキャラクター: {character_path}")
    print(f"コンテキスト: {time_context}")
    print()

    char_manager = CharacterManager(character_path)
    character = char_manager.get_character()

    print(f"キャラクター名: {character.name}")
    print(f"性格: {character.personality[:60]}...")
    print()

    print("【統合コード例】")
    print(
        """
def choose_character_by_time() -> str:
    hour = datetime.now().hour

    if 7 <= hour < 12:
        return "data/templates/business_entrepreneur.yaml"
    elif 12 <= hour < 18:
        return "data/character.yaml"
    else:
        return "data/templates/casual_friendly.yaml"

def main_with_dynamic_character():
    # 時間帯に応じたキャラクターを選択
    character_path = choose_character_by_time()
    char_manager = CharacterManager(character_path)

    # プロンプト生成と投稿
    tweet_prompt = char_manager.generate_tweet_prompt()
    generated_text = generate_with_openai_enhanced(tweet_prompt, model, api_key)

    return generated_text
"""
    )
    print()


def example_4_topic_based_character():
    """例4: トピックベースのキャラクター選択"""
    print("=" * 70)
    print("例4: トピックベースのキャラクター選択")
    print("=" * 70)
    print()

    # トピックとキャラクターのマッピング
    topic_to_character = {
        "ビジネス": "data/templates/business_entrepreneur.yaml",
        "科学": "data/templates/science_researcher.yaml",
        "技術": "data/templates/tech_professional.yaml",
        "日常": "data/templates/casual_friendly.yaml",
        "デフォルト": "data/character.yaml",
    }

    # デモ用のトピック
    demo_topic = "技術"

    character_path = topic_to_character.get(demo_topic, topic_to_character["デフォルト"])

    print(f"選択されたトピック: {demo_topic}")
    print(f"使用するキャラクター: {character_path}")
    print()

    char_manager = CharacterManager(character_path)
    character = char_manager.get_character()

    print(f"キャラクター名: {character.name}")
    print(f"興味分野: {', '.join(character.interests[:3])}")
    print()

    print("【統合コード例】")
    print(
        """
TOPIC_TO_CHARACTER = {
    "ビジネス": "data/templates/business_entrepreneur.yaml",
    "科学": "data/templates/science_researcher.yaml",
    "技術": "data/templates/tech_professional.yaml",
    "日常": "data/templates/casual_friendly.yaml",
}

def generate_post_for_topic(topic: str) -> str:
    # トピックに応じたキャラクターを選択
    character_path = TOPIC_TO_CHARACTER.get(topic, "data/character.yaml")
    char_manager = CharacterManager(character_path)

    # トピックを含めたコンテキスト
    context = {
        "topic": topic,
        "time_of_day": datetime.now().strftime("%H:%M")
    }

    # プロンプト生成
    tweet_prompt = char_manager.generate_tweet_prompt(context)

    # AI生成
    generated_text = generate_with_openai_enhanced(tweet_prompt, model, api_key)

    return generated_text
"""
    )
    print()


def main():
    """メイン処理"""
    print("\n")
    print("╔" + "=" * 68 + "╗")
    print("║" + " " * 10 + "Character Manager 統合例 - auto_post.py" + " " * 17 + "║")
    print("╚" + "=" * 68 + "╝")
    print()

    try:
        example_1_basic_integration()
        example_2_context_aware_generation()
        example_3_dynamic_character_switching()
        example_4_topic_based_character()

        print("=" * 70)
        print("すべての統合例の説明が完了しました")
        print("=" * 70)
        print()
        print("実際に統合する際は、上記のコード例を参考にしてください。")
        print("詳細は README_character.md を参照してください。")

    except Exception as e:
        print(f"\nエラーが発生しました: {e}")
        import traceback

        traceback.print_exc()
        return 1

    return 0


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
