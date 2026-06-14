"""
Response quality tests for deterministic MOCK-mode agent responses.
"""

import asyncio
from types import SimpleNamespace

from src.main import AgentConfig, PsychologistAgent


SAFETY_NOTICE_MARKER = "이 AI는 의료 진단이나 치료"
RAW_USER_INPUT = "내 비밀 원문 ABC123을 그대로 말하지 마"
RAW_DATASET_TEXT = "상담 참고: 원본 데이터셋 문장을 그대로 노출하면 안 됩니다"
RAW_MEMORY_TEXT = "raw memory transcript should never appear"
NON_ACTION_HINT = "상담 참고: 기분이 우울하시군요. 공감 참고: 그대로 말하세요."
ACTION_MARKERS = (
    "보세요",
    "해보세요",
    "정해",
    "적어",
    "느껴",
    "마시",
    "낮춰",
    "내려놓",
)


async def _run_message(message, *, counseling_hint=NON_ACTION_HINT, empathy_hint="공감 참고: 감정을 먼저 확인하세요."):
    agent = PsychologistAgent(
        config=AgentConfig(
            enable_rag=False,
            enable_audit_logging=False,
        ),
        mock_mode=True,
    )
    agent.counseling_retriever = SimpleNamespace(
        recommend=lambda _: SimpleNamespace(
            intervention_hint=counseling_hint,
            matched_record_id="counseling-test",
            category="test",
            score=1.0,
        )
    )
    agent.empathy_retriever = SimpleNamespace(
        recommend=lambda _: SimpleNamespace(
            empathy_style_hint=empathy_hint,
            emotion_label="",
            empathy_label="test",
            matched_record_id="empathy-test",
            score=1.0,
        )
    )
    agent.wellness_recommender = SimpleNamespace(recommend=lambda _: None)

    await agent.initialize()
    session = await agent.session_manager.create_session()
    try:
        return await agent.process_message(message, session.session_id)
    finally:
        await agent.shutdown()


def _flatten_strings(value):
    if isinstance(value, dict):
        for key, item in value.items():
            yield str(key)
            yield from _flatten_strings(item)
    elif isinstance(value, list):
        for item in value:
            yield from _flatten_strings(item)
    elif isinstance(value, str):
        yield value


def test_sleep_problem_response_includes_sleep_followup():
    result = asyncio.run(_run_message("요즘 잠을 못 자고 불안해요"))

    followup = result["pipeline_details"]["agents"]["followup"]["question"]
    assert "잠드는 데 오래 걸리는 편인가요" in followup
    assert followup in result["response"]


def test_sleep_problem_response_does_not_mix_low_mood_sentence():
    result = asyncio.run(_run_message("요즘 잠을 못 자고 불안해요"))

    assert "기분이 우울" not in result["response"]
    assert "우울하시군요" not in result["response"]


def test_low_mood_response_centers_low_energy_empathy():
    result = asyncio.run(_run_message("요즘 너무 무기력하고 아무 기운이 없어요"))

    assert "무기력" in result["response"] or "기운이 없는" in result["response"]
    assert "소진" in result["response"]


def test_need_empathy_response_centers_empathy_over_advice():
    result = asyncio.run(_run_message("조언보다 그냥 들어주고 공감해줬으면 해요"))

    response = result["response"]
    assert "해결책을 서둘러" in response
    assert "판단하거나 몰아붙이지" in response
    assert "작은 실행 단계" not in response


def test_need_advice_response_centers_small_execution_step():
    result = asyncio.run(_run_message("어떻게 해야 할지 방법을 알려줘"))

    response = result["response"]
    assert "작은 실행 단계" in response or "가장 작은" in response
    assert any(marker in response for marker in ACTION_MARKERS)


def test_small_action_is_actual_action_sentence():
    result = asyncio.run(_run_message("요즘 잠을 못 자고 불안해요"))

    small_action = result["pipeline_details"]["agents"]["small_action"]
    action_text = small_action["action_text"]
    assert small_action["has_action"] is True
    assert any(marker in action_text for marker in ACTION_MARKERS)
    assert "상담 참고" not in action_text
    assert "공감 참고" not in action_text


def test_dataset_hint_labels_are_not_exposed():
    result = asyncio.run(
        _run_message(
            "요즘 잠을 못 자고 불안해요",
            counseling_hint=RAW_DATASET_TEXT,
            empathy_hint="웰니스 참고: 그대로 노출하지 마세요",
        )
    )

    assert "상담 참고" not in result["response"]
    assert "공감 참고" not in result["response"]
    assert "웰니스 참고" not in result["response"]


def test_disclaimer_is_not_duplicated():
    result = asyncio.run(_run_message("요즘 잠을 못 자고 불안해요"))

    assert result["response"].count(SAFETY_NOTICE_MARKER) == 1


def test_crisis_response_has_no_general_followup_or_small_action():
    result = asyncio.run(_run_message("죽고 싶어요. 지금 혼자라서 너무 위험해요."))

    agents = result["pipeline_details"].get("agents", {})
    assert result["requires_crisis_response"] is True
    assert not agents.get("followup", {}).get("has_question", False)
    assert not agents.get("small_action", {}).get("has_action", False)
    assert "잠드는 데 오래 걸리는 편인가요" not in result["response"]
    assert "오늘의 작은 행동" not in result["response"]


def test_raw_inputs_dataset_text_and_memory_transcript_are_not_exposed():
    result = asyncio.run(
        _run_message(
            RAW_USER_INPUT,
            counseling_hint=RAW_DATASET_TEXT,
            empathy_hint=RAW_MEMORY_TEXT,
        )
    )

    exposed = "\n".join([result["response"], *list(_flatten_strings(result["pipeline_details"]))])
    assert RAW_USER_INPUT not in exposed
    assert RAW_DATASET_TEXT not in exposed
    assert RAW_MEMORY_TEXT not in exposed
