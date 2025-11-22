#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""プロンプト生成機能のテストスクリプト"""

import random
import sys
from pathlib import Path

# プロジェクトルートをパスに追加
sys.path.insert(0, str(Path(__file__).parent))

# 必要な部分のみをインポート（tweepyなどは不要）
import json
from collections import Counter

# ポストバリエーション定義を共通モジュールからインポート
from modules.post_variations import TOPICS, POST_TYPES, HOOKS

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


def main():
    """メインテスト処理"""
    print("=" * 60)
    print("プロンプト生成機能のテスト")
    print("=" * 60)
    print()

    # 統計情報を収集
    topic_counts = Counter()
    post_type_counts = Counter()
    hook_counts = Counter()

    num_samples = 10

    # 複数のプロンプトを生成してテスト
    for i in range(num_samples):
        random.seed(i)  # 各サンプルで異なるシード
        prompt = generate_dynamic_prompt()

        print(f"=== サンプル {i+1}/{num_samples} ===")
        print(prompt)
        print()

        # 統計収集（プロンプトを解析）
        if "【トピック】" in prompt:
            for topic_key, topic in TOPICS.items():
                if topic["name"] in prompt:
                    topic_counts[topic["name"]] += 1
                    break

        if "【スタイル】" in prompt:
            for pt_key, pt in POST_TYPES.items():
                if pt["name"] in prompt:
                    post_type_counts[pt["name"]] += 1
                    break

        if "【冒頭フック】" in prompt:
            for hook in HOOKS:
                if hook and f"「{hook}」" in prompt:
                    hook_counts[hook] += 1
                    break
        else:
            hook_counts["フックなし"] += 1

    # 統計情報を表示
    print("=" * 60)
    print("バリエーション統計")
    print("=" * 60)
    print()

    print(f"トピック分布（{num_samples}サンプル）：")
    for topic, count in topic_counts.most_common():
        print(f"  - {topic}: {count}回")
    print()

    print(f"ポストタイプ分布（{num_samples}サンプル）：")
    for post_type, count in post_type_counts.most_common():
        print(f"  - {post_type}: {count}回")
    print()

    print(f"フック分布（{num_samples}サンプル）：")
    for hook, count in hook_counts.most_common():
        display_hook = hook if hook != "フックなし" else "（フックなし）"
        print(f"  - {display_hook}: {count}回")
    print()

    print("=" * 60)
    print("✓ テスト完了")
    print("=" * 60)


if __name__ == "__main__":
    main()
