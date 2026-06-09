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
