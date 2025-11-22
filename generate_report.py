#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
エンゲージメント分析レポート生成スクリプト

Usage:
    python generate_report.py
    python generate_report.py --db-path data/tweets.db --output reports/analysis.md
"""
import argparse
import sys
from datetime import datetime
from pathlib import Path

from modules.analyzer import EngagementAnalyzer


def generate_markdown_report(analyzer: EngagementAnalyzer) -> str:
    """
    Markdown形式の分析レポートを生成

    Args:
        analyzer: EngagementAnalyzerインスタンス

    Returns:
        Markdown形式のレポート文字列
    """
    # 統計サマリー取得
    summary = analyzer.get_stats_summary()

    # トップツイート取得
    top_by_likes = analyzer.get_top_tweets(limit=10, metric="likes")
    top_by_engagement = analyzer.get_top_tweets(limit=5, metric="engagement")

    # 成功パターン抽出
    features = analyzer.extract_successful_features()

    # 最適投稿時間
    optimal_times = analyzer.get_optimal_posting_time()

    # トピック分析
    topic_performance = analyzer.analyze_topic_performance()

    # レポート生成
    report_lines = [
        "# エンゲージメント分析レポート",
        f"\n生成日時: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n",
        "---\n",
        "## 📊 全体統計",
        f"- **総ツイート数**: {summary['total_tweets']:,}",
        f"- **平均いいね数**: {summary['avg_likes']:.2f}",
        f"- **平均リツイート数**: {summary['avg_retweets']:.2f}",
        f"- **平均返信数**: {summary['avg_replies']:.2f}",
        f"- **最大いいね数**: {summary['max_likes']:,}",
        f"- **総インプレッション数**: {summary['total_impressions']:,}",
        "\n---\n",
        "## 🏆 トップパフォーマンスツイート",
        "\n### いいね数トップ10\n",
    ]

    for i, tweet in enumerate(top_by_likes, 1):
        report_lines.append(
            f"{i}. **{tweet['likes']}** いいね | "
            f"{tweet['retweets']} RT | "
            f"{tweet['replies']} 返信\n"
            f"   > {tweet['content'][:80]}{'...' if len(tweet['content']) > 80 else ''}\n"
        )

    report_lines.extend([
        "\n### エンゲージメント率トップ5\n",
    ])

    for i, tweet in enumerate(top_by_engagement, 1):
        engagement_pct = tweet['engagement_rate'] * 100
        report_lines.append(
            f"{i}. **{engagement_pct:.2f}%** | "
            f"{tweet['likes']} いいね | "
            f"{tweet['retweets']} RT\n"
            f"   > {tweet['content'][:80]}{'...' if len(tweet['content']) > 80 else ''}\n"
        )

    report_lines.extend([
        "\n---\n",
        "## 🎯 成功パターン分析",
        "\n### パフォーマンスの高いツイートの特徴\n",
    ])

    patterns = features.get("top_performing_pattern", {})
    if patterns:
        report_lines.extend([
            f"- **平均文字数**: {patterns.get('avg_length', 0)}文字",
            f"- **絵文字使用数**: {patterns.get('emoji_count', 0)}個",
            f"- **ハッシュタグ使用数**: {patterns.get('hashtag_count', 0)}個",
            f"- **質問形式**: {patterns.get('question_tweets', 0)}件",
            f"- **断定形式**: {patterns.get('statement_tweets', 0)}件",
        ])

        if patterns.get('common_words'):
            report_lines.append("\n**頻出キーワード**:")
            report_lines.append(", ".join(patterns['common_words'][:10]))

        if patterns.get('topics'):
            report_lines.append("\n**主要トピック**:")
            report_lines.append(", ".join(patterns['topics'][:5]))

    report_lines.extend([
        "\n### 推奨事項\n",
    ])

    for recommendation in features.get("recommended_features", []):
        report_lines.append(f"- {recommendation}")

    report_lines.extend([
        "\n---\n",
        "## ⏰ 最適投稿時間",
        "\nエンゲージメント率が高い時間帯:\n",
    ])

    if optimal_times:
        for i, time_range in enumerate(optimal_times, 1):
            report_lines.append(f"{i}. **{time_range}**")
    else:
        report_lines.append("データ不足のため分析できません")

    report_lines.extend([
        "\n---\n",
        "## 📚 トピック別パフォーマンス\n",
    ])

    if topic_performance:
        report_lines.append("| トピック | ツイート数 | 平均いいね数 |")
        report_lines.append("|---------|-----------|-------------|")

        for topic, stats in topic_performance.items():
            report_lines.append(
                f"| {topic} | {stats['count']} | {stats['avg_likes']:.1f} |"
            )
    else:
        report_lines.append("トピックデータがありません")

    report_lines.extend([
        "\n---\n",
        "\n*このレポートは自動生成されました*\n"
    ])

    return "\n".join(report_lines)


def main():
    """メイン処理"""
    parser = argparse.ArgumentParser(
        description="エンゲージメント分析レポートを生成します"
    )
    parser.add_argument(
        "--db-path",
        default="data/tweets.db",
        help="データベースファイルのパス (デフォルト: data/tweets.db)"
    )
    parser.add_argument(
        "--output",
        default=None,
        help="レポート出力先ファイル (デフォルト: 標準出力)"
    )

    args = parser.parse_args()

    # データベースの存在確認
    if not Path(args.db_path).exists():
        print(f"エラー: データベースファイルが見つかりません: {args.db_path}", file=sys.stderr)
        print("まず、ツイートデータをデータベースに追加してください。", file=sys.stderr)
        return 1

    # アナライザー初期化
    analyzer = EngagementAnalyzer(db_path=args.db_path)

    # 統計確認
    summary = analyzer.get_stats_summary()
    if summary["total_tweets"] == 0:
        print("エラー: データベースにツイートデータがありません", file=sys.stderr)
        print("まず、ツイートデータをデータベースに追加してください。", file=sys.stderr)
        return 1

    # レポート生成
    report = generate_markdown_report(analyzer)

    # 出力
    if args.output:
        output_path = Path(args.output)
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(report, encoding="utf-8")
        print(f"✓ レポートを生成しました: {output_path}")
    else:
        print(report)

    return 0


if __name__ == "__main__":
    sys.exit(main())
