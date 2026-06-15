"""Gradio demo for the Psychologist Agent."""

from __future__ import annotations

import html
import os
import socket
from datetime import datetime
from typing import Any, Dict, List, Optional, Tuple, TYPE_CHECKING

os.environ.setdefault("LLM_TYPE", "MOCK")

from src.utils.logging_config import setup_logging

if TYPE_CHECKING:
    from src.main import PsychologistAgent

logger = setup_logging("demo_app")

agent: Optional["PsychologistAgent"] = None
current_session_id: Optional[str] = None
last_agent_result: Optional[Dict[str, Any]] = None

ChatMessage = Dict[str, str]
INITIAL_ASSISTANT_MESSAGE = "안녕하세요. 오늘 마음 상태는 어떤가요? 편하게 한 문장으로 이야기해도 괜찮아요."
INITIAL_CHAT_HISTORY: List[ChatMessage] = [
    {"role": "assistant", "content": INITIAL_ASSISTANT_MESSAGE}
]

RISK_KEYWORDS = (
    "죽고 싶",
    "자해",
    "죽어버리",
    "사라지고 싶",
)

RAW_LOOKING_KEYS = {
    "raw_text",
    "raw_input",
    "user_input",
    "assistant_response",
    "conversation",
    "content",
    "transcript",
    "message",
    "source_conversation",
}

INTERNAL_HINT_LABELS = (
    "상담 참고",
    "공감 참고",
    "웰니스 참고",
    "심리상담 데이터 기반 힌트",
    "공감형 대화 기반 힌트",
    "웰니스 기반 힌트",
)

AGENT_SECTION_TITLES = (
    "Safety Agent",
    "Emotion Agent",
    "Intent Agent",
    "Dataset Strategy Agent",
    "Memory Agent / Proactive Recall",
    "Emotional State Agent",
    "Decision Agent",
    "Response Agent",
)

INTENT_LABEL_KO = {
    "SLEEP_PROBLEM": "수면 문제",
    "ANXIETY_SUPPORT": "불안",
    "STRESS_SUPPORT": "스트레스",
    "LOW_MOOD_SUPPORT": "무기력",
    "NEED_EMPATHY": "공감 필요",
    "NEED_ADVICE": "조언 필요",
    "LONELINESS_SUPPORT": "고립감",
    "CRISIS_RISK": "위험 신호",
    "CRISIS_SIGNAL": "위험 신호",
    "RELATIONSHIP_STRESS": "관계 스트레스",
    "WORK_OR_STUDY_STRESS": "일/학업 스트레스",
    "FAMILY_CONFLICT": "가족 갈등",
    "LOW_SELF_ESTEEM": "자존감 저하",
    "SUBSTANCE_OR_ADDICTION": "중독 관련 고민",
    "GRIEF_SUPPORT": "상실/애도",
    "SUPPORT_REQUEST": "정서 지원 요청",
    "EMOTIONAL_DISCLOSURE": "감정 표현",
    "SAFETY_CONCERN": "안전 우려",
    "PRACTICAL_HELP": "실질 도움 요청",
    "REFLECTION": "자기 성찰",
    "MEMORY_UPDATE": "상담 내용 업데이트",
    "SMALL_ACTION": "작은 실천",
    "CLARIFICATION": "상황 확인",
    "OTHER_CONCERN": "기타 고민",
}

CAUSE_LABEL_KO = {
    "sleep_maintenance": "수면 중 자주 깸",
    "worry_or_anxiety": "걱정이나 불안",
    "lifestyle_rhythm": "생활 리듬",
    "physical_fatigue": "몸의 피로",
    "task_pressure": "해야 할 일의 압박",
    "relationship_stress": "관계 스트레스",
    "future_uncertainty": "미래에 대한 불확실성",
    "accumulated_fatigue": "누적된 피로",
    "exhaustion": "소진감",
    "isolation": "고립감",
    "low_self_evaluation": "자기 평가 저하",
    "repeated_failure_experience": "반복된 실패감",
    "overload": "과부하",
    "unclear_starting_point": "시작점이 불명확함",
    "pressure_to_finish": "끝내야 한다는 압박",
    "fear_of_failure": "실패에 대한 걱정",
    "communication_gap": "소통의 어긋남",
    "fear_of_rejection": "거절에 대한 두려움",
    "loneliness_in_relationship": "관계 안의 외로움",
    "boundary_pressure": "관계 경계 부담",
}


async def get_agent() -> "PsychologistAgent":
    global agent
    if agent is None:
        from src.main import PsychologistAgent

        agent = PsychologistAgent()
        await agent.initialize()
        logger.info("Agent initialized for demo")
    return agent


async def get_session_id(active_agent: "PsychologistAgent") -> str:
    global current_session_id
    if current_session_id is None:
        session = await active_agent.session_manager.create_session()
        current_session_id = session.session_id
    return current_session_id


def has_risk_keyword(message: str) -> bool:
    return any(keyword in message for keyword in RISK_KEYWORDS)


def escape_text(value: Any) -> str:
    return html.escape(str(value))


def safe_body_text(value: Any) -> str:
    return escape_text(value).replace("\n", "<br>")


def wrap_card(title: str, body_md: str, crisis: bool = False) -> str:
    card_class = "output-card crisis" if crisis else "output-card"
    return f"<div class='{card_class}'>\n\n## {escape_text(title)}\n\n{body_md}\n\n</div>"


def _as_dict(value: Any) -> Dict[str, Any]:
    return value if isinstance(value, dict) else {}


def _safe_key_value(key: str, value: Any) -> Optional[str]:
    if key in RAW_LOOKING_KEYS:
        return None
    if isinstance(value, bool):
        return f"{key}: {value}"
    if isinstance(value, (int, float)):
        return f"{key}: {value}"
    if value is None:
        return None
    if isinstance(value, str):
        cleaned = value.strip()
        if not cleaned or len(cleaned) > 80 or "\n" in cleaned:
            return None
        if any(label in cleaned for label in INTERNAL_HINT_LABELS):
            return None
        return f"{key}: {escape_text(cleaned)}"
    return None


def _safe_list(values: Any, *, max_items: int = 6) -> List[str]:
    if not isinstance(values, list):
        return []

    safe_values: List[str] = []
    for value in values:
        if not isinstance(value, str):
            continue
        cleaned = value.strip()
        if not cleaned or len(cleaned) > 80 or "\n" in cleaned:
            continue
        if cleaned in RAW_LOOKING_KEYS:
            continue
        safe_values.append(escape_text(cleaned))
        if len(safe_values) >= max_items:
            break
    return safe_values


def _bool_from_presence(value: Any) -> bool:
    return bool(value) if not isinstance(value, dict) else bool(value.keys())


def _agent_details(result: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    details = _as_dict((result or {}).get("pipeline_details", {}))
    return _as_dict(details.get("agents", {}))


def _pipeline_details(result: Optional[Dict[str, Any]]) -> Dict[str, Any]:
    return _as_dict((result or {}).get("pipeline_details", {}))


def _section(title: str, lines: List[str]) -> str:
    body = "\n".join(f"- {line}" for line in lines if line) or "- not available"
    return f"### {title}\n{body}"


def _extract_labels(agent_data: Dict[str, Any]) -> List[str]:
    labels = _safe_list(agent_data.get("labels"))
    if labels:
        return labels

    candidates = agent_data.get("candidates")
    if isinstance(candidates, list):
        extracted = []
        for candidate in candidates:
            candidate_dict = _as_dict(candidate)
            label = candidate_dict.get("label")
            if isinstance(label, str):
                extracted.append(label)
        return _safe_list(extracted)

    secondary = _safe_list(agent_data.get("secondary_labels"))
    primary = agent_data.get("primary_label") or agent_data.get("primary_intent")
    if isinstance(primary, str):
        return _safe_list([primary] + secondary)
    return secondary


def _korean_intent_labels(labels: List[str]) -> List[str]:
    translated: List[str] = []
    seen = set()
    for label in labels:
        cleaned = str(label or "").strip()
        if not cleaned:
            continue
        display = INTENT_LABEL_KO.get(cleaned, cleaned)
        if display not in seen:
            translated.append(display)
            seen.add(display)
    return translated


def _expert_guidance_for_stage(risk_stage: str) -> str:
    if risk_stage == "위험":
        return "즉시 109, 119, 112에 연락하고, 가까운 믿을 수 있는 사람에게 알리세요. 즉각적인 위험이 있으면 가까운 응급실이나 지역 정신건강복지센터로 가세요."
    return "필요하면 가까운 사람이나 상담센터에 도움을 요청할 수 있어요."


def _dataset_lines(summary: Dict[str, Any], result: Optional[Dict[str, Any]]) -> List[str]:
    details = _pipeline_details(result)
    hint_keys = []
    for key in ("counseling_hint", "empathy_style_hint", "wellness_hint"):
        if summary.get(key) or (result or {}).get(key):
            hint_keys.append(key)

    lines = [f"hint_keys: {', '.join(hint_keys) if hint_keys else 'none'}"]
    for source_key in ("counseling", "empathy", "wellness"):
        source = _as_dict(details.get(source_key))
        category = source.get("category") or source.get("matched_category")
        score = source.get("score")
        if score is None:
            score = source.get("similarity_score")
        if score is None:
            score = source.get("confidence")
        matched_record_id = source.get("matched_record_id")
        safe_parts = []
        if isinstance(category, str) and len(category) <= 80:
            safe_parts.append(f"category={escape_text(category)}")
        if isinstance(score, (int, float)):
            safe_parts.append(f"score={score}")
            if score <= 0:
                safe_parts.append("low_confidence_match=True")
        if isinstance(matched_record_id, str) and matched_record_id:
            safe_parts.append(f"record_id_present=True")
        if safe_parts:
            lines.append(f"{source_key}: " + ", ".join(safe_parts))
    return lines


def _final_safety_summary(
    summary: Dict[str, Any],
    result: Dict[str, Any],
    safety: Dict[str, Any],
) -> Dict[str, Any]:
    final_stage = result.get("risk_stage") or summary.get("risk_stage", "관심")
    final_level = result.get("risk_level") or summary.get("risk_level", "none")
    final_crisis = result.get(
        "requires_crisis_response",
        summary.get("requires_crisis_response", False),
    )

    merged = dict(safety)
    merged.update(
        {
            "risk_stage": final_stage,
            "risk_level": final_level,
            "requires_crisis_response": final_crisis,
        }
    )
    return merged


DEFAULT_SAFETY_NOTICE_START = "이 AI는 의료 진단이나 치료를 하지 않으며 전문 상담사를 대체하지 않습니다."


def _strip_default_safety_notice(response_text: str, *, risk_stage: str) -> str:
    if risk_stage == "위험":
        return response_text

    marker = "\n\n" + DEFAULT_SAFETY_NOTICE_START
    if marker in response_text:
        return response_text.split(marker, 1)[0].rstrip()
    if response_text.startswith(DEFAULT_SAFETY_NOTICE_START):
        return ""
    return response_text


def build_agent_pipeline_markdown(
    summary: Dict[str, Any],
    result: Optional[Dict[str, Any]] = None,
) -> str:
    """Build a raw-text-safe Agent Pipeline View markdown block."""
    summary = summary or {}
    result = result or {}
    details = _pipeline_details(result)
    agents = _agent_details(result)
    timing = _as_dict(details.get("timing"))

    safety = _final_safety_summary(
        summary,
        result,
        _as_dict(agents.get("safety")) or _as_dict(details.get("safety")),
    )
    emotion = _as_dict(agents.get("emotion"))
    intent = _as_dict(agents.get("intent"))
    memory = _as_dict(agents.get("recall")) or _as_dict(agents.get("memory")) or _as_dict(details.get("memory_context"))
    memory = _as_dict(agents.get("memory_recall")) or memory
    state = _as_dict(agents.get("state")) or _as_dict(agents.get("emotional_state"))
    decision = _as_dict(agents.get("decision"))

    safety_lines = [
        _safe_key_value("risk_stage", safety.get("risk_stage", summary.get("risk_stage", "관심"))),
        _safe_key_value(
            "requires_crisis_response",
            safety.get("requires_crisis_response", summary.get("requires_crisis_response", False)),
        ),
        _safe_key_value("risk_level", safety.get("risk_level", summary.get("risk_level", "none"))),
    ]

    emotion_labels = _extract_labels(emotion)
    emotion_lines = [
        _safe_key_value("dominant_label", emotion.get("dominant_label") or emotion.get("primary_label")),
        f"labels: {', '.join(emotion_labels) if emotion_labels else 'none'}",
        _safe_key_value("labels_count", len(emotion_labels)),
        _safe_key_value("intensity", emotion.get("intensity")),
        _safe_key_value("confidence", emotion.get("confidence")),
    ]

    intent_labels = _extract_labels(intent)
    intent_lines = [
        _safe_key_value("primary_intent", intent.get("primary_intent")),
        _safe_key_value("s2_suspected", intent.get("s2_suspected")),
        _safe_key_value("s3_sos", intent.get("s3_sos")),
        f"labels: {', '.join(intent_labels) if intent_labels else 'none'}",
    ]

    memory_counts = []
    for key in ("recent_summaries", "facts", "directives", "emotional_trend"):
        value = memory.get(key)
        if isinstance(value, int):
            memory_counts.append(f"{key}={value}")
        elif isinstance(value, list):
            memory_counts.append(f"{key}={len(value)}")
    recalled_keys = _safe_list(memory.get("recalled_keys"))
    repeated_concerns = _safe_list(memory.get("repeated_concerns"))
    memory_lines = [
        f"memory_context_count: {', '.join(memory_counts) if memory_counts else 'none'}",
        f"recalled_keys: {', '.join(recalled_keys) if recalled_keys else 'none'}",
        f"repeated_concerns: {', '.join(repeated_concerns) if repeated_concerns else 'none'}",
        _safe_key_value("last_small_action_present", _bool_from_presence(memory.get("last_small_action"))),
        _safe_key_value("next_follow_up_present", _bool_from_presence(memory.get("next_follow_up"))),
    ]

    state_summary = _safe_list(state.get("state_summary"))
    state_lines = [
        f"state_summary: {', '.join(state_summary) if state_summary else 'none'}",
    ]
    for key in ("mood", "anxiety", "stress", "sleep", "energy", "safety", "rapport"):
        state_lines.append(_safe_key_value(key, state.get(key)))

    secondary_actions = _safe_list(decision.get("secondary_actions"))
    reason_codes = _safe_list(decision.get("reason_codes"))
    constraints = _as_dict(decision.get("response_constraints"))
    constraint_lines = []
    for key in sorted(constraints.keys()):
        rendered = _safe_key_value(key, constraints.get(key))
        if rendered:
            constraint_lines.append(rendered)
    decision_lines = [
        _safe_key_value("primary_action", decision.get("primary_action") or decision.get("action")),
        f"secondary_actions: {', '.join(secondary_actions) if secondary_actions else 'none'}",
        f"reason_codes: {', '.join(reason_codes) if reason_codes else 'none'}",
        f"response_constraints: {', '.join(constraint_lines) if constraint_lines else 'none'}",
    ]

    response_lines = [
        _safe_key_value("response_generated", bool(result.get("response") or summary.get("response_preview"))),
        _safe_key_value("safety_notice_added", bool(summary.get("requires_crisis_response"))),
        _safe_key_value("mode", result.get("response_source") or summary.get("response_source")),
    ]
    timing_lines = []
    for key in (
        "initialize",
        "safety",
        "dataset_retrieval",
        "memory_context",
        "agent_pipeline",
        "response_generation",
        "total",
    ):
        rendered = _safe_key_value(key, timing.get(key))
        if rendered:
            timing_lines.append(rendered)

    sections = [
        _section("Safety Agent", safety_lines),
        _section("Emotion Agent", emotion_lines),
        _section("Intent Agent", intent_lines),
        _section("Dataset Strategy Agent", _dataset_lines(summary, result)),
        _section("Memory Agent / Proactive Recall", memory_lines),
        _section("Emotional State Agent", state_lines),
        _section("Decision Agent", decision_lines),
        _section("Response Agent", response_lines),
        _section("Timing", timing_lines),
    ]
    return wrap_card("Agent Pipeline View", "\n\n".join(sections))


def build_crisis_markdown() -> str:
    return wrap_card(
        "위기 안내 카드",
        "\n".join(
            [
                "- 위험 단계: 위험",
                "- 지금은 안전이 가장 중요해요. 혼자 버티지 말고 즉시 도움을 요청하세요.",
                "- 109(자살예방), 119(응급), 112(경찰) 중 하나로 바로 연락하세요.",
                "- 가까이에 믿을 수 있는 사람에게 지금 연락해서 혼자 있지 않도록 해주세요.",
                "- 즉각적인 위험이 있으면 가장 가까운 응급실이나 지역 정신건강복지센터로 가세요.",
            ]
        ),
        crisis=True,
    )


def infer_risk_stage(wellness_checkin: Dict[str, int]) -> str:
    concern_signals = [
        wellness_checkin.get("mood_score", 3) <= 2,
        wellness_checkin.get("anxiety_score", 3) >= 4,
        wellness_checkin.get("loneliness_score", 3) >= 4,
        wellness_checkin.get("sleep_quality", 3) <= 2,
        wellness_checkin.get("meal_status", 3) <= 2,
        wellness_checkin.get("energy_score", 3) <= 2,
        wellness_checkin.get("stress_score", 3) >= 4,
    ]
    return "주의" if any(concern_signals) else "관심"


def build_counseling_hint(message: str, wellness_checkin: Dict[str, int]) -> str:
    if "공부" in message:
        return "할 일을 아주 작게 쪼개서 10분만 시작해도 부담이 줄어요."
    if wellness_checkin.get("stress_score", 3) >= 4:
        return "스트레스가 높을 때는 우선순위를 하나만 정하고 나머지는 잠시 미뤄보세요."
    if wellness_checkin.get("anxiety_score", 3) >= 4:
        return "불안이 올라올 때는 호흡을 천천히 맞추며 현재 감각에 집중해보세요."
    return "감정을 설명하기 어려우면, 지금 가장 힘든 점 하나만 먼저 적어도 충분해요."


def build_empathy_hint(message: str, wellness_checkin: Dict[str, int]) -> str:
    if "외로" in message:
        return "지금 많이 혼자 버티고 있다는 느낌을 먼저 알아봐 주는 반응이 도움이 됩니다."
    if wellness_checkin.get("loneliness_score", 3) >= 4:
        return "외로움이 높을수록 판단보다 공감과 동행 메시지가 먼저 필요해요."
    return "반응은 조언보다 감정 확인으로 시작하면 더 안전하고 자연스럽습니다."


def build_wellness_hint(wellness_checkin: Dict[str, int]) -> str:
    hints = []
    if wellness_checkin.get("sleep_quality", 3) <= 2:
        hints.append("수면 회복을 우선해 보세요.")
    if wellness_checkin.get("meal_status", 3) <= 2:
        hints.append("따뜻한 물이나 간단한 식사부터 챙겨보세요.")
    if wellness_checkin.get("energy_score", 3) <= 2:
        hints.append("오늘은 짧게 쉬는 시간을 자주 두는 편이 좋아요.")
    if wellness_checkin.get("stress_score", 3) >= 4:
        hints.append("스트레스가 높으면 해야 할 일을 한 줄로만 적어보세요.")
    return " ".join(hints) or "기본 리듬을 지키는 것만으로도 회복에 도움이 됩니다."


def build_mock_summary(
    message: str,
    wellness_checkin: Dict[str, int],
    response_text: str,
    *,
    risk_stage: Optional[str] = None,
    source: str = "mock",
) -> Dict[str, Any]:
    stage = risk_stage or infer_risk_stage(wellness_checkin)
    risk_level = "attention" if stage == "관심" else "high" if stage == "위험" else "moderate"
    return {
        "session_id": "",
        "risk_level": risk_level,
        "risk_stage": stage,
        "requires_crisis_response": False,
        "counseling_hint": build_counseling_hint(message, wellness_checkin),
        "empathy_style_hint": build_empathy_hint(message, wellness_checkin),
        "wellness_hint": build_wellness_hint(wellness_checkin),
        "response_source": source,
        "response_preview": response_text,
        "wellness_checkin": wellness_checkin,
    }


def build_general_markdown(
    summary: Dict[str, Any],
    response_text: str,
    result: Optional[Dict[str, Any]] = None,
) -> str:
    risk_stage = summary.get("risk_stage", "관심")
    visible_response = _strip_default_safety_notice(response_text, risk_stage=risk_stage)
    return "\n\n".join(
        [
            wrap_card("상담 응답 카드", f"- 위험 단계: {escape_text(risk_stage)}"),
            wrap_card("AI 상담 응답", safe_body_text(visible_response)),
        ]
    )


def build_chat_response_text(
    summary: Dict[str, Any],
    response_text: str,
) -> str:
    """Return only user-facing chat text, without debug pipeline or duplicate notice."""
    risk_stage = (summary or {}).get("risk_stage", "관심")
    return _strip_default_safety_notice(response_text, risk_stage=risk_stage).strip()


def initial_chat_messages() -> List[ChatMessage]:
    """Return a fresh copy of the initial chat messages."""
    return [dict(message) for message in INITIAL_CHAT_HISTORY]


def initial_chat_history() -> List[ChatMessage]:
    """Backward-compatible alias for the initial chat messages."""
    return initial_chat_messages()


def reset_chat_history() -> Tuple[List[ChatMessage], List[ChatMessage]]:
    """Reset chat display and state to the initial assistant greeting."""
    history = initial_chat_messages()
    return history, [dict(message) for message in history]


def _bounded_score(value: Any, default: int = 3) -> int:
    try:
        score = int(value)
    except (TypeError, ValueError):
        score = default
    return max(1, min(5, score))


def _short_note(note: str) -> str:
    compact = " ".join((note or "").split())
    if not compact:
        return ""
    if any(label in compact for label in INTERNAL_HINT_LABELS):
        return ""
    return compact[:80]


def _diary_entries(diary_state: Optional[Dict[str, Any]]) -> List[Dict[str, Any]]:
    if not isinstance(diary_state, dict) or not diary_state:
        return []
    entries = diary_state.get("entries")
    if isinstance(entries, list):
        return [entry for entry in entries if isinstance(entry, dict)]

    if "mood_score" in diary_state:
        legacy_entry = {
            "timestamp": diary_state.get("timestamp", ""),
            "emotion_label": diary_state.get("emotion_label", "선택 안 함"),
            "mood_score": diary_state.get("mood_score"),
            "anxiety_score": diary_state.get("anxiety_score"),
            "loneliness_score": diary_state.get("loneliness_score"),
            "sleep_quality": diary_state.get("sleep_quality", diary_state.get("sleep_score")),
            "meal_status": diary_state.get("meal_status", 3),
            "energy_score": diary_state.get("energy_score", 3),
            "stress_score": diary_state.get("stress_score", 3),
            "risk_stage": diary_state.get("risk_stage", "관심"),
            "note": diary_state.get("note", ""),
        }
        return [legacy_entry]
    return []


def _score_label(value: Any) -> str:
    return {
        1: "매우 낮음",
        2: "낮음",
        3: "보통",
        4: "높음",
        5: "매우 높음",
    }[_bounded_score(value)]


def _burden_label(value: Any) -> str:
    return {
        1: "낮음",
        2: "약간 있음",
        3: "보통",
        4: "높음",
        5: "매우 높음",
    }[_bounded_score(value)]


def _sleep_label(value: Any) -> str:
    return {
        1: "매우 부족",
        2: "부족",
        3: "보통",
        4: "양호",
        5: "매우 양호",
    }[_bounded_score(value)]


def _energy_label(value: Any) -> str:
    return {
        1: "매우 낮음",
        2: "낮음",
        3: "보통",
        4: "양호",
        5: "매우 높음",
    }[_bounded_score(value)]


def _normalize_agent_key(value: Any) -> str:
    return str(value or "").strip().upper()


def _primary_intent_label(intent: Dict[str, Any]) -> str:
    candidates = []
    primary = intent.get("primary_intent")
    if isinstance(primary, str) and primary:
        candidates.append(primary)
    candidates.extend(_extract_labels(intent))

    for candidate in candidates:
        normalized = _normalize_agent_key(candidate)
        if normalized:
            return INTENT_LABEL_KO.get(normalized, normalized)
    return "아직 판단 전"


def _state_level(value: Any, *, reverse: bool = False) -> str:
    try:
        score = float(value)
    except (TypeError, ValueError):
        return ""

    if reverse:
        if score < 0.4:
            return "낮음"
        if score < 0.65:
            return "보통"
        return "양호"

    if score >= 0.65:
        return "높음"
    if score >= 0.4:
        return "보통"
    return "낮음"


def _diary_burden_level(value: Any) -> str:
    score = _bounded_score(value)
    if score >= 4:
        return "높음"
    if score == 3:
        return "보통"
    return "낮음"


def _diary_recovery_level(value: Any) -> str:
    score = _bounded_score(value)
    if score <= 2:
        return "낮음"
    if score == 3:
        return "보통"
    return "양호"


def _emotional_state_labels(
    state: Dict[str, Any],
    latest_diary: Dict[str, Any],
    wellness_checkin: Dict[str, Any],
) -> List[str]:
    labels = []

    anxiety = _state_level(state.get("anxiety"))
    stress = _state_level(state.get("stress"))
    sleep = _state_level(state.get("sleep"), reverse=True)

    if not anxiety and (latest_diary or wellness_checkin):
        anxiety = _diary_burden_level(
            latest_diary.get("anxiety_score", wellness_checkin.get("anxiety_score", 3))
        )
    if not stress and (latest_diary or wellness_checkin):
        stress = _diary_burden_level(
            latest_diary.get("stress_score", wellness_checkin.get("stress_score", 3))
        )
    if not sleep and (latest_diary or wellness_checkin):
        sleep = _diary_recovery_level(
            latest_diary.get("sleep_quality", wellness_checkin.get("sleep_quality", 3))
        )

    if anxiety:
        labels.append(f"불안 {anxiety}")
    if stress:
        labels.append(f"스트레스 {stress}")
    if sleep:
        labels.append(f"수면 회복감 {sleep}")
    return labels or ["상담 또는 감정일기 저장 후 표시"]


def _is_high_anxiety_or_stress(
    state: Dict[str, Any],
    latest_diary: Dict[str, Any],
    wellness_checkin: Dict[str, Any],
) -> bool:
    for key in ("anxiety", "stress"):
        try:
            if float(state.get(key, 0.0)) >= 0.65:
                return True
        except (TypeError, ValueError):
            pass

    anxiety_score = latest_diary.get("anxiety_score", wellness_checkin.get("anxiety_score", 3))
    stress_score = latest_diary.get("stress_score", wellness_checkin.get("stress_score", 3))
    return _bounded_score(anxiety_score) >= 4 or _bounded_score(stress_score) >= 4


def _selected_cause_label(cause: Dict[str, Any]) -> Tuple[str, str]:
    selected = cause.get("selected_cause") if isinstance(cause.get("selected_cause"), str) else ""
    if not selected:
        candidates = cause.get("cause_candidates")
        if isinstance(candidates, list):
            selected = next((item for item in candidates if isinstance(item, str) and item), "")
    return selected, CAUSE_LABEL_KO.get(selected, selected) if selected else ""


def _decision_action_summary(decision: Dict[str, Any], small_action: Dict[str, Any]) -> str:
    primary = _normalize_agent_key(decision.get("primary_action") or decision.get("action"))
    secondary = {
        _normalize_agent_key(action)
        for action in _safe_list(decision.get("secondary_actions"), max_items=8)
    }

    parts = []
    if primary == "ESCALATE_SAFETY":
        return "즉시 안전 안내"
    if primary == "ASK_FOLLOW_UP":
        parts.append("후속 질문")
    elif primary == "RESPOND_SUPPORTIVELY":
        parts.append("공감 응답")
    elif primary == "SUMMARIZE_STATE":
        parts.append("상태 요약")

    if "SUGGEST_SMALL_ACTION" in secondary or bool(small_action.get("has_action")):
        parts.append("작은 실천 행동 제안")
    if "UPDATE_MEMORY" in secondary:
        parts.append("상담 흐름 기억")
    return " + ".join(parts) if parts else "공감 응답"


def _next_counseling_plan(
    *,
    risk_stage: str,
    selected_cause: str,
    high_anxiety_or_stress: bool,
) -> List[str]:
    if risk_stage == "위험":
        return [
            "지금은 상담 계획보다 즉각적인 안전 확보가 우선입니다.",
            "109, 119, 112 중 하나로 바로 연락하고, 가까이에 믿을 수 있는 사람에게 지금 알려 혼자 있지 않도록 합니다.",
        ]

    plan = []
    if selected_cause == "sleep_maintenance":
        plan.append("중간에 깨는 원인이 걱정 때문인지, 신체 긴장 때문인지 확인합니다.")
    elif selected_cause == "worry_or_anxiety":
        plan.append("잠들기 전 커지는 걱정의 주제를 함께 좁혀봅니다.")
    else:
        plan.append("현재 가장 부담이 큰 감정과 상황을 한 가지로 좁혀 다음 대화를 이어갑니다.")

    if high_anxiety_or_stress:
        plan.append("불안과 스트레스 변화를 감정일기로 추적합니다.")
    return plan


def _safe_report_sentence(value: Any, fallback: str) -> str:
    text = " ".join(str(value or "").split()).strip()
    if not text:
        return fallback
    if len(text) > 120:
        return fallback
    if any(label in text for label in INTERNAL_HINT_LABELS):
        return fallback
    if any(raw_key in text for raw_key in RAW_LOOKING_KEYS):
        return fallback
    return escape_text(text)


def _recent_status_labels(
    state: Dict[str, Any],
    latest_diary: Dict[str, Any],
    wellness_checkin: Dict[str, Any],
) -> Dict[str, str]:
    if latest_diary:
        return {
            "불안": _burden_label(latest_diary.get("anxiety_score")),
            "스트레스": _burden_label(latest_diary.get("stress_score")),
            "수면 회복감": _diary_recovery_level(latest_diary.get("sleep_quality")),
            "활력": _diary_recovery_level(latest_diary.get("energy_score")),
        }

    if wellness_checkin:
        return {
            "불안": _burden_label(wellness_checkin.get("anxiety_score")),
            "스트레스": _burden_label(wellness_checkin.get("stress_score")),
            "수면 회복감": _diary_recovery_level(wellness_checkin.get("sleep_quality")),
            "활력": _diary_recovery_level(wellness_checkin.get("energy_score")),
        }

    labels: Dict[str, str] = {}
    anxiety = _state_level(state.get("anxiety"))
    stress = _state_level(state.get("stress"))
    sleep = _state_level(state.get("sleep"), reverse=True)
    energy = _state_level(state.get("energy"))
    if anxiety:
        labels["불안"] = anxiety
    if stress:
        labels["스트레스"] = stress
    if sleep:
        labels["수면 회복감"] = sleep
    if energy:
        labels["활력"] = energy
    return labels


def _recent_status_summary(status_labels: Dict[str, str]) -> str:
    if not status_labels:
        return "상담 또는 감정일기를 저장하면 최근 상태를 요약해드릴게요."

    high_burdens = [
        label
        for label in ("불안", "스트레스")
        if status_labels.get(label) in {"높음", "매우 높음"}
    ]
    low_recovery = [
        label
        for label in ("수면 회복감", "활력")
        if status_labels.get(label) in {"낮음", "매우 낮음", "부족", "매우 부족"}
    ]

    parts = []
    if high_burdens:
        parts.append(f"{'과 '.join(high_burdens)}가 높고")
    if low_recovery:
        parts.append(f"{'과 '.join(low_recovery)}이 낮은")

    if parts:
        return "현재는 " + ", ".join(parts) + " 상태로 보입니다."

    stable = [
        label
        for label, value in status_labels.items()
        if value in {"보통", "양호", "매우 양호", "높음", "매우 높음"}
    ]
    if stable:
        return f"현재는 {', '.join(stable)} 상태가 비교적 유지되고 있는 것으로 보입니다."
    return "현재 마음 상태는 추가 기록을 통해 더 분명하게 확인할 수 있습니다."


def _change_word(first: Any, last: Any) -> str:
    delta = _bounded_score(last) - _bounded_score(first)
    if delta > 0:
        return "높아지고"
    if delta < 0:
        return "낮아지고"
    return "비슷하게 유지되고"


def _natural_trend_summary(first: Dict[str, Any], last: Dict[str, Any]) -> str:
    changes = {
        "기분": _change_word(first.get("mood_score"), last.get("mood_score")),
        "불안": _change_word(first.get("anxiety_score"), last.get("anxiety_score")),
        "스트레스": _change_word(first.get("stress_score"), last.get("stress_score")),
        "수면 회복감": _change_word(first.get("sleep_quality"), last.get("sleep_quality")),
        "활력": _change_word(first.get("energy_score"), last.get("energy_score")),
    }

    groups: Dict[str, List[str]] = {}
    for label, change in changes.items():
        groups.setdefault(change, []).append(label)

    parts = [
        f"{', '.join(labels)}: {change}"
        for change, labels in groups.items()
    ]
    return "최근 기록과 비교했을 때 " + ", ".join(parts) + " 있는 흐름입니다."


def build_emotional_trend_markdown(diary_state: Optional[Dict[str, Any]]) -> str:
    entries = _diary_entries(diary_state)
    if len(entries) < 2:
        if entries:
            return "- 첫 기준선이 기록됐어요. 감정일기를 한 번 더 저장하면 변화 방향을 함께 보여드릴게요."
        return "- 아직 감정 변화 기록이 없습니다."

    first = entries[0]
    last = entries[-1]
    return _natural_trend_summary(first, last)


def diary_graph_message(diary_state: Optional[Dict[str, Any]]) -> str:
    guidance = (
        "그래프는 여러 번 기록했을 때 장기적인 변화 흐름을 보기 위한 참고 자료입니다. "
        "높을수록 더 안정적이고 회복된 상태를 의미합니다."
    )
    entries = _diary_entries(diary_state)
    if len(entries) < 2:
        return (
            "기록이 2개 이상이면 변화 흐름을 더 분명하게 볼 수 있습니다.\n\n"
            f"{guidance}"
        )
    return guidance


def diary_trend_dataframe(diary_state: Optional[Dict[str, Any]]) -> Any:
    rows = []
    for index, entry in enumerate(_diary_entries(diary_state), start=1):
        record_label = f"{index}번째 기록"
        display_scores = (
            ("기분", _bounded_score(entry.get("mood_score"))),
            ("안정감", 6 - _bounded_score(entry.get("anxiety_score"))),
            ("여유감", 6 - _bounded_score(entry.get("stress_score"))),
            ("수면 회복감", _bounded_score(entry.get("sleep_quality"))),
            ("활력", _bounded_score(entry.get("energy_score"))),
        )
        for label, score in display_scores:
            rows.append(
                {
                    "기록": record_label,
                    "항목": label,
                    "마음 회복 수준": score,
                }
            )

    try:
        import pandas as pd

        frame = pd.DataFrame(rows, columns=["기록", "항목", "마음 회복 수준"])
        return frame
    except Exception:
        return rows


def save_emotion_diary(
    diary_state: Optional[Dict[str, Any]],
    emotion_label: str,
    mood_score: int,
    anxiety_score: int,
    loneliness_score: int,
    sleep_quality: int,
    meal_status: int,
    energy_score: int,
    stress_score: int,
    diary_line: str,
    save_consent: bool,
) -> Tuple[Dict[str, Any], str]:
    """Store timestamped structured diary values for the current demo session."""
    entry = {
        "timestamp": datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
        "emotion_label": str(emotion_label or "선택 안 함"),
        "mood_score": _bounded_score(mood_score),
        "anxiety_score": _bounded_score(anxiety_score),
        "loneliness_score": _bounded_score(loneliness_score),
        "sleep_quality": _bounded_score(sleep_quality),
        "meal_status": _bounded_score(meal_status),
        "energy_score": _bounded_score(energy_score),
        "stress_score": _bounded_score(stress_score),
        "risk_stage": infer_risk_stage(
            {
                "mood_score": _bounded_score(mood_score),
                "anxiety_score": _bounded_score(anxiety_score),
                "loneliness_score": _bounded_score(loneliness_score),
                "sleep_quality": _bounded_score(sleep_quality),
                "meal_status": _bounded_score(meal_status),
                "energy_score": _bounded_score(energy_score),
                "stress_score": _bounded_score(stress_score),
            }
        ),
        "note": _short_note(diary_line),
        "save_consent": bool(save_consent),
    }
    entries = _diary_entries(diary_state)
    entries.append(entry)
    entries = entries[-20:]
    updated_state = {"entries": entries, "latest_entry": entry}

    summary_lines = [
        "- 감정일기가 저장되었습니다. 마음정리 보고서에서 감정 변화 그래프를 확인할 수 있어요.",
    ]
    if not save_consent:
        summary_lines.append("- 기록 저장 동의가 꺼져 있어 현재 데모 세션에서만 임시로 보여줍니다.")

    return updated_state, wrap_card("감정일기 저장 완료", "\n".join(summary_lines))


def build_service_report(
    summary: Optional[Dict[str, Any]],
    diary_state: Optional[Dict[str, Any]],
) -> str:
    """Build a user-facing structured report without raw text."""
    summary = summary or {}
    diary_state = diary_state or {}
    result = last_agent_result or {}
    if not summary and not diary_state and not result:
        return wrap_card("마음정리 보고서", "- 아직 상담 기록이 없습니다.")

    agents = _agent_details(result)
    intent = _as_dict(agents.get("intent"))
    state = _as_dict(agents.get("emotional_state"))
    decision = _as_dict(agents.get("decision"))
    small_action = _as_dict(agents.get("small_action"))
    cause = _as_dict(agents.get("cause_exploration"))
    diary_entries = _diary_entries(diary_state)
    latest_diary = diary_entries[-1] if diary_entries else {}
    wellness_checkin = _as_dict(summary.get("wellness_checkin"))

    risk_stage = summary.get("risk_stage") or result.get("risk_stage") or "관심"
    intent_labels = _extract_labels(intent)
    primary_intent = intent.get("primary_intent")
    action_text = small_action.get("action_text") if isinstance(small_action.get("action_text"), str) else ""

    concern_keywords = []
    if isinstance(primary_intent, str) and primary_intent:
        concern_keywords.append(primary_intent)
    concern_keywords.extend(intent_labels)
    concern_keywords = _korean_intent_labels(_safe_list(concern_keywords, max_items=8))[:4]
    primary_intent_ko = _primary_intent_label(intent)
    secondary_concerns = [
        label for label in concern_keywords
        if label != primary_intent_ko
    ]
    selected_cause, selected_cause_label = _selected_cause_label(cause)
    main_concern = escape_text(selected_cause_label) if selected_cause_label else (
        ", ".join(secondary_concerns) if secondary_concerns else "아직 없음"
    )
    action_summary = _decision_action_summary(decision, small_action)
    high_anxiety_or_stress = _is_high_anxiety_or_stress(state, latest_diary, wellness_checkin)
    next_plan = _next_counseling_plan(
        risk_stage=str(risk_stage),
        selected_cause=selected_cause,
        high_anxiety_or_stress=high_anxiety_or_stress,
    )

    recent_status = _recent_status_labels(state, latest_diary, wellness_checkin)
    recent_state_lines = [
        f"- {label}: {escape_text(value)}"
        for label, value in recent_status.items()
    ]
    if not recent_state_lines:
        recent_state_lines = ["- 상담 또는 감정일기 저장 후 표시됩니다."]
    recent_state_lines.append(
        f"- 최근 상태 요약: {escape_text(_recent_status_summary(recent_status))}"
    )

    risk_lines = [f"- 현재 단계: {escape_text(risk_stage)}"]
    if risk_stage == "위험":
        risk_lines.extend(
            [
                "- 지금은 안전 확보가 가장 중요합니다.",
                "- 109, 119, 112 중 하나로 바로 연락하고 가까이에 믿을 수 있는 사람에게 알려주세요.",
            ]
        )

    agent_summary_lines = [
        f"- 의도 판단: {escape_text(primary_intent_ko)}",
        f"- 원인 탐색: {escape_text(selected_cause_label or main_concern or '아직 탐색 전')}",
        f"- 다음 상담 방향: {escape_text(' '.join(next_plan))}",
    ]
    next_plan_lines = [f"- {escape_text(item)}" for item in next_plan]
    small_action_text = _safe_report_sentence(action_text, "상담 채팅 후 표시됩니다.")
    small_action_lines = [
        f"- {small_action_text}",
        f"- 방향: {escape_text(action_summary)}",
    ]

    sections = []
    sections.append(wrap_card("최근 마음 상태", "\n".join(recent_state_lines)))
    sections.append(wrap_card("현재 위험 단계", "\n".join(risk_lines), crisis=risk_stage == "위험"))
    sections.append(wrap_card("Agent 판단 요약", "\n".join(agent_summary_lines)))
    sections.append(wrap_card("오늘의 작은 실천", "\n".join(small_action_lines)))
    sections.append(wrap_card("최근 마음 회복 흐름", build_emotional_trend_markdown(diary_state)))
    return "\n\n".join(sections)


def build_report_outputs(
    summary: Optional[Dict[str, Any]],
    diary_state: Optional[Dict[str, Any]],
) -> Tuple[str, Any, str]:
    return (
        build_service_report(summary, diary_state),
        diary_trend_dataframe(diary_state),
        diary_graph_message(diary_state),
    )


def build_error_markdown(error_text: str) -> str:
    return wrap_card("오류", f"오류가 발생했습니다: {safe_body_text(error_text)}")


def build_wellness_checkin(
    mood_score: int,
    anxiety_score: int,
    loneliness_score: int,
    sleep_quality: int,
    meal_status: int,
    energy_score: int,
    stress_score: int,
) -> Dict[str, int]:
    return {
        "mood_score": int(mood_score),
        "anxiety_score": int(anxiety_score),
        "loneliness_score": int(loneliness_score),
        "sleep_quality": int(sleep_quality),
        "meal_status": int(meal_status),
        "energy_score": int(energy_score),
        "stress_score": int(stress_score),
    }


def build_summary(result: Dict[str, Any], wellness_checkin: Dict[str, int]) -> Dict[str, Any]:
    details = result.get("pipeline_details", {})
    wellness = details.get("wellness", {}) if isinstance(details, dict) else {}
    safety = details.get("safety", {}) if isinstance(details, dict) else {}

    return {
        "session_id": result.get("session_id", ""),
        "risk_level": result.get("risk_level", "none"),
        "risk_stage": result.get("risk_stage", "관심"),
        "requires_crisis_response": result.get("requires_crisis_response", False),
        "counseling_hint": "present" if result.get("counseling_hint") else "",
        "empathy_style_hint": "present" if result.get("empathy_style_hint") else "",
        "wellness_hint": "present" if (result.get("wellness_hint") or wellness.get("support_hint")) else "",
        "counseling_record_id": details.get("counseling", {}).get("matched_record_id", "") if isinstance(details, dict) else "",
        "empathy_record_id": details.get("empathy", {}).get("matched_record_id", "") if isinstance(details, dict) else "",
        "wellness_record_id": wellness.get("matched_record_id", ""),
        "safety_action": safety.get("action", ""),
        "wellness_checkin": wellness_checkin,
        "response_preview": result.get("response", ""),
    }


async def handle_chat(
    message: str,
    mood_score: int,
    anxiety_score: int,
    loneliness_score: int,
    sleep_quality: int,
    meal_status: int,
    energy_score: int,
    stress_score: int,
) -> Tuple[str, Dict[str, Any]]:
    global last_agent_result
    wellness_checkin = build_wellness_checkin(
        mood_score=mood_score,
        anxiety_score=anxiety_score,
        loneliness_score=loneliness_score,
        sleep_quality=sleep_quality,
        meal_status=meal_status,
        energy_score=energy_score,
        stress_score=stress_score,
    )
    session_id = ""

    try:
        message_text = (message or "").strip()
        if not message_text:
            return "오늘 어떤 일이 있었는지 한 문장만 적어주세요.", {
                "session_id": "",
                "risk_stage": "관심",
                "wellness_checkin": wellness_checkin,
                "empty_message": True,
            }

        if has_risk_keyword(message_text):
            summary = build_mock_summary(
                message_text,
                wellness_checkin,
                "위기 신호가 감지되어 안전 안내를 우선합니다. 지금은 109, 119, 112 중 하나로 바로 연락하고, 가까이에 믿을 수 있는 사람에게 알려 혼자 있지 않도록 해주세요. 즉각적인 위험이 있으면 가장 가까운 응급실이나 지역 정신건강복지센터로 가세요.",
                risk_stage="위험",
                source="crisis-fallback",
            )
            last_agent_result = None
            return build_crisis_markdown(), summary

        active_agent = await get_agent()
        session_id = await get_session_id(active_agent)
        result = await active_agent.process_message(
            user_input=message_text,
            session_id=session_id,
            wellness_checkin=wellness_checkin,
        )
        if not isinstance(result, dict):
            raise TypeError("Agent response must be a dictionary.")
        last_agent_result = result

        response_text = str(result.get("response", "") or "응답이 비어 있습니다.")
        summary = build_summary(result, wellness_checkin)
        if summary.get("requires_crisis_response"):
            return build_crisis_markdown(), summary

        return build_general_markdown(summary, response_text, result), summary

    except Exception as exc:
        logger.exception("Agent path failed, using mock fallback")
        try:
            fallback_response = "지금은 한 번에 다 해결하려 하지 말고, 가장 부담이 작은 한 가지부터 시작해 보세요."
            summary = build_mock_summary(
                (message or "").strip(),
                wellness_checkin,
                fallback_response,
                source="mock-fallback",
            )
            last_agent_result = None
            return build_general_markdown(summary, fallback_response), summary
        except Exception as fallback_exc:
            logger.exception("Fallback generation failed")
            return build_error_markdown(f"{exc} / fallback: {fallback_exc}"), {
                "session_id": session_id,
                "error": str(exc),
                "fallback_error": str(fallback_exc),
                "wellness_checkin": wellness_checkin,
            }


async def handle_chat_ui(
    message: str,
    chat_history: Optional[List[Any]],
    mood_score: int,
    anxiety_score: int,
    loneliness_score: int,
    sleep_quality: int,
    meal_status: int,
    energy_score: int,
    stress_score: int,
) -> Tuple[List[ChatMessage], List[ChatMessage], str, str, Dict[str, Any], str]:
    """Handle one chat turn for the user-facing Gradio chat UI."""
    history = normalize_chat_history(chat_history)
    if not history:
        history = initial_chat_messages()
    message_text = (message or "").strip()
    if not message_text:
        return history, [dict(message) for message in history], "", "", {"empty_message": True}, ""

    markdown, summary = await handle_chat(
        message_text,
        mood_score,
        anxiety_score,
        loneliness_score,
        sleep_quality,
        meal_status,
        energy_score,
        stress_score,
    )

    response_text = markdown
    pipeline_markdown = ""
    if not summary.get("empty_message"):
        pipeline_markdown = build_agent_pipeline_markdown(summary, last_agent_result)
        response_text = build_chat_response_text(
            summary,
            str(summary.get("response_preview") or markdown),
        )

    history.extend(
        [
            {"role": "user", "content": message_text},
            {"role": "assistant", "content": response_text},
        ]
    )
    return history, [dict(message) for message in history], "", pipeline_markdown, summary, "응답이 준비됐어요."


def normalize_chat_history(chat_history: Optional[List[Any]]) -> List[ChatMessage]:
    """Return Gradio Chatbot messages format, accepting older tuple history safely."""
    normalized: List[ChatMessage] = []
    for item in chat_history or []:
        if isinstance(item, dict):
            role = item.get("role")
            content = item.get("content")
            if role in {"user", "assistant"} and isinstance(content, str):
                normalized.append({"role": role, "content": content})
            continue

        if isinstance(item, (tuple, list)) and len(item) == 2:
            user_message, assistant_message = item
            if isinstance(user_message, str) and user_message:
                normalized.append({"role": "user", "content": user_message})
            if isinstance(assistant_message, str) and assistant_message:
                normalized.append({"role": "assistant", "content": assistant_message})

    return normalized


def toggle_nickname_input(anonymous_enabled: bool) -> Dict[str, Any]:
    """Enable nickname only when anonymous mode is off."""
    try:
        import gradio as gr

        return gr.update(interactive=not bool(anonymous_enabled), value="" if anonymous_enabled else None)
    except Exception:
        return {"interactive": not bool(anonymous_enabled)}


def show_status_checkin_panel() -> Tuple[Dict[str, Any], str]:
    """Reveal optional status check controls from the next-step button."""
    message = "상태 체크하기 영역에서 기분, 불안, 외로움, 수면 상태를 선택해 상담에 반영할 수 있어요."
    try:
        import gradio as gr

        return gr.update(visible=True), message
    except Exception:
        return {"visible": True}, message


def create_demo():
    """Create and return the Gradio demo interface."""
    try:
        import gradio as gr
    except ImportError as exc:
        raise ImportError("gradio is required for the demo. Install with: pip install gradio") from exc
    custom_css = """
    body, .gradio-container, .main, .wrap { background: #f7f8fb !important; }
    .chat-shell { max-width: 980px; margin: 18px auto; }
    .app-title { font-size:24px; font-weight:700; color:#202124; margin-bottom:2px; }
    .app-sub { font-size:13px; color:#5f6368; margin-bottom:14px; }
    .chatbot { border-radius:12px; height:520px; max-height:520px; overflow-y:auto; }
    .input-row textarea { border-radius:10px !important; }
    .cta { border-radius:10px; font-weight:700; }
    .status-line { min-height:28px; color:#4c6f8f; font-size:13px; }
    .small-note { font-size:12px; color:#6f7378; text-align:center; margin-top:8px; }
    .output-card { background:#ffffff; border-radius:8px; padding:12px; margin-top:8px; border:1px solid #e5e7eb; }
    .crisis { background:#fff1f1; border-left:4px solid #d93025; }
    """

    with gr.Blocks(title="Psychologist AI Agent", css=custom_css) as demo:
        with gr.Column(elem_classes="chat-shell"):
            gr.Markdown(
                "<div class='app-title'>Psychologist AI Agent</div>"
                "<div class='app-sub'>2030 청년을 위한 익명 정서 지원, 감정 체크, 안정화 활동 추천, 위험 신호 조기 발견 데모입니다.</div>"
            )
            chat_history_state = gr.State(initial_chat_messages())
            diary_state = gr.State({})
            summary_output = gr.JSON({}, visible=False)

            with gr.Row():
                anonymous_mode = gr.Checkbox(value=True, label="익명으로 시작하기", interactive=True)
                nickname = gr.Textbox(label="닉네임", placeholder="선택 입력", lines=1, interactive=False)
                save_consent = gr.Checkbox(value=False, label="기록 저장 동의", interactive=True)
            gr.Markdown("<div class='small-note'>익명 모드에서는 닉네임을 입력하지 않아도 상담을 시작할 수 있습니다.</div>")

            with gr.Tabs():
                with gr.TabItem("상담 채팅"):
                    chatbot = gr.Chatbot(
                        label="상담 채팅",
                        elem_classes="chatbot",
                        height=460,
                        value=initial_chat_messages(),
                    )
                    status_output = gr.Markdown("", elem_classes="status-line")

                    with gr.Row(elem_classes="input-row"):
                        message = gr.Textbox(
                            label="메시지",
                            placeholder="예: 요즘 잠을 못 자고 불안해요.",
                            lines=2,
                            scale=5,
                        )
                        submit = gr.Button("보내기", variant="primary", elem_classes="cta", scale=1)

                    with gr.Group(visible=False):
                        mood_score = gr.Slider(1, 5, value=3, step=1, label="오늘 기분")
                        anxiety_score = gr.Slider(1, 5, value=3, step=1, label="불안감")
                        loneliness_score = gr.Slider(1, 5, value=3, step=1, label="외로움")
                        sleep_quality = gr.Slider(1, 5, value=3, step=1, label="수면 상태")
                        meal_status = gr.Slider(1, 5, value=3, step=1, label="식사 상태")
                        energy_score = gr.Slider(1, 5, value=3, step=1, label="에너지")
                        stress_score = gr.Slider(1, 5, value=3, step=1, label="스트레스")

                with gr.TabItem("감정일기"):
                    diary_emotion = gr.Dropdown(
                        ["불안", "외로움", "스트레스", "무기력", "평온", "기타"],
                        value="불안",
                        label="오늘의 감정",
                    )
                    with gr.Row():
                        diary_mood = gr.Slider(1, 5, value=3, step=1, label="기분 점수")
                        diary_sleep = gr.Slider(1, 5, value=3, step=1, label="수면 점수")
                    with gr.Row():
                        diary_anxiety = gr.Slider(1, 5, value=3, step=1, label="불안 점수")
                        diary_loneliness = gr.Slider(1, 5, value=3, step=1, label="외로움 점수")
                    with gr.Row():
                        diary_meal = gr.Slider(1, 5, value=3, step=1, label="식사 상태")
                        diary_energy = gr.Slider(1, 5, value=3, step=1, label="에너지 점수")
                        diary_stress = gr.Slider(1, 5, value=3, step=1, label="스트레스 점수")
                    diary_line = gr.Textbox(
                        label="한 줄 일기",
                        placeholder="선택 입력입니다. 보고서에는 짧은 메모만 표시됩니다.",
                        lines=2,
                    )
                    diary_save = gr.Button("감정일기 저장", variant="primary")
                    diary_output = gr.Markdown("")

                with gr.TabItem("마음정리 보고서"):
                    report_output = gr.Markdown(build_service_report({}, {}))
                    report_graph_note = gr.Markdown(diary_graph_message({}))
                    report_trend_plot = gr.LinePlot(
                        value=diary_trend_dataframe({}),
                        x="기록",
                        y="마음 회복 수준",
                        color="항목",
                        title="최근 마음 회복 흐름",
                        x_title="기록",
                        y_title="마음 회복 수준",
                        y_lim=[1, 5],
                        height=460,
                    )

                with gr.TabItem("전문가 상담 연결"):
                    expert_output = gr.Markdown(
                        wrap_card(
                            "전문가 상담 연결",
                            "\n".join(
                                [
                                    "- 위기 상황: 109, 119, 112에 즉시 연락하세요.",
                                    "- 가까운 정신건강복지센터나 상담센터 이용을 권장합니다.",
                                    "- 혼자 있기 어렵다면 가까운 사람에게 지금 바로 연락하세요.",
                                    "- 이 AI는 의료 진단이나 치료를 하지 않으며 전문 상담사를 대체하지 않습니다.",
                                ]
                            ),
                            crisis=True,
                        )
                    )

            with gr.Accordion("Agent Pipeline Details", open=False):
                pipeline_output = gr.Markdown("")

            gr.Markdown(
                "<div class='small-note'>본 서비스는 전문 상담사나 의료진을 대체하지 않습니다. "
                "위기 상황에서는 즉시 109, 119, 112 또는 가까운 사람에게 도움을 요청하세요.</div>"
            )

        anonymous_mode.change(
            toggle_nickname_input,
            inputs=anonymous_mode,
            outputs=nickname,
        )

        submit.click(
            lambda: "응답을 준비하고 있어요...",
            outputs=status_output,
        ).then(
            handle_chat_ui,
            inputs=[
                message,
                chat_history_state,
                mood_score,
                anxiety_score,
                loneliness_score,
                sleep_quality,
                meal_status,
                energy_score,
                stress_score,
            ],
            outputs=[
                chatbot,
                chat_history_state,
                message,
                pipeline_output,
                summary_output,
                status_output,
            ],
        ).then(
            build_report_outputs,
            inputs=[summary_output, diary_state],
            outputs=[report_output, report_trend_plot, report_graph_note],
        )

        diary_save.click(
            save_emotion_diary,
            inputs=[
                diary_state,
                diary_emotion,
                diary_mood,
                diary_anxiety,
                diary_loneliness,
                diary_sleep,
                diary_meal,
                diary_energy,
                diary_stress,
                diary_line,
                save_consent,
            ],
            outputs=[diary_state, diary_output],
        ).then(
            build_report_outputs,
            inputs=[summary_output, diary_state],
            outputs=[report_output, report_trend_plot, report_graph_note],
        )

    return demo


def find_available_port(preferred_port: int = 7860, max_tries: int = 50) -> int:
    for port in range(preferred_port, preferred_port + max_tries):
        with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as sock:
            sock.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            if sock.connect_ex(("127.0.0.1", port)) != 0:
                return port
    return preferred_port


def main():
    """Run the demo."""
    demo = create_demo()
    launch_port = find_available_port(int(os.environ.get("GRADIO_SERVER_PORT", "7860")))
    demo.launch(
        server_name="0.0.0.0",
        server_port=launch_port,
        share=False,
    )


if __name__ == "__main__":
    main()
