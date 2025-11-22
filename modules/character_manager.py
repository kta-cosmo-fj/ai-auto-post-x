# -*- coding: utf-8 -*-
"""
Character Manager Module

AI botのキャラクター設定を管理し、プロンプト生成に活用するモジュール
"""

import logging
from dataclasses import dataclass, field
from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml

logger = logging.getLogger(__name__)


@dataclass
class Character:
    """キャラクター設定を保持するデータクラス"""

    name: str
    personality: str
    tone: str
    interests: List[str]
    knowledge_level: str
    speaking_style: Dict[str, Any] = field(default_factory=dict)
    constraints: Dict[str, Any] = field(default_factory=dict)

    def __post_init__(self):
        """初期化後のバリデーション"""
        if not self.name:
            raise ValueError("キャラクター名は必須です")
        if not self.personality:
            raise ValueError("personalityは必須です")
        if not self.tone:
            raise ValueError("toneは必須です")
        if not self.interests:
            raise ValueError("interestsは少なくとも1つ必要です")
        if not self.knowledge_level:
            raise ValueError("knowledge_levelは必須です")

    def to_dict(self) -> Dict[str, Any]:
        """辞書形式に変換"""
        return {
            "name": self.name,
            "personality": self.personality,
            "tone": self.tone,
            "interests": self.interests,
            "knowledge_level": self.knowledge_level,
            "speaking_style": self.speaking_style,
            "constraints": self.constraints,
        }


class CharacterManager:
    """キャラクター設定を管理するクラス"""

    def __init__(self, config_path: str = "data/character.yaml"):
        """
        CharacterManagerを初期化する

        Args:
            config_path: キャラクター設定ファイルのパス
        """
        self.config_path = Path(config_path)
        self._character: Optional[Character] = None
        self._raw_config: Optional[Dict] = None

        # 設定ファイルが存在する場合は自動ロード
        if self.config_path.exists():
            self.load_character()

    def load_character(self) -> Character:
        """
        キャラクター設定をYAMLファイルから読み込む

        Returns:
            Character: 読み込まれたキャラクター設定

        Raises:
            FileNotFoundError: 設定ファイルが見つからない場合
            ValueError: 設定ファイルの形式が不正な場合
        """
        if not self.config_path.exists():
            raise FileNotFoundError(
                f"キャラクター設定ファイルが見つかりません: {self.config_path}"
            )

        try:
            with self.config_path.open("r", encoding="utf-8") as f:
                self._raw_config = yaml.safe_load(f)

            if not self._raw_config or "character" not in self._raw_config:
                raise ValueError(
                    "設定ファイルに'character'キーが見つかりません"
                )

            char_data = self._raw_config["character"]

            # Characterオブジェクトを構築
            self._character = Character(
                name=char_data.get("name", ""),
                personality=char_data.get("personality", ""),
                tone=char_data.get("tone", ""),
                interests=char_data.get("interests", []),
                knowledge_level=char_data.get("knowledge_level", ""),
                speaking_style=char_data.get("speaking_style", {}),
                constraints=char_data.get("constraints", {}),
            )

            logger.info(
                "キャラクター設定を読み込みました: %s", self._character.name
            )
            return self._character

        except yaml.YAMLError as e:
            raise ValueError(f"YAML解析エラー: {e}")
        except Exception as e:
            raise ValueError(f"キャラクター設定の読み込みに失敗しました: {e}")

    def get_character(self) -> Character:
        """
        現在のキャラクター設定を取得する

        Returns:
            Character: 現在のキャラクター設定

        Raises:
            RuntimeError: キャラクターが読み込まれていない場合
        """
        if self._character is None:
            raise RuntimeError(
                "キャラクターが読み込まれていません。load_character()を先に実行してください"
            )
        return self._character

    def get_system_prompt(self) -> str:
        """
        キャラクター設定に基づいたシステムプロンプトを生成する

        Returns:
            str: システムプロンプト
        """
        char = self.get_character()

        # 基本的なシステムプロンプト
        prompt_parts = [
            f"あなたは「{char.name}」という名前のAI botです。",
            f"",
            f"【性格・個性】",
            f"{char.personality}",
            f"",
            f"【トーン・話し方】",
            f"{char.tone}",
            f"",
            f"【知識レベル】",
            f"{char.knowledge_level}",
            f"",
            f"【興味・関心分野】",
        ]

        # 興味分野をリスト化
        for interest in char.interests:
            prompt_parts.append(f"- {interest}")

        # スピーキングスタイルの追加
        if char.speaking_style:
            prompt_parts.append("")
            prompt_parts.append("【話し方のスタイル】")

            sentence_endings = char.speaking_style.get("sentence_ending", [])
            if sentence_endings:
                prompt_parts.append(
                    f"- 語尾: {', '.join(sentence_endings)}を使い分ける"
                )

            emoji_freq = char.speaking_style.get("emoji_frequency", "moderate")
            max_emoji = char.speaking_style.get("max_emoji_per_tweet", 2)
            emoji_desc = {
                "low": "控えめに",
                "moderate": "適度に",
                "high": "積極的に",
            }
            prompt_parts.append(
                f"- 絵文字使用: {emoji_desc.get(emoji_freq, '適度に')}（最大{max_emoji}個まで）"
            )

            hashtag_usage = char.speaking_style.get("hashtag_usage", False)
            if hashtag_usage:
                prompt_parts.append("- ハッシュタグ: 適切に使用する")

        # 制約事項の追加
        if char.constraints:
            prompt_parts.append("")
            prompt_parts.append("【制約事項】")

            max_length = char.constraints.get("max_tweet_length", 140)
            prompt_parts.append(f"- 投稿は{max_length}文字以内に収める")

            avoid_topics = char.constraints.get("avoid_topics", [])
            if avoid_topics:
                prompt_parts.append("- 以下のトピックは避ける:")
                for topic in avoid_topics:
                    prompt_parts.append(f"  * {topic}")

        prompt_parts.append("")
        prompt_parts.append(
            "これらの設定に従って、魅力的で価値のある投稿を作成してください。"
        )

        return "\n".join(prompt_parts)

    def get_personality_description(self) -> str:
        """
        キャラクターの性格を簡潔に説明する文字列を返す

        Returns:
            str: 性格の説明
        """
        char = self.get_character()
        return f"{char.name}: {char.personality} ({char.tone})"

    def update_character(self, updates: Dict[str, Any]) -> None:
        """
        キャラクター設定を部分的に更新する

        Args:
            updates: 更新する設定項目の辞書

        Raises:
            RuntimeError: キャラクターが読み込まれていない場合
        """
        if self._character is None:
            raise RuntimeError(
                "キャラクターが読み込まれていません。load_character()を先に実行してください"
            )

        # 現在の設定を辞書化
        current = self._character.to_dict()

        # 更新をマージ
        current.update(updates)

        # 新しいCharacterオブジェクトを作成
        self._character = Character(
            name=current["name"],
            personality=current["personality"],
            tone=current["tone"],
            interests=current["interests"],
            knowledge_level=current["knowledge_level"],
            speaking_style=current.get("speaking_style", {}),
            constraints=current.get("constraints", {}),
        )

        logger.info("キャラクター設定を更新しました")

    def validate_character_config(self) -> bool:
        """
        現在のキャラクター設定が有効かどうかを検証する

        Returns:
            bool: 設定が有効な場合True、無効な場合False
        """
        try:
            char = self.get_character()

            # 必須フィールドのチェック
            if not char.name or not isinstance(char.name, str):
                logger.error("name が不正です")
                return False

            if not char.personality or not isinstance(char.personality, str):
                logger.error("personality が不正です")
                return False

            if not char.tone or not isinstance(char.tone, str):
                logger.error("tone が不正です")
                return False

            if not char.interests or not isinstance(char.interests, list):
                logger.error("interests が不正です")
                return False

            if not char.knowledge_level or not isinstance(
                char.knowledge_level, str
            ):
                logger.error("knowledge_level が不正です")
                return False

            # speaking_styleのバリデーション
            if char.speaking_style:
                valid_emoji_freq = ["low", "moderate", "high"]
                emoji_freq = char.speaking_style.get("emoji_frequency")
                if emoji_freq and emoji_freq not in valid_emoji_freq:
                    logger.error(
                        "emoji_frequency は %s のいずれかである必要があります",
                        valid_emoji_freq,
                    )
                    return False

            logger.info("キャラクター設定は有効です")
            return True

        except Exception as e:
            logger.error("バリデーションエラー: %s", e)
            return False

    def generate_tweet_prompt(self, context: Optional[Dict[str, Any]] = None) -> str:
        """
        キャラクター設定とコンテキストに基づいて投稿用プロンプトを生成する

        Args:
            context: コンテキスト情報（過去の高エンゲージメントツイート、最近のトピック等）
                - successful_patterns: 過去の高エンゲージメントツイート
                - recent_topics: 最近の返信から抽出したトピック
                - time_of_day: 投稿時刻
                - topic: 投稿トピック（任意）
                - post_type: 投稿タイプ（任意）

        Returns:
            str: 生成されたプロンプト
        """
        char = self.get_character()
        context = context or {}

        # システムプロンプトを取得
        system_prompt = self.get_system_prompt()

        # コンテキスト情報を追加
        context_parts = []

        # 成功パターンの活用
        if "successful_patterns" in context and context["successful_patterns"]:
            context_parts.append("【過去の成功パターン】")
            context_parts.append(
                "以下のような投稿が高いエンゲージメントを獲得しました:"
            )
            for i, pattern in enumerate(
                context["successful_patterns"][:3], 1
            ):  # 最大3件
                context_parts.append(f"{i}. {pattern}")
            context_parts.append("")

        # 最近のトピック
        if "recent_topics" in context and context["recent_topics"]:
            context_parts.append("【最近の関心トピック】")
            context_parts.append(
                "フォロワーは以下のトピックに興味を示しています:"
            )
            for topic in context["recent_topics"][:5]:  # 最大5件
                context_parts.append(f"- {topic}")
            context_parts.append("")

        # 時間帯に応じた調整
        time_of_day = context.get("time_of_day", "")
        if time_of_day:
            preferred_slots = char.constraints.get("preferred_time_slots", [])
            if preferred_slots:
                context_parts.append(f"【投稿時刻】{time_of_day}")
                context_parts.append(
                    "この時間帯に適した内容を考慮してください。"
                )
                context_parts.append("")

        # トピックの指定（任意）
        if "topic" in context:
            context_parts.append(f"【トピック】{context['topic']}")
            context_parts.append("")

        # 投稿タイプの指定（任意）
        if "post_type" in context:
            context_parts.append(f"【投稿スタイル】{context['post_type']}")
            context_parts.append("")

        # 最終的なプロンプトを組み立て
        prompt_parts = [system_prompt]

        if context_parts:
            prompt_parts.append("")
            prompt_parts.append("=== コンテキスト情報 ===")
            prompt_parts.extend(context_parts)

        # 投稿生成の指示
        max_length = char.constraints.get("max_tweet_length", 140)
        prompt_parts.append("")
        prompt_parts.append("=== 投稿生成の指示 ===")
        prompt_parts.append(
            f"上記のキャラクター設定とコンテキストに基づいて、{max_length}文字以内の魅力的な投稿を作成してください。"
        )
        prompt_parts.append("")
        prompt_parts.append("【要件】")
        prompt_parts.append(f"- {max_length}文字以内")
        prompt_parts.append("- キャラクターの個性を反映")
        prompt_parts.append("- 読者の興味を引く内容")
        prompt_parts.append("- 自然で読みやすい日本語")

        # 絵文字の制限
        max_emoji = char.speaking_style.get("max_emoji_per_tweet", 2)
        prompt_parts.append(f"- 絵文字は最大{max_emoji}個まで")

        # 回避すべきトピック
        avoid_topics = char.constraints.get("avoid_topics", [])
        if avoid_topics:
            prompt_parts.append(
                f"- 以下のトピックは避ける: {', '.join(avoid_topics)}"
            )

        prompt_parts.append("")
        prompt_parts.append("純粋な投稿テキストのみを出力してください。")

        return "\n".join(prompt_parts)

    def save_character(self, output_path: Optional[str] = None) -> None:
        """
        現在のキャラクター設定をYAMLファイルに保存する

        Args:
            output_path: 保存先のパス（指定しない場合は元のconfig_pathを使用）
        """
        if self._character is None:
            raise RuntimeError(
                "キャラクターが読み込まれていません。load_character()を先に実行してください"
            )

        save_path = Path(output_path) if output_path else self.config_path

        # YAMLデータを構築
        yaml_data = {"character": self._character.to_dict()}

        # ファイルに書き込み
        save_path.parent.mkdir(parents=True, exist_ok=True)
        with save_path.open("w", encoding="utf-8") as f:
            yaml.dump(
                yaml_data,
                f,
                allow_unicode=True,
                default_flow_style=False,
                sort_keys=False,
            )

        logger.info("キャラクター設定を保存しました: %s", save_path)
