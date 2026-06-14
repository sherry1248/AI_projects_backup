"""Gradio demo for the Psychologist Agent."""

from __future__ import annotations

import html
import os
import socket
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
                "- 지금은 안전이 가장 중요해요",
                "- 109",
                "- 119",
                "- 112",
                "- 가까운 사람에게 연락",
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


def save_emotion_diary(
    emotion_label: str,
    mood_score: int,
    sleep_score: int,
    anxiety_score: int,
    loneliness_score: int,
    diary_line: str,
    save_consent: bool,
) -> Tuple[Dict[str, Any], str]:
    """Store only structured diary values for the demo report."""
    text_length = len((diary_line or "").strip())
    if text_length == 0:
        length_bucket = "empty"
    elif text_length <= 20:
        length_bucket = "short"
    elif text_length <= 60:
        length_bucket = "medium"
    else:
        length_bucket = "long"

    diary_state = {
        "emotion_label": str(emotion_label or "선택 안 함"),
        "mood_score": int(mood_score),
        "sleep_score": int(sleep_score),
        "anxiety_score": int(anxiety_score),
        "loneliness_score": int(loneliness_score),
        "has_diary_text": bool(text_length),
        "diary_length_bucket": length_bucket,
        "save_consent": bool(save_consent),
    }

    summary_lines = [
        f"- 오늘의 감정: {escape_text(diary_state['emotion_label'])}",
        f"- 기분/수면/불안/외로움: {mood_score}/{sleep_score}/{anxiety_score}/{loneliness_score}",
        f"- 한 줄 일기: {'입력됨' if text_length else '미입력'}",
        "- 일기 원문은 저장하지 않고 구조화 값만 보고서에 반영합니다.",
    ]
    if not save_consent:
        summary_lines.append("- 기록 저장 동의가 꺼져 있어 데모 화면 안에서만 임시 반영됩니다.")

    return diary_state, wrap_card("감정일기 저장 요약", "\n".join(summary_lines))


def build_service_report(
    summary: Optional[Dict[str, Any]],
    diary_state: Optional[Dict[str, Any]],
) -> str:
    """Build a user-facing structured report without raw text."""
    summary = summary or {}
    diary_state = diary_state or {}
    result = last_agent_result or {}
    agents = _agent_details(result)
    intent = _as_dict(agents.get("intent"))
    state = _as_dict(agents.get("emotional_state"))
    decision = _as_dict(agents.get("decision"))
    followup = _as_dict(agents.get("followup"))
    small_action = _as_dict(agents.get("small_action"))

    risk_stage = summary.get("risk_stage") or result.get("risk_stage") or "관심"
    intent_labels = _extract_labels(intent)
    state_summary = _safe_list(state.get("state_summary"))
    primary_intent = intent.get("primary_intent")
    primary_action = decision.get("primary_action") or decision.get("action")
    action_text = small_action.get("action_text") if isinstance(small_action.get("action_text"), str) else ""
    followup_question = followup.get("question") if isinstance(followup.get("question"), str) else ""

    concern_keywords = []
    if isinstance(primary_intent, str) and primary_intent:
        concern_keywords.append(primary_intent)
    concern_keywords.extend(intent_labels)
    concern_keywords = _safe_list(concern_keywords, max_items=4)

    diary_lines = []
    if diary_state:
        diary_lines = [
            _safe_key_value("emotion_label", diary_state.get("emotion_label")),
            _safe_key_value("mood_score", diary_state.get("mood_score")),
            _safe_key_value("sleep_score", diary_state.get("sleep_score")),
            _safe_key_value("anxiety_score", diary_state.get("anxiety_score")),
            _safe_key_value("loneliness_score", diary_state.get("loneliness_score")),
            _safe_key_value("has_diary_text", diary_state.get("has_diary_text")),
        ]

    report_lines = [
        f"- 주요 감정: {', '.join(state_summary) if state_summary else escape_text(str(diary_state.get('emotion_label', '아직 없음')))}",
        f"- 주요 고민 키워드: {', '.join(concern_keywords) if concern_keywords else '아직 없음'}",
        f"- 위험 단계: {escape_text(risk_stage)}",
        f"- 추천 안정화 활동: {escape_text(action_text) if action_text and len(action_text) <= 120 else '상담 채팅 후 표시됩니다.'}",
        f"- 다음 follow-up 질문: {escape_text(followup_question) if followup_question and len(followup_question) <= 120 else '상담 채팅 후 표시됩니다.'}",
        f"- 전문가 상담 안내: {'긴급 연락 또는 상담센터 연결을 우선 권장합니다.' if risk_stage in {'주의', '위험'} else '필요하면 상담센터 이용을 함께 검토할 수 있습니다.'}",
    ]

    sections = [wrap_card("마음정리 보고서", "\n".join(report_lines))]
    if diary_lines:
        sections.append(wrap_card("감정 체크 요약", "\n".join(f"- {line}" for line in diary_lines if line)))
    return "\n\n".join(sections)


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
                "위기 신호가 감지되어 즉시 안전 안내를 우선했습니다.",
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
) -> Tuple[List[ChatMessage], str, str, Dict[str, Any], str]:
    """Handle one chat turn for the user-facing Gradio chat UI."""
    history = normalize_chat_history(chat_history)
    message_text = (message or "").strip()
    if not message_text:
        return history, "", "", {"empty_message": True}, ""

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
    return history, "", pipeline_markdown, summary, "응답이 준비됐어요."


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
    .chatbot { border-radius:12px; min-height:460px; }
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
            chat_state = gr.State([])
            diary_state = gr.State({})
            summary_output = gr.JSON({}, visible=False)

            with gr.Row():
                anonymous_mode = gr.Checkbox(value=True, label="익명으로 시작하기")
                save_consent = gr.Checkbox(value=False, label="기록 저장 동의")
            gr.Markdown(
                wrap_card(
                    "AI 첫 인사",
                    "안녕하세요. 이름을 말하지 않아도 괜찮아요. 지금 마음에 남아 있는 일을 한 문장부터 편하게 적어주세요.",
                )
            )

            with gr.Tabs():
                with gr.TabItem("상담 채팅"):
                    chatbot = gr.Chatbot(
                        label="상담 채팅",
                        elem_classes="chatbot",
                        height=460,
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

                    with gr.Row():
                        def example_text(t: str):
                            return t

                        ex_normal = gr.Button("외로움 예시", elem_classes="example-button")
                        ex_anxiety = gr.Button("불안 예시", elem_classes="example-button")
                        ex_risk = gr.Button("위험 예시", elem_classes="example-button")

                        ex_normal.click(lambda: example_text("요즘 너무 외롭고 잠을 잘 못 자요."), outputs=message)
                        ex_anxiety.click(lambda: example_text("사람 만나는 게 부담스럽고 계속 불안해요."), outputs=message)
                        ex_risk.click(lambda: example_text("죽고 싶어요."), outputs=message)

                    with gr.Accordion("상태 체크", open=False):
                        gr.Markdown("선택 입력입니다. 잘 모르겠으면 보통으로 두어도 괜찮아요.")
                        with gr.Row():
                            mood_score = gr.Slider(1, 5, value=3, step=1, label="오늘 기분")
                            anxiety_score = gr.Slider(1, 5, value=3, step=1, label="불안감")
                        with gr.Row():
                            loneliness_score = gr.Slider(1, 5, value=3, step=1, label="외로움")
                            sleep_quality = gr.Slider(1, 5, value=3, step=1, label="수면 상태")
                        with gr.Row():
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
                    diary_line = gr.Textbox(
                        label="한 줄 일기",
                        placeholder="원문은 저장하지 않고 입력 여부와 구조화 값만 반영합니다.",
                        lines=2,
                    )
                    diary_save = gr.Button("감정일기 저장", variant="primary")
                    diary_output = gr.Markdown("")

                with gr.TabItem("마음정리 보고서"):
                    report_output = gr.Markdown(build_service_report({}, {}))

                with gr.TabItem("전문가 상담 연결"):
                    gr.Markdown(
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

        submit.click(
            lambda: "응답을 준비하고 있어요...",
            outputs=status_output,
        ).then(
            handle_chat_ui,
            inputs=[
                message,
                chat_state,
                mood_score,
                anxiety_score,
                loneliness_score,
                sleep_quality,
                meal_status,
                energy_score,
                stress_score,
            ],
            outputs=[chatbot, message, pipeline_output, summary_output, status_output],
        ).then(
            build_service_report,
            inputs=[summary_output, diary_state],
            outputs=report_output,
        ).then(
            lambda history: history,
            inputs=chatbot,
            outputs=chat_state,
        )

        diary_save.click(
            save_emotion_diary,
            inputs=[
                diary_emotion,
                diary_mood,
                diary_sleep,
                diary_anxiety,
                diary_loneliness,
                diary_line,
                save_consent,
            ],
            outputs=[diary_state, diary_output],
        ).then(
            build_service_report,
            inputs=[summary_output, diary_state],
            outputs=report_output,
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
