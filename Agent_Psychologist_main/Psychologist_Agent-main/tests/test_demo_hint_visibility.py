"""Tests for hiding internal hints in the demo UI."""

from demo.app import build_general_markdown


def test_general_markdown_hides_internal_hint_cards():
    markdown = build_general_markdown(
        {
            "risk_stage": "관심",
            "counseling_hint": "internal counseling hint",
            "empathy_style_hint": "internal empathy hint",
            "wellness_hint": "internal wellness hint",
        },
        "자연스러운 상담 응답입니다.",
    )

    assert "AI 상담 응답" in markdown
    assert "자연스러운 상담 응답입니다." in markdown
    assert "심리상담 데이터 기반 힌트" not in markdown
    assert "공감형 대화 기반 힌트" not in markdown
    assert "웰니스 기반 힌트" not in markdown
    assert "internal counseling hint" not in markdown
    assert "internal empathy hint" not in markdown
    assert "internal wellness hint" not in markdown


def test_general_markdown_strips_default_safety_notice_for_non_crisis():
    notice = (
        "이 AI는 의료 진단이나 치료를 하지 않으며 전문 상담사를 대체하지 않습니다. "
        "위험 신호가 있으면 109, 119, 112 또는 가까운 응급실/지역 정신건강복지센터에 바로 연결하세요."
    )
    markdown = build_general_markdown(
        {"risk_stage": "주의"},
        f"수면과 불안을 먼저 살펴볼게요.\n\n{notice}",
    )

    assert "수면과 불안을 먼저 살펴볼게요." in markdown
    assert notice not in markdown
