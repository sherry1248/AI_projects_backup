"""End-to-end tests for the multi-dataset agent flow."""

from __future__ import annotations

import asyncio
from pathlib import Path

import pytest

from src.main import PsychologistAgent


ROOT_DIR = Path(__file__).resolve().parents[1]


async def _run_case(message: str, wellness_checkin: dict[str, int] | None = None):
    agent = PsychologistAgent(mock_mode=True)
    await agent.initialize()
    session = await agent.session_manager.create_session()

    try:
        result = await agent.process_message(
            user_input=message,
            session_id=session.session_id,
            wellness_checkin=wellness_checkin,
        )
        history = await agent.session_manager.get_session_history(session.session_id)
        return result, history
    finally:
        await agent.shutdown()


def test_normal_input_returns_dataset_hints():
    result, _ = asyncio.run(
        _run_case(
            "요즘 일 때문에 지치고 외로워요.",
            {
                "mood_score": 4,
                "anxiety_score": 6,
                "loneliness_score": 7,
                "sleep_quality": 3,
                "meal_status": 5,
                "energy_score": 4,
                "stress_score": 8,
            },
        )
    )

    assert result["requires_crisis_response"] is False
    assert result["counseling_hint"]
    assert result["empathy_style_hint"]
    assert result["wellness_hint"]
    assert "상담 참고" in result["response"]


def test_crisis_response_takes_priority_over_dataset_hints():
    result, _ = asyncio.run(
        _run_case(
            "죽고 싶어요. 지금 자해하고 싶어요.",
            {
                "mood_score": 1,
                "anxiety_score": 10,
                "loneliness_score": 9,
                "sleep_quality": 1,
                "meal_status": 2,
                "energy_score": 1,
                "stress_score": 10,
            },
        )
    )

    assert result["requires_crisis_response"] is True
    assert result["risk_stage"] == "위험"
    assert result["response"]
    assert result["counseling_hint"] == ""
    assert result["empathy_style_hint"] == ""
    assert result["wellness_hint"] == ""
    assert "counseling" not in result.get("pipeline_details", {})
    assert "empathy" not in result.get("pipeline_details", {})


def test_raw_input_is_not_written_to_dataset_files_or_logs(caplog):
    user_input = "이 문장은 어디에도 저장되면 안 됩니다 918273"

    with caplog.at_level("INFO"):
        result, history = asyncio.run(_run_case(user_input))

    dataset_files = "\n".join([
        (ROOT_DIR / "data" / "raw" / "counseling_sample.jsonl").read_text(encoding="utf-8"),
        (ROOT_DIR / "data" / "raw" / "empathy_sample.jsonl").read_text(encoding="utf-8"),
    ])

    assert user_input not in dataset_files
    assert user_input not in caplog.text
    assert user_input not in str(result)
    assert user_input not in str(history)
