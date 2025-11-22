#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
Character Manager のテストケース
"""

import sys
import tempfile
import unittest
from pathlib import Path

# プロジェクトルートをパスに追加
sys.path.insert(0, str(Path(__file__).parent.parent))

from modules.character_manager import Character, CharacterManager


class TestCharacter(unittest.TestCase):
    """Character データクラスのテスト"""

    def test_character_creation(self):
        """正常なCharacterオブジェクトの作成"""
        char = Character(
            name="テストAI",
            personality="テスト用の性格",
            tone="フレンドリー",
            interests=["AI", "プログラミング"],
            knowledge_level="中級",
        )

        self.assertEqual(char.name, "テストAI")
        self.assertEqual(char.personality, "テスト用の性格")
        self.assertEqual(char.tone, "フレンドリー")
        self.assertEqual(char.interests, ["AI", "プログラミング"])
        self.assertEqual(char.knowledge_level, "中級")

    def test_character_with_optional_fields(self):
        """オプションフィールド付きのCharacter作成"""
        char = Character(
            name="テストAI",
            personality="テスト用の性格",
            tone="フレンドリー",
            interests=["AI"],
            knowledge_level="中級",
            speaking_style={"emoji_frequency": "high"},
            constraints={"max_tweet_length": 140},
        )

        self.assertEqual(char.speaking_style["emoji_frequency"], "high")
        self.assertEqual(char.constraints["max_tweet_length"], 140)

    def test_character_validation_empty_name(self):
        """空の名前でエラーが発生することを確認"""
        with self.assertRaises(ValueError):
            Character(
                name="",
                personality="テスト",
                tone="テスト",
                interests=["AI"],
                knowledge_level="中級",
            )

    def test_character_validation_empty_interests(self):
        """空のinterestsでエラーが発生することを確認"""
        with self.assertRaises(ValueError):
            Character(
                name="テストAI",
                personality="テスト",
                tone="テスト",
                interests=[],
                knowledge_level="中級",
            )

    def test_character_to_dict(self):
        """to_dict メソッドのテスト"""
        char = Character(
            name="テストAI",
            personality="テスト用の性格",
            tone="フレンドリー",
            interests=["AI", "プログラミング"],
            knowledge_level="中級",
        )

        char_dict = char.to_dict()
        self.assertEqual(char_dict["name"], "テストAI")
        self.assertEqual(char_dict["personality"], "テスト用の性格")
        self.assertIn("interests", char_dict)
        self.assertIsInstance(char_dict["interests"], list)


class TestCharacterManager(unittest.TestCase):
    """CharacterManager クラスのテスト"""

    def setUp(self):
        """テストの前処理"""
        # 一時的なYAMLファイルを作成
        self.temp_dir = tempfile.mkdtemp()
        self.temp_yaml = Path(self.temp_dir) / "test_character.yaml"

        yaml_content = """
character:
  name: "テストAI"
  personality: "テスト用の性格"
  tone: "フレンドリー"
  interests:
    - AI
    - プログラミング
  knowledge_level: "中級"
  speaking_style:
    sentence_ending:
      - "です"
      - "ます"
    emoji_frequency: "moderate"
    max_emoji_per_tweet: 2
    hashtag_usage: true
  constraints:
    max_tweet_length: 140
    avoid_topics:
      - "政治"
      - "宗教"
    preferred_time_slots:
      - "09:00-10:00"
      - "12:00-13:00"
"""
        self.temp_yaml.write_text(yaml_content, encoding="utf-8")

    def tearDown(self):
        """テストの後処理"""
        import shutil

        shutil.rmtree(self.temp_dir)

    def test_load_character(self):
        """キャラクター設定の読み込み"""
        manager = CharacterManager(str(self.temp_yaml))
        char = manager.load_character()

        self.assertEqual(char.name, "テストAI")
        self.assertEqual(char.personality, "テスト用の性格")
        self.assertEqual(char.tone, "フレンドリー")
        self.assertIn("AI", char.interests)

    def test_load_character_auto(self):
        """ファイルが存在する場合の自動読み込み"""
        manager = CharacterManager(str(self.temp_yaml))
        char = manager.get_character()

        self.assertEqual(char.name, "テストAI")

    def test_load_character_file_not_found(self):
        """存在しないファイルでエラーが発生することを確認"""
        manager = CharacterManager("nonexistent.yaml")
        with self.assertRaises(FileNotFoundError):
            manager.load_character()

    def test_get_character_not_loaded(self):
        """キャラクターが読み込まれていない場合のエラー"""
        manager = CharacterManager("nonexistent.yaml")
        with self.assertRaises(RuntimeError):
            manager.get_character()

    def test_get_system_prompt(self):
        """システムプロンプトの生成"""
        manager = CharacterManager(str(self.temp_yaml))
        manager.load_character()
        prompt = manager.get_system_prompt()

        self.assertIn("テストAI", prompt)
        self.assertIn("テスト用の性格", prompt)
        self.assertIn("AI", prompt)
        self.assertIn("プログラミング", prompt)
        self.assertIn("140文字以内", prompt)

    def test_get_personality_description(self):
        """性格説明の取得"""
        manager = CharacterManager(str(self.temp_yaml))
        manager.load_character()
        desc = manager.get_personality_description()

        self.assertIn("テストAI", desc)
        self.assertIn("テスト用の性格", desc)
        self.assertIn("フレンドリー", desc)

    def test_update_character(self):
        """キャラクター設定の更新"""
        manager = CharacterManager(str(self.temp_yaml))
        manager.load_character()

        # 名前を更新
        manager.update_character({"name": "新しいAI"})
        char = manager.get_character()

        self.assertEqual(char.name, "新しいAI")

    def test_validate_character_config(self):
        """設定のバリデーション"""
        manager = CharacterManager(str(self.temp_yaml))
        manager.load_character()

        self.assertTrue(manager.validate_character_config())

    def test_validate_character_invalid_emoji_frequency(self):
        """不正な絵文字頻度でバリデーションが失敗することを確認"""
        manager = CharacterManager(str(self.temp_yaml))
        manager.load_character()

        # 不正な値を設定
        manager.update_character(
            {"speaking_style": {"emoji_frequency": "invalid"}}
        )

        self.assertFalse(manager.validate_character_config())

    def test_generate_tweet_prompt_basic(self):
        """基本的な投稿プロンプトの生成"""
        manager = CharacterManager(str(self.temp_yaml))
        manager.load_character()

        prompt = manager.generate_tweet_prompt()

        self.assertIn("テストAI", prompt)
        self.assertIn("140文字以内", prompt)
        self.assertIn("投稿生成の指示", prompt)

    def test_generate_tweet_prompt_with_context(self):
        """コンテキスト付き投稿プロンプトの生成"""
        manager = CharacterManager(str(self.temp_yaml))
        manager.load_character()

        context = {
            "successful_patterns": ["過去の成功投稿1", "過去の成功投稿2"],
            "recent_topics": ["AI", "機械学習"],
            "time_of_day": "09:30",
            "topic": "プログラミング",
            "post_type": "ハウツー",
        }

        prompt = manager.generate_tweet_prompt(context)

        self.assertIn("過去の成功パターン", prompt)
        self.assertIn("最近の関心トピック", prompt)
        self.assertIn("AI", prompt)
        self.assertIn("プログラミング", prompt)
        self.assertIn("ハウツー", prompt)

    def test_save_character(self):
        """キャラクター設定の保存"""
        manager = CharacterManager(str(self.temp_yaml))
        manager.load_character()

        # 別のファイルに保存
        save_path = Path(self.temp_dir) / "saved_character.yaml"
        manager.save_character(str(save_path))

        self.assertTrue(save_path.exists())

        # 保存したファイルを読み込んで確認
        manager2 = CharacterManager(str(save_path))
        char = manager2.load_character()

        self.assertEqual(char.name, "テストAI")


class TestCharacterManagerIntegration(unittest.TestCase):
    """統合テスト"""

    def test_load_default_character(self):
        """デフォルトのキャラクター設定を読み込む"""
        # プロジェクトのデフォルト設定ファイルが存在する場合
        default_path = Path(__file__).parent.parent / "data" / "character.yaml"

        if default_path.exists():
            manager = CharacterManager(str(default_path))
            char = manager.load_character()

            self.assertIsNotNone(char.name)
            self.assertIsNotNone(char.personality)
            self.assertTrue(len(char.interests) > 0)

            # システムプロンプトの生成
            system_prompt = manager.get_system_prompt()
            self.assertTrue(len(system_prompt) > 0)

            # プロンプト生成
            tweet_prompt = manager.generate_tweet_prompt()
            self.assertTrue(len(tweet_prompt) > 0)

            # バリデーション
            self.assertTrue(manager.validate_character_config())

    def test_load_all_templates(self):
        """すべてのテンプレートを読み込んでテスト"""
        templates_dir = (
            Path(__file__).parent.parent / "data" / "templates"
        )

        if templates_dir.exists():
            for template_file in templates_dir.glob("*.yaml"):
                with self.subTest(template=template_file.name):
                    manager = CharacterManager(str(template_file))
                    char = manager.load_character()

                    # 基本的な検証
                    self.assertIsNotNone(char.name)
                    self.assertIsNotNone(char.personality)
                    self.assertTrue(len(char.interests) > 0)

                    # システムプロンプト生成
                    system_prompt = manager.get_system_prompt()
                    self.assertTrue(len(system_prompt) > 0)

                    # バリデーション
                    self.assertTrue(manager.validate_character_config())


def main():
    """テストを実行"""
    unittest.main(verbosity=2)


if __name__ == "__main__":
    main()
