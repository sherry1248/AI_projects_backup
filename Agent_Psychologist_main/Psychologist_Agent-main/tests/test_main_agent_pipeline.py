"""Tests for shallow agent pipeline integration in src.main."""

import asyncio
import os
import sys
import types
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

os.environ["LLM_TYPE"] = "MOCK"

sys.modules.setdefault("yaml", types.SimpleNamespace(safe_load=lambda _: None))

if "pydantic" not in sys.modules:
    class BaseModel:
        def __init__(self, **kwargs):
            for key, value in kwargs.items():
                setattr(self, key, value)

        def dict(self):
            return dict(self.__dict__)

    def Field(default=None, **kwargs):
        if "default_factory" in kwargs:
            return kwargs["default_factory"]()
        return default

    sys.modules["pydantic"] = types.SimpleNamespace(BaseModel=BaseModel, Field=Field)

sys.modules.setdefault(
    "numpy",
    types.SimpleNamespace(
        ndarray=object,
        argmax=lambda values: 0,
        max=max,
    ),
)

from src.main import AgentConfig, PsychologistAgent
from src.api.models import AnalysisResult
from src.inference.generator import GenerationResult


RAW_KEYS = (
    "raw_text",
    "user_input",
    "conversation",
    "content",
    "assistant_response",
)


async def _run_message(message: str, wellness_checkin=None):
    agent = PsychologistAgent(
        config=AgentConfig(
            enable_safety_check=False,
            enable_rag=False,
            enable_audit_logging=False,
        ),
        mock_mode=True,
    )
    agent.counseling_retriever = SimpleNamespace(
        recommend=lambda _: SimpleNamespace(
            intervention_hint="지금 당장 해결하려 하기보다, 가장 작은 한 가지를 정해보세요.",
            matched_record_id="counseling-test",
            category="sleep",
            score=1.0,
        )
    )
    agent.empathy_retriever = SimpleNamespace(
        recommend=lambda _: SimpleNamespace(
            empathy_style_hint="감정을 먼저 확인하고 차분하게 공감하세요.",
            emotion_label="불안",
            empathy_label="위로",
            matched_record_id="empathy-test",
            score=1.0,
        )
    )
    agent.wellness_recommender = SimpleNamespace(
        recommend=lambda _: SimpleNamespace(
            support_hint="지금 자리에서 발바닥 감각을 30초만 느껴보세요.",
            risk_stage="관심",
            matched_record_id="wellness-test",
            matched_topic="anxiety",
            distance=0.1,
        )
    )
    await agent.initialize()
    session = await agent.session_manager.create_session()
    try:
        return await agent.process_message(
            user_input=message,
            session_id=session.session_id,
            wellness_checkin=wellness_checkin,
        )
    finally:
        await agent.shutdown()


def test_non_crisis_input_creates_agents_pipeline_details():
    result = asyncio.run(_run_message("요즘 잠을 못 자고 불안해요"))

    agents = result["pipeline_details"].get("agents")

    assert isinstance(agents, dict)
    assert "intent" in agents
    assert "emotional_state" in agents
    assert "decision" in agents
    assert "followup" in agents
    assert "small_action" in agents


def test_non_crisis_mock_flow_creates_agent_prompt_context():
    result = asyncio.run(_run_message("요즘 잠을 못 자고 불안해요"))

    prompt_context = result["pipeline_details"]["agents"].get("prompt_context")

    assert isinstance(prompt_context, dict)
    assert "decision" in prompt_context
    assert "emotional_state" in prompt_context
    assert "proactive_recall" in prompt_context
    assert "followup" in prompt_context
    assert "small_action" in prompt_context
    assert "primary_action" in prompt_context["decision"]
    assert "state_summary" in prompt_context["emotional_state"]


def test_sleep_and_anxiety_input_sets_sleep_intent_label():
    result = asyncio.run(_run_message("요즘 잠을 못 자고 불안해요"))

    intent = result["pipeline_details"]["agents"]["intent"]

    assert (
        intent["primary_intent"] == "SLEEP_PROBLEM"
        or "SLEEP_PROBLEM" in intent["labels"]
    )


def test_decision_selects_followup_or_small_action():
    result = asyncio.run(
        _run_message(
            "요즘 잠을 못 자고 불안해요",
            wellness_checkin={
                "mood_score": 3,
                "anxiety_score": 5,
                "loneliness_score": 3,
                "sleep_quality": 1,
                "meal_status": 3,
                "energy_score": 2,
                "stress_score": 4,
            },
        )
    )

    decision = result["pipeline_details"]["agents"]["decision"]

    assert (
        decision["primary_action"] == "ASK_FOLLOW_UP"
        or "SUGGEST_SMALL_ACTION" in decision["secondary_actions"]
    )


def test_mock_response_includes_followup_question():
    result = asyncio.run(_run_message("요즘 잠을 못 자고 불안해요"))

    followup = result["pipeline_details"]["agents"]["followup"]

    assert followup["has_question"] is True
    assert followup["question"]
    assert followup["question"] in result["response"]


def test_mock_response_includes_small_action_when_planned():
    result = asyncio.run(
        _run_message(
            "요즘 잠을 못 자고 불안해요",
            wellness_checkin={
                "mood_score": 3,
                "anxiety_score": 5,
                "loneliness_score": 3,
                "sleep_quality": 1,
                "meal_status": 3,
                "energy_score": 2,
                "stress_score": 4,
            },
        )
    )

    small_action = result["pipeline_details"]["agents"]["small_action"]

    assert small_action["has_action"] is True
    assert small_action["status"] == "suggested"
    assert "작은 행동" in result["response"]


def test_sleep_anxiety_mock_response_does_not_include_low_mood_phrase():
    result = asyncio.run(_run_message("요즘 잠을 못 자고 불안해요"))

    assert "기분이 우울" not in result["response"]
    assert "우울하시군요" not in result["response"]


def test_sleep_anxiety_followup_is_sleep_related():
    result = asyncio.run(_run_message("요즘 잠을 못 자고 불안해요"))

    followup = result["pipeline_details"]["agents"]["followup"]["question"]

    assert "잠드는 데 오래 걸리는 편인가요" in followup
    assert followup in result["response"]


def test_sleep_anxiety_small_action_is_action_not_empathy_sentence():
    result = asyncio.run(
        _run_message(
            "요즘 잠을 못 자고 불안해요",
            wellness_checkin={
                "mood_score": 3,
                "anxiety_score": 5,
                "loneliness_score": 3,
                "sleep_quality": 1,
                "meal_status": 3,
                "energy_score": 2,
                "stress_score": 4,
            },
        )
    )

    small_action = result["pipeline_details"]["agents"]["small_action"]
    action_text = small_action["action_text"]

    assert any(keyword in action_text for keyword in ("잠", "수면", "불안", "발바닥", "화면", "조명"))
    assert "감정을 먼저 확인" not in action_text
    assert "공감" not in action_text
    assert "기분이 우울" not in action_text
    assert f"오늘의 작은 행동으로는 {action_text}" in result["response"]


def test_risk_stage_matches_safety_agent_view():
    result = asyncio.run(
        _run_message(
            "요즘 잠을 못 자고 불안해요",
            wellness_checkin={
                "mood_score": 3,
                "anxiety_score": 5,
                "loneliness_score": 3,
                "sleep_quality": 1,
                "meal_status": 3,
                "energy_score": 2,
                "stress_score": 4,
            },
        )
    )

    safety = result["pipeline_details"]["agents"]["safety"]

    assert result["risk_stage"] == safety["risk_stage"]


def test_crisis_flow_takes_priority_without_general_followup_or_small_action():
    result = asyncio.run(_run_message("죽고 싶어요. 지금 자해하고 싶어요."))

    agents = result["pipeline_details"].get("agents", {})

    assert result["requires_crisis_response"] is True
    assert result["risk_stage"] == "위험"
    assert not agents.get("followup", {}).get("has_question", False)
    assert not agents.get("small_action", {}).get("has_action", False)
    assert "prompt_context" not in agents
    assert "잠드는 데 오래 걸리는 편인가요" not in result["response"]
    assert "발바닥 감각" not in result["response"]


def test_non_mock_local_prompt_receives_agent_context():
    class PromptCapture:
        def __init__(self):
            self.local_kwargs = None

        def gen_cloud_prompt(self, **kwargs):
            return SimpleNamespace(system_message="system", user_message="user")

        def gen_local_prompt(self, **kwargs):
            self.local_kwargs = kwargs
            return SimpleNamespace(
                to_messages=lambda: [{"role": "user", "content": "user"}],
            )

    agent = PsychologistAgent(
        config=AgentConfig(
            enable_safety_check=False,
            enable_rag=False,
            enable_risk_audit=False,
            enable_audit_logging=False,
        ),
        mock_mode=True,
    )
    agent.mock_mode = False
    agent._initialized = True
    agent.prompt_generator = PromptCapture()
    agent.pii_redactor = SimpleNamespace(
        redact=Mock(return_value=SimpleNamespace(redacted_text="redacted", entity_count=0, entities=[]))
    )
    agent.cloud_client = SimpleNamespace(analyze=AsyncMock(return_value=AnalysisResult()))
    agent.local_generator = SimpleNamespace(
        create_chat_completion=AsyncMock(
            return_value=GenerationResult(
                text="Generated response",
                tokens_generated=2,
                finish_reason="stop",
                generation_time_ms=1.0,
            )
        )
    )
    agent.memory_store = SimpleNamespace(
        get_memory_context=AsyncMock(
            return_value=SimpleNamespace(
                is_empty=lambda: True,
                recent_summaries=[],
                facts=[],
                directives=[],
                emotional_trend=[],
            )
        ),
        get_cloud_context=AsyncMock(return_value=([], None)),
        get_local_context=AsyncMock(return_value=[]),
    )
    agent.session_manager = SimpleNamespace(
        add_to_history=AsyncMock(),
        update_activity=AsyncMock(),
    )
    agent.counseling_retriever = SimpleNamespace(
        recommend=Mock(
            return_value=SimpleNamespace(
                intervention_hint="작은 단계를 제안하세요.",
                matched_record_id="counseling-test",
                category="support",
                score=1.0,
            )
        )
    )
    agent.empathy_retriever = SimpleNamespace(
        recommend=Mock(
            return_value=SimpleNamespace(
                empathy_style_hint="차분하게 공감하세요.",
                emotion_label="불안",
                empathy_label="위로",
                matched_record_id="empathy-test",
                score=1.0,
            )
        )
    )
    agent.wellness_recommender = SimpleNamespace(recommend=Mock(return_value=None))

    result = asyncio.run(agent.process_message("요즘 잠을 못 자고 불안해요", "session-1"))
    agent_context = agent.prompt_generator.local_kwargs["agent_context"]

    assert result["requires_crisis_response"] is False
    assert agent_context["decision"]["primary_action"]
    assert agent_context["emotional_state"]["state_summary"]
    assert "question" in agent_context["followup"]
    assert "small_action" in agent_context


def test_agents_pipeline_details_do_not_include_raw_looking_keys():
    result = asyncio.run(_run_message("요즘 잠을 못 자고 불안해요"))
    rendered = str(result["pipeline_details"].get("agents", {}))

    for key in RAW_KEYS:
        assert key not in rendered


def test_internal_hint_labels_are_not_exposed_in_response():
    result = asyncio.run(_run_message("요즘 잠을 못 자고 불안해요"))

    assert "상담 참고" not in result["response"]
    assert "공감 참고" not in result["response"]
    assert "웰니스 참고" not in result["response"]
