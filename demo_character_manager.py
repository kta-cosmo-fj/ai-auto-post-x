#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Character Manager のデモスクリプト

CharacterManagerの基本的な機能を実演します
"""

import sys
from pathlib import Path

# プロジェクトルートをパスに追加
sys.path.insert(0, str(Path(__file__).parent))

from modules.character_manager import CharacterManager


def print_section(title: str):
    """セクションの区切りを表示"""
    print("\n" + "=" * 70)
    print(f" {title}")
    print("=" * 70 + "\n")


def demo_basic_usage():
    """基本的な使い方のデモ"""
    print_section("1. 基本的な使い方")

    # CharacterManagerの初期化
    manager = CharacterManager("data/character.yaml")

    # キャラクター情報の取得
    character = manager.get_character()
    print(f"キャラクター名: {character.name}")
    print(f"性格: {character.personality}")
    print(f"トーン: {character.tone}")
    print(f"興味分野: {', '.join(character.interests[:3])}...")
    print(f"知識レベル: {character.knowledge_level}")

    # 性格の簡潔な説明
    print(f"\n性格説明: {manager.get_personality_description()}")


def demo_system_prompt():
    """システムプロンプトの生成デモ"""
    print_section("2. システムプロンプトの生成")

    manager = CharacterManager("data/character.yaml")
    system_prompt = manager.get_system_prompt()

    print("生成されたシステムプロンプト:")
    print("-" * 70)
    print(system_prompt)
    print("-" * 70)


def demo_tweet_prompt_basic():
    """基本的な投稿プロンプトの生成デモ"""
    print_section("3. 基本的な投稿プロンプトの生成")

    manager = CharacterManager("data/character.yaml")
    tweet_prompt = manager.generate_tweet_prompt()

    print("生成された投稿プロンプト:")
    print("-" * 70)
    print(tweet_prompt)
    print("-" * 70)


def demo_tweet_prompt_with_context():
    """コンテキスト付き投稿プロンプトの生成デモ"""
    print_section("4. コンテキスト付き投稿プロンプトの生成")

    manager = CharacterManager("data/character.yaml")

    # コンテキスト情報を定義
    context = {
        "successful_patterns": [
            "知ってました？Pythonは世界で最も人気のあるプログラミング言語の1つです",
            "AIの進化が止まらない！最新の研究では、AIが人間の感情を理解できるように",
        ],
        "recent_topics": ["AI", "機械学習", "Python", "クラウド技術"],
        "time_of_day": "09:30",
        "topic": "AI・機械学習",
        "post_type": "事実・トリビア",
    }

    tweet_prompt = manager.generate_tweet_prompt(context)

    print("コンテキスト情報:")
    print(f"  - 過去の成功パターン: {len(context['successful_patterns'])}件")
    print(f"  - 最近のトピック: {', '.join(context['recent_topics'])}")
    print(f"  - 投稿時刻: {context['time_of_day']}")
    print(f"  - トピック: {context['topic']}")
    print(f"  - 投稿タイプ: {context['post_type']}")
    print()
    print("生成された投稿プロンプト:")
    print("-" * 70)
    print(tweet_prompt)
    print("-" * 70)


def demo_multiple_templates():
    """複数のテンプレートのデモ"""
    print_section("5. 複数のキャラクターテンプレート")

    templates = [
        ("デフォルト", "data/character.yaml"),
        ("ビジネス・起業家", "data/templates/business_entrepreneur.yaml"),
        ("科学・研究者", "data/templates/science_researcher.yaml"),
        ("カジュアル・フレンドリー", "data/templates/casual_friendly.yaml"),
        ("テックプロフェッショナル", "data/templates/tech_professional.yaml"),
    ]

    for name, path in templates:
        if Path(path).exists():
            manager = CharacterManager(path)
            char = manager.get_character()
            print(f"\n【{name}】")
            print(f"  名前: {char.name}")
            print(f"  性格: {char.personality[:60]}...")
            print(f"  トーン: {char.tone[:60]}...")
            print(f"  興味: {', '.join(char.interests[:3])}")
        else:
            print(f"\n【{name}】 - ファイルが見つかりません")


def demo_validation():
    """バリデーションのデモ"""
    print_section("6. 設定のバリデーション")

    manager = CharacterManager("data/character.yaml")

    # バリデーションの実行
    is_valid = manager.validate_character_config()

    if is_valid:
        print("✓ キャラクター設定は有効です")
        print("\n設定内容:")
        char = manager.get_character()
        print(f"  - 名前: {char.name}")
        print(f"  - 性格: OK")
        print(f"  - トーン: OK")
        print(f"  - 興味分野: {len(char.interests)}件")
        print(f"  - 知識レベル: OK")
        print(f"  - 話し方スタイル: OK")
        print(f"  - 制約事項: OK")
    else:
        print("✗ キャラクター設定に問題があります")


def demo_update_and_save():
    """設定の更新と保存のデモ"""
    print_section("7. 設定の更新と保存")

    manager = CharacterManager("data/character.yaml")

    print("元の設定:")
    char = manager.get_character()
    print(f"  名前: {char.name}")
    print(f"  性格: {char.personality[:50]}...")

    # 設定の更新
    manager.update_character({"name": "カスタムAI"})

    print("\n更新後:")
    char = manager.get_character()
    print(f"  名前: {char.name}")
    print(f"  性格: {char.personality[:50]}...")

    # 一時ファイルに保存（実際のファイルを変更しないため）
    import tempfile

    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".yaml", delete=False
    ) as f:
        temp_path = f.name

    manager.save_character(temp_path)
    print(f"\n✓ 設定を保存しました: {temp_path}")

    # 保存したファイルを読み込んで確認
    manager2 = CharacterManager(temp_path)
    char2 = manager2.get_character()
    print(f"✓ 保存したファイルから読み込み: {char2.name}")

    # クリーンアップ
    Path(temp_path).unlink()
    print("✓ 一時ファイルを削除しました")


def main():
    """メイン処理"""
    print("\n")
    print("╔" + "=" * 68 + "╗")
    print("║" + " " * 15 + "Character Manager デモスクリプト" + " " * 20 + "║")
    print("╚" + "=" * 68 + "╝")

    try:
        demo_basic_usage()
        demo_system_prompt()
        demo_tweet_prompt_basic()
        demo_tweet_prompt_with_context()
        demo_multiple_templates()
        demo_validation()
        demo_update_and_save()

        print_section("デモ完了")
        print("すべてのデモが正常に完了しました。")
        print("\n詳細なドキュメントは README_character.md を参照してください。")

    except Exception as e:
        print(f"\nエラーが発生しました: {e}")
        import traceback

        traceback.print_exc()
        return 1

    return 0


if __name__ == "__main__":
    exit_code = main()
    sys.exit(exit_code)
