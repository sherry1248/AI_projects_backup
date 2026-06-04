"""
Prompt Generator for cloud and local model inference.

This module provides the PromptGenerator class that creates prompts
for both the cloud analysis (Deepseek-V3) and local generation (GGUF) stages.
"""

import os
import json
from typing import Optional, List, Dict, Any, Union
from dataclasses import dataclass, field

from src.prompt.templates import TemplateLoader, PromptTemplate, DEFAULT_TEMPLATES
from src.utils.logging_config import setup_logging

logger = setup_logging("prompt_generator")


@dataclass
class CloudPrompt:
    """Prompt for cloud (Deepseek-V3) analysis."""
    system_message: str
    user_message: str
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_messages(self) -> List[Dict[str, str]]:
        """Convert to message format for API."""
        return [
            {"role": "system", "content": self.system_message},
            {"role": "user", "content": self.user_message}
        ]


@dataclass
class LocalPrompt:
    """Prompt for local (GGUF) generation."""
    system_message: str
    user_message: str
    full_prompt: str  # Formatted for single-prompt models
    messages: List[Dict[str, str]] = field(default_factory=list)
    metadata: Dict[str, Any] = field(default_factory=dict)

    def to_messages(self) -> List[Dict[str, str]]:
        """Convert to messages list for chat completion API."""
        if self.messages:
            return self.messages
        return [
            {"role": "system", "content": self.system_message},
            {"role": "user", "content": self.user_message}
        ]


@dataclass
class PromptConfig:
    """Configuration for prompt generation."""
    max_history_turns: int = 5
    max_rag_context_length: int = 1500
    include_timestamps: bool = False
    therapeutic_approach: str = "integrative"


class PromptGenerator:
    """
    Generator for cloud and local model prompts.

    Creates structured prompts for the two-stage inference pipeline:
    1. Cloud prompt for Deepseek-V3 analysis
    2. Local prompt for GGUF response generation

    Example:
        generator = PromptGenerator()
        cloud_prompt = generator.gen_cloud_prompt(
            sanitized_input="I'm feeling anxious",
            rag_context="CBT techniques for anxiety...",
            history=[{"role": "user", "content": "Hi"}]
        )
    """

    def __init__(
        self,
        config: Optional[PromptConfig] = None,
        template_path: Optional[str] = None
    ):
        """
        Initialize prompt generator.

        Args:
            config: Prompt generation configuration
            template_path: Path to custom template file
        """
        self.config = config or PromptConfig()
        self.template_loader = TemplateLoader(template_path)
        self._templates = self.template_loader.load()

        logger.info("PromptGenerator initialized")

    def gen_cloud_prompt(
        self,
        sanitized_input: str,
        rag_context: str = "",
        history: Optional[List[Dict[str, str]]] = None,
        user_profile: Optional[Dict[str, Any]] = None,
        additional_context: Optional[Dict[str, Any]] = None
    ) -> CloudPrompt:
        """
        Generate prompt for cloud (Deepseek-V3) analysis.

        Args:
            sanitized_input: User input after PII redaction
            rag_context: Retrieved knowledge context
            history: Conversation history (10 turns for cloud)
            user_profile: Long-term user profile for clinical context
            additional_context: Additional context variables

        Returns:
            CloudPrompt ready for API call
        """
        template = self._templates.get("cloud_analysis", DEFAULT_TEMPLATES["cloud_analysis"])

        # Format conversation history
        history_str = self._format_history(history or [], max_turns=10)

        # Truncate RAG context if needed
        rag_context = self._truncate_context(rag_context, self.config.max_rag_context_length)

        # Format user profile
        profile_str = json.dumps(user_profile, indent=2) if user_profile else "{}"

        rendered = template.format(
            user_input=sanitized_input,
            conversation_history=history_str or "(No prior conversation)",
            rag_context=rag_context or "(No additional context)",
            user_profile=profile_str,
            safety_notice=(
                "이 AI는 의료 진단이나 치료를 하지 않으며, 전문 상담사를 대체하지 않습니다. "
                "위험 신호가 있으면 109, 119, 112 또는 가까운 응급실 연결을 우선 안내하세요."
            ),
            output_schema=(
                '{"risk_stage":"관심|주의|위험","risk_level":"low|moderate|high|critical",'
                '"primary_concern":"...","risk_reasoning":"...",'
                '"guidance_for_local_model":"...","suggested_technique":"...",'
                '"updated_user_profile":{}}'
            )
        )

        system_message = rendered["system"]
        user_message = rendered["user"]

        return CloudPrompt(
            system_message=system_message,
            user_message=user_message,
            metadata={
                "template": "cloud_analysis_supervisor",
                "input_length": len(sanitized_input),
                "history_turns": len(history or []) // 2,
                "has_rag_context": bool(rag_context),
                "has_user_profile": bool(user_profile)
            }
        )

    def gen_local_prompt(
        self,
        user_input: str,
        cloud_analysis: Union[str, Dict[str, Any]],
        rag_context: str = "",
        history: Optional[List[Dict[str, str]]] = None,
        therapeutic_guidance: str = "",
        additional_context: Optional[Dict[str, Any]] = None
    ) -> LocalPrompt:
        """
        Generate prompt for local (GGUF) response generation.

        Args:
            user_input: Original user input
            cloud_analysis: Analysis from cloud API (Dict or string)
            rag_context: Retrieved knowledge context
            history: Conversation history (3 turns for local)
            therapeutic_guidance: Additional therapeutic guidance
            additional_context: Additional context variables

        Returns:
            LocalPrompt ready for local inference
        """
        template = self._templates.get("local_generation", DEFAULT_TEMPLATES["local_generation"])

        # Handle both Dict and string formats
        if isinstance(cloud_analysis, dict):
            analysis_dict = cloud_analysis
        else:
            # Legacy string format
            analysis_dict = {
                "primary_concern": "",
                "suggested_technique": therapeutic_guidance or self._get_default_guidance(),
                "guidance_for_local_model": cloud_analysis
            }

        # Format conversation history (3 turns only for local)
        history_str = self._format_history(history or [], max_turns=3)

        # Truncate RAG context if needed
        rag_context = self._truncate_context(rag_context, self.config.max_rag_context_length)

        rendered = template.format(
            user_input=user_input,
            cloud_analysis=json.dumps(analysis_dict, ensure_ascii=False, indent=2),
            rag_context=rag_context or "(No additional context)",
            conversation_history=history_str or "(No prior conversation)",
            therapeutic_guidance=analysis_dict.get("guidance_for_local_model") or self._get_default_guidance(),
            safety_notice=(
                "이 응답은 의료 진단이나 치료가 아니며, 사용자 감정 정리와 안전 안내를 우선한다."
            ),
            expert_referral=(
                "위험 신호가 있으면 109, 119, 112 또는 가까운 응급실/지역 정신건강복지센터 연결을 제안한다."
            )
        )

        system_content = rendered["system"]
        user_content = rendered["user"]

        # Build messages list for chat completion API
        messages = [
            {"role": "system", "content": system_content},
            {"role": "user", "content": user_content}
        ]

        # Create full prompt for single-prompt models (backwards compatibility)
        full_prompt = self._build_full_prompt(system_content, user_content)

        return LocalPrompt(
            system_message=system_content,
            user_message=user_content,
            full_prompt=full_prompt,
            messages=messages,
            metadata={
                "template": "local_generation_agent",
                "input_length": len(user_input),
                "analysis_length": len(str(cloud_analysis)),
                "history_turns": len(history or []) // 2
            }
        )

    def gen_crisis_prompt(
        self,
        user_input: str,
        risk_level: str,
        matched_pattern: str = "",
        additional_context: Optional[Dict[str, Any]] = None
    ) -> LocalPrompt:
        """
        Generate prompt for crisis response.

        Args:
            user_input: User's crisis message
            risk_level: Detected risk level
            matched_pattern: Pattern that triggered crisis detection
            additional_context: Additional context

        Returns:
            LocalPrompt for crisis response
        """
        template = self._templates.get("crisis_response", DEFAULT_TEMPLATES["crisis_response"])

        rendered = template.format(
            user_input=user_input,
            risk_level=risk_level,
            matched_pattern=matched_pattern or "(General crisis indicators)",
            emergency_numbers="109, 119, 112",
            safety_notice=(
                "이 AI는 의료 진단이나 치료를 하지 않으며, 즉시 안전 확보와 전문기관 연결을 우선한다."
            ),
            **(additional_context or {})
        )

        system_message = rendered["system"]
        user_message = rendered["user"]

        full_prompt = self._build_full_prompt(system_message, user_message)

        return LocalPrompt(
            system_message=system_message,
            user_message=user_message,
            full_prompt=full_prompt,
            metadata={
                "template": "crisis_response",
                "risk_level": risk_level
            }
        )

    def _format_history(
        self,
        history: List[Dict[str, str]],
        max_turns: Optional[int] = None
    ) -> str:
        """Format conversation history as string."""
        if not history:
            return ""

        max_turns = max_turns or self.config.max_history_turns
        # Take last N messages (each turn is 2 messages)
        recent = history[-(max_turns * 2):]

        parts = []
        for msg in recent:
            role = "User" if msg.get("role") == "user" else "Assistant"
            content = msg.get("content", "")
            parts.append(f"{role}: {content}")

        return "\n".join(parts)

    def _truncate_context(self, context: str, max_length: int) -> str:
        """Truncate context to maximum length."""
        if len(context) <= max_length:
            return context
        return context[:max_length] + "..."

    def _build_full_prompt(self, system: str, user: str) -> str:
        """Build full prompt for single-prompt models (llama-cpp-python)."""
        return f"""<|system|>
{system}
<|user|>
{user}
<|assistant|>
"""

    def _get_default_guidance(self) -> str:
        """Get default therapeutic guidance based on config."""
        guidance_map = {
            "cbt": "Focus on cognitive restructuring and behavioral activation.",
            "dbt": "Emphasize distress tolerance and emotional regulation skills.",
            "supportive": "Provide validation, empathy, and emotional support.",
            "integrative": "Combine elements from various therapeutic approaches as appropriate."
        }
        return guidance_map.get(
            self.config.therapeutic_approach,
            guidance_map["integrative"]
        )

    def get_available_templates(self) -> List[str]:
        """Get list of available template names."""
        return list(self._templates.keys())
