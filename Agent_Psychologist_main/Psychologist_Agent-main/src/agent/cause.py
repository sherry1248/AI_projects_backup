"""Rule-based cause exploration helper for counseling-style mock responses.

The helper uses structured intent labels and dataset metadata only. It does not
store raw user turns or raw dataset text in its result.
"""

from __future__ import annotations

from dataclasses import dataclass, field
from typing import Any, Dict, List, Optional

from src.agent.models import IntentAgentResult, IntentLabel


SLEEP_MAINTENANCE_MARKERS = (
    "자주깨",
    "자주 깨",
    "깨는 편",
    "중간에 깨",
    "계속 깨",
    "새벽에 깨",
    "자다가 깨",
    "눈이 떠져",
    "자꾸 일어",
    "숙면이 안",
)

SLEEP_WAKE_THOUGHT_MARKERS = ("걱정", "생각", "불안", "떠올", "머리")
SLEEP_WAKE_NO_THOUGHT_MARKERS = ("특별한 생각 없이", "생각 없이", "이유 없이", "그냥")
SLEEP_ONSET_MARKERS = ("잠들기", "잠이 안", "잠 안", "뒤척", "오래 걸")


BASE_CAUSES: Dict[IntentLabel, List[str]] = {
    IntentLabel.SLEEP_PROBLEM: [
        "worry_or_anxiety",
        "sleep_maintenance",
        "lifestyle_rhythm",
        "physical_fatigue",
    ],
    IntentLabel.ANXIETY_SUPPORT: [
        "task_pressure",
        "relationship_stress",
        "future_uncertainty",
        "accumulated_fatigue",
    ],
    IntentLabel.LOW_MOOD_SUPPORT: [
        "exhaustion",
        "isolation",
        "low_self_evaluation",
        "repeated_failure_experience",
    ],
    IntentLabel.STRESS_SUPPORT: [
        "overload",
        "unclear_starting_point",
        "pressure_to_finish",
        "fear_of_failure",
    ],
    IntentLabel.WORK_OR_STUDY_STRESS: [
        "overload",
        "unclear_starting_point",
        "pressure_to_finish",
        "fear_of_failure",
    ],
    IntentLabel.RELATIONSHIP_STRESS: [
        "communication_gap",
        "fear_of_rejection",
        "loneliness_in_relationship",
        "boundary_pressure",
    ],
}


CAUSE_QUESTIONS = {
    "worry_or_anxiety": "잠들기 전 걱정이 많아지는 편인가요, 아니면 잠들어도 중간에 자주 깨는 편인가요?",
    "sleep_maintenance": "깨고 난 뒤 걱정이 떠올라 다시 잠들기 어려운 편인가요, 아니면 특별한 생각 없이 자주 깨는 편인가요?",
    "lifestyle_rhythm": "최근 잠드는 시간이나 화면을 보는 시간이 조금씩 밀리고 있는지도 같이 살펴볼 수 있을까요?",
    "physical_fatigue": "몸은 피곤한데 긴장이 풀리지 않는 느낌에 가까운지도 확인해볼 수 있을까요?",
    "task_pressure": "불안이 해야 할 일을 떠올릴 때 커지는 편인가요, 아니면 특별한 이유 없이 올라오는 편인가요?",
    "relationship_stress": "불안이나 긴장이 특정 사람과의 관계를 떠올릴 때 더 커지는지도 같이 살펴볼 수 있을까요?",
    "future_uncertainty": "앞으로 어떻게 될지 모른다는 생각이 불안을 키우는 쪽에 가까울까요?",
    "accumulated_fatigue": "최근 피로가 쌓이면서 불안을 견디는 힘도 같이 줄어든 느낌이 있을까요?",
    "exhaustion": "지금의 무기력은 쉬어도 회복이 잘 안 되는 소진감에 가까울까요?",
    "isolation": "혼자 감당하고 있다는 느낌이 기분을 더 가라앉히는지도 살펴볼 수 있을까요?",
    "low_self_evaluation": "스스로를 낮게 평가하는 생각이 반복되면서 기분이 더 무거워지는 편일까요?",
    "repeated_failure_experience": "최근 반복된 실망이나 실패감이 마음에 남아 있는지도 같이 볼 수 있을까요?",
    "overload": "부담이 일의 양이 많은 데서 오는지, 감당해야 한다는 압박에서 오는지 같이 좁혀볼 수 있을까요?",
    "unclear_starting_point": "어디서부터 시작해야 할지 모르는 막막함이 스트레스를 더 키우는 편인가요?",
    "pressure_to_finish": "끝내야 한다는 압박이 몸의 긴장까지 올리는 쪽에 가까울까요?",
    "fear_of_failure": "잘 못하면 어떡하지 하는 걱정이 시작을 어렵게 만드는지도 살펴볼 수 있을까요?",
    "communication_gap": "말이 잘 통하지 않는 느낌이 가장 힘든 지점인지 같이 확인해볼 수 있을까요?",
    "fear_of_rejection": "거절당하거나 멀어질까 봐 조심하게 되는 마음도 영향을 주고 있을까요?",
    "loneliness_in_relationship": "관계 안에서도 혼자 감당하는 느낌이 있는지 살펴볼 수 있을까요?",
    "boundary_pressure": "상대에게 맞추느라 내 경계가 흐려지는 느낌이 있는지도 확인해볼 수 있을까요?",
}

DEEPER_CAUSE_QUESTIONS = {
    "sleep_maintenance_thought": "깨고 난 뒤 가장 먼저 떠오르는 생각은 해야 할 일 쪽인가요, 아니면 막연한 걱정 쪽인가요?",
    "sleep_maintenance_no_thought": "특별한 생각 없이 깨는 날에는 몸의 긴장이나 불편감이 먼저 느껴지는 편인가요?",
    "worry_or_anxiety_bedtime": "잠들기 전 걱정은 오늘 있었던 일에 가까운가요, 아니면 앞으로의 일이 떠오르는 쪽에 가까운가요?",
}


@dataclass
class CauseExplorationResult:
    cause_candidates: List[str] = field(default_factory=list)
    selected_cause: str = ""
    exploration_question: str = ""
    reason_codes: List[str] = field(default_factory=list)
    dataset_signals: Dict[str, str] = field(default_factory=dict)

    def to_pipeline_dict(self) -> Dict[str, Any]:
        return {
            "cause_candidates": list(self.cause_candidates),
            "selected_cause": self.selected_cause,
            "reason_codes": list(self.reason_codes),
            "dataset_signals": dict(self.dataset_signals),
        }


def _enum_name(value: Any) -> str:
    return getattr(value, "name", str(value or "")).upper()


def _primary_intent(intent_result: Optional[IntentAgentResult]) -> IntentLabel:
    if intent_result and intent_result.primary_intent:
        return intent_result.primary_intent
    return IntentLabel.OTHER_CONCERN


def _dataset_signals(
    counseling_recommendation: Any,
    empathy_recommendation: Any,
    wellness_recommendation: Any,
) -> Dict[str, str]:
    return {
        "counseling_category": str(getattr(counseling_recommendation, "category", "") or ""),
        "empathy_emotion": str(getattr(empathy_recommendation, "emotion_label", "") or ""),
        "wellness_topic": str(getattr(wellness_recommendation, "matched_topic", "") or ""),
    }


def _sleep_followup_answer_type(user_input: str, previous_followup: str) -> str:
    if not (previous_followup or "").strip():
        return ""

    previous = previous_followup or ""
    if not any(marker in previous for marker in ("잠", "수면", "깨", "걱정")):
        return ""

    if any(marker in user_input for marker in SLEEP_MAINTENANCE_MARKERS):
        return "sleep_maintenance"
    if any(marker in user_input for marker in SLEEP_WAKE_NO_THOUGHT_MARKERS):
        return "sleep_maintenance_no_thought"
    if any(marker in user_input for marker in SLEEP_ONSET_MARKERS):
        return "worry_or_anxiety"
    if any(marker in user_input for marker in SLEEP_WAKE_THOUGHT_MARKERS):
        return "sleep_maintenance_thought"
    return ""


def _deeper_question(selected: str, answer_type: str, previous_followup: str) -> str:
    previous = (previous_followup or "").strip()
    if selected == "sleep_maintenance" and "깨고 난 뒤" in previous:
        if answer_type == "sleep_maintenance_no_thought":
            return DEEPER_CAUSE_QUESTIONS["sleep_maintenance_no_thought"]
        return DEEPER_CAUSE_QUESTIONS["sleep_maintenance_thought"]
    if selected == "worry_or_anxiety" and previous:
        return DEEPER_CAUSE_QUESTIONS["worry_or_anxiety_bedtime"]
    return ""


def _score_candidates(
    candidates: List[str],
    *,
    user_input: str,
    signals: Dict[str, str],
    previous_followup: str,
) -> tuple[str, List[str]]:
    scores = {candidate: 1 for candidate in candidates}
    reason_codes: List[str] = ["intent_candidate_set"]
    lowered = " ".join([user_input, *signals.values()]).lower()
    followup_answer_type = _sleep_followup_answer_type(user_input, previous_followup)

    if any(marker in user_input for marker in SLEEP_MAINTENANCE_MARKERS):
        scores["sleep_maintenance"] = scores.get("sleep_maintenance", 0) + 20
        reason_codes.append("followup_answer_sleep_maintenance")
    if followup_answer_type:
        reason_codes.append("previous_followup_answer_detected")
    if followup_answer_type in {"sleep_maintenance", "sleep_maintenance_thought", "sleep_maintenance_no_thought"}:
        if "sleep_maintenance" in scores:
            scores["sleep_maintenance"] += 20
        reason_codes.append("previous_followup_narrows_sleep_maintenance")
    elif followup_answer_type == "worry_or_anxiety":
        if "worry_or_anxiety" in scores:
            scores["worry_or_anxiety"] += 20
        reason_codes.append("previous_followup_narrows_worry_or_anxiety")
    if any(marker in lowered for marker in ("불안", "걱정", "anxiety", "worry")):
        for cause in ("worry_or_anxiety", "task_pressure", "future_uncertainty"):
            if cause in scores:
                scores[cause] += 3
        reason_codes.append("dataset_or_input_anxiety_signal")
    if any(marker in lowered for marker in ("sleep", "수면", "불면", "잠")):
        for cause in ("worry_or_anxiety", "lifestyle_rhythm"):
            if cause in scores:
                scores[cause] += 2
        reason_codes.append("dataset_sleep_signal")
    if any(marker in lowered for marker in ("depression", "우울", "슬픔")):
        for cause in ("exhaustion", "isolation", "low_self_evaluation"):
            if cause in scores:
                scores[cause] += 1
        reason_codes.append("dataset_low_mood_signal")
    if any(marker in lowered for marker in ("관계", "relationship", "친구", "연애")):
        for cause in ("relationship_stress", "communication_gap"):
            if cause in scores:
                scores[cause] += 2
        reason_codes.append("dataset_relationship_signal")
    if any(marker in lowered for marker in ("업무", "공부", "시험", "work", "study", "overload")):
        for cause in ("overload", "pressure_to_finish", "unclear_starting_point"):
            if cause in scores:
                scores[cause] += 2
        reason_codes.append("dataset_task_pressure_signal")

    selected = max(candidates, key=lambda cause: scores.get(cause, 0)) if candidates else ""
    return selected, reason_codes


def explore_causes(
    *,
    user_input: str,
    intent_result: Optional[IntentAgentResult],
    counseling_recommendation: Any,
    empathy_recommendation: Any,
    wellness_recommendation: Any,
    proactive_recall: Any = None,
    previous_followup: str = "",
) -> CauseExplorationResult:
    del proactive_recall
    intent = _primary_intent(intent_result)
    candidates = list(BASE_CAUSES.get(intent, []))
    if not candidates:
        return CauseExplorationResult(
            dataset_signals=_dataset_signals(
                counseling_recommendation,
                empathy_recommendation,
                wellness_recommendation,
            )
        )

    signals = _dataset_signals(
        counseling_recommendation,
        empathy_recommendation,
        wellness_recommendation,
    )
    selected, reason_codes = _score_candidates(
        candidates,
        user_input=user_input or "",
        signals=signals,
        previous_followup=previous_followup or "",
    )
    answer_type = _sleep_followup_answer_type(user_input or "", previous_followup or "")
    question = _deeper_question(selected, answer_type, previous_followup or "")
    if question:
        reason_codes.append("deeper_exploration_question_selected")
    else:
        question = CAUSE_QUESTIONS.get(selected, "")
    if question and question == (previous_followup or "").strip():
        reason_codes.append("duplicate_previous_question_omitted")
        question = ""

    return CauseExplorationResult(
        cause_candidates=candidates,
        selected_cause=selected,
        exploration_question=question,
        reason_codes=reason_codes,
        dataset_signals=signals,
    )


class CauseExplorationAgent:
    """Agent that explores underlying causes of counseling concerns,
    particularly focused on sleep problems and emotional/wellness triggers.
    """

    def __init__(self) -> None:
        pass

    def explore(
        self,
        user_input: str,
        intent_result: Any,
        counseling_rec: Any,
        empathy_rec: Any,
        wellness_rec: Any,
        proactive_recall: Any,
    ) -> Dict[str, Any]:
        # 1. Determine primary intent and initial candidates
        primary_intent = None
        if intent_result:
            if hasattr(intent_result, "primary_intent"):
                primary_intent = intent_result.primary_intent
            elif isinstance(intent_result, dict):
                primary_intent = intent_result.get("primary_intent")

        intent_str = ""
        if primary_intent is not None:
            if hasattr(primary_intent, "value"):
                intent_str = str(primary_intent.value)
            elif hasattr(primary_intent, "name"):
                intent_str = str(primary_intent.name)
            else:
                intent_str = str(primary_intent)

        is_sleep_problem = False
        if intent_str.lower() in ("sleep_problem", "intentlabel.sleep_problem"):
            is_sleep_problem = True

        candidates = []
        if is_sleep_problem:
            candidates = ["worry_or_anxiety", "sleep_maintenance", "lifestyle_rhythm", "physical_fatigue"]
        else:
            # General fallback to other BASE_CAUSES if applicable
            for key, val in BASE_CAUSES.items():
                key_name = getattr(key, "name", str(key)).lower()
                key_value = getattr(key, "value", str(key)).lower()
                if intent_str.lower() in (key_name, key_value):
                    candidates = list(val)
                    break

        # 2. Extract empathy and wellness fields
        emotion_label = ""
        if empathy_rec:
            if hasattr(empathy_rec, "emotion_label"):
                emotion_label = getattr(empathy_rec, "emotion_label") or ""
            elif isinstance(empathy_rec, dict):
                emotion_label = empathy_rec.get("emotion_label") or ""

        matched_topic = ""
        if wellness_rec:
            if hasattr(wellness_rec, "matched_topic"):
                matched_topic = getattr(wellness_rec, "matched_topic") or ""
            elif isinstance(wellness_rec, dict):
                matched_topic = wellness_rec.get("matched_topic") or ""

        # 3. Handle empathy/wellness prioritization and reason_codes
        reason_codes = []
        if emotion_label == "불안" or matched_topic == "불면":
            if "worry_or_anxiety" in candidates:
                candidates.remove("worry_or_anxiety")
                candidates.insert(0, "worry_or_anxiety")
            reason_codes.append("EMOTION_WELLNESS_MATCH")

        # 4. Check proactive recall force matching rule
        has_previous_followup = False
        if proactive_recall:
            if hasattr(proactive_recall, "previous_followup"):
                has_previous_followup = True
            elif isinstance(proactive_recall, dict) and "previous_followup" in proactive_recall:
                has_previous_followup = True

        contains_keyword = False
        if user_input:
            contains_keyword = any(word in user_input for word in ("깨", "중간에", "자주"))

        selected_cause = ""
        if has_previous_followup and contains_keyword:
            selected_cause = "sleep_maintenance"
        else:
            selected_cause = candidates[0] if candidates else ""

        # 5. Build dataset signals
        dataset_signals = {
            "counseling_category": "",
            "empathy_emotion": "",
            "wellness_topic": "",
        }
        if counseling_rec:
            if hasattr(counseling_rec, "category"):
                dataset_signals["counseling_category"] = str(getattr(counseling_rec, "category") or "")
            elif isinstance(counseling_rec, dict):
                dataset_signals["counseling_category"] = str(counseling_rec.get("category") or "")

        if empathy_rec:
            if hasattr(empathy_rec, "emotion_label"):
                dataset_signals["empathy_emotion"] = str(getattr(empathy_rec, "emotion_label") or "")
            elif isinstance(empathy_rec, dict):
                dataset_signals["empathy_emotion"] = str(empathy_rec.get("emotion_label") or "")

        if wellness_rec:
            if hasattr(wellness_rec, "matched_topic"):
                dataset_signals["wellness_topic"] = str(getattr(wellness_rec, "matched_topic") or "")
            elif isinstance(wellness_rec, dict):
                dataset_signals["wellness_topic"] = str(wellness_rec.get("matched_topic") or "")

        return {
            "cause_candidates": candidates,
            "selected_cause": selected_cause,
            "reason_codes": reason_codes,
            "dataset_signals": dataset_signals,
        }

    def __call__(
        self,
        user_input: str,
        intent_result: Any,
        counseling_rec: Any,
        empathy_rec: Any,
        wellness_rec: Any,
        proactive_recall: Any,
    ) -> Dict[str, Any]:
        return self.explore(
            user_input=user_input,
            intent_result=intent_result,
            counseling_rec=counseling_rec,
            empathy_rec=empathy_rec,
            wellness_rec=wellness_rec,
            proactive_recall=proactive_recall,
        )
