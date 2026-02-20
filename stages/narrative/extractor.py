"""Narrative extraction stage: structured extraction from meetings, notes, unstructured content."""

from typing import Dict, Any

from core.interfaces import Stage
from core.models import (
    ReceptionResult,
    ContentClassification,
    NarrativeExtraction,
    Topic,
    Decision,
    ActionItem,
    Statement,
    Question,
    Idea,
    Tension,
    SentimentPoint,
)
from core.enums import NarrativeContentType
from core.exceptions import StageError
from llm.client import LLMClient
from llm.prompts import NarrativeExtractionPrompt


class NarrativeExtractor(Stage[Dict[str, Any], NarrativeExtraction]):
    """Extract structured NarrativeExtraction from narrative content via LLM."""

    @property
    def name(self) -> str:
        return "Narrative Extraction"

    @property
    def stage_number(self) -> int:
        return 5  # Replaces ETL for narrative path

    def __init__(self):
        self.llm = LLMClient()
        self.prompt_builder = NarrativeExtractionPrompt()

    def validate_input(self, input_data: Dict[str, Any]) -> bool:
        return (
            isinstance(input_data, dict)
            and "reception" in input_data
            and "classification" in input_data
        )

    def _get_raw_content(self, reception: ReceptionResult) -> str:
        """Get raw text from reception (Transcript for audio, Document for docs)."""
        raw = reception.raw_data or {}
        content = raw.get("Transcript") or raw.get("Document") or ""
        if isinstance(content, str):
            return content
        return str(content)

    def _parse_list(self, data: list, model_class, **defaults) -> list:
        """Parse list of dicts into Pydantic models."""
        result = []
        for item in (data or []):
            if not isinstance(item, dict):
                continue
            try:
                result.append(model_class(**{**defaults, **item}))
            except Exception:
                pass
        return result

    async def execute(self, input_data: Dict[str, Any]) -> NarrativeExtraction:
        reception: ReceptionResult = input_data["reception"]
        classification: ContentClassification = input_data["classification"]

        content = self._get_raw_content(reception)
        if not content.strip():
            raise StageError(
                self.stage_number,
                "No content to extract. Reception raw_data must contain 'Transcript' or 'Document'.",
            )

        content_type = (
            classification.narrative_content_type or NarrativeContentType.GENERAL
        ).value

        prompt = self.prompt_builder.build_prompt(
            {"content_type": content_type, "content": content}
        )
        response = await self.llm.complete(
            prompt,
            system="You extract structured information from narrative content. Respond only with valid JSON.",
            max_tokens=4096,
            temperature=0.2,
        )
        result = self.prompt_builder.parse_response(response)

        # Build NarrativeExtraction from parsed JSON
        topics = self._parse_list(
            result.get("topics", []), Topic,
            theme="", summary="", relevance_score=0.0
        )
        decisions = self._parse_list(
            result.get("decisions", []), Decision,
            what="", who_decided=None, context="", timestamp=None
        )
        action_items = self._parse_list(
            result.get("action_items", []), ActionItem,
            task="", owner=None, deadline=None, priority="", status=""
        )
        key_statements = self._parse_list(
            result.get("key_statements", []), Statement,
            quote="", speaker=None, significance="", sentiment=""
        )
        open_questions = self._parse_list(
            result.get("open_questions", []), Question,
            question="", raised_by=None, context=""
        )
        ideas = self._parse_list(
            result.get("ideas", []), Idea,
            concept="", proposer=None, feasibility="", novelty=""
        )
        tensions = self._parse_list(
            result.get("tensions", []), Tension,
            opposing_views="", parties="", resolution_status=""
        )
        sentiment_arc = self._parse_list(
            result.get("sentiment_arc", []), SentimentPoint,
            timestamp_or_section="", sentiment="", trigger=""
        )

        return NarrativeExtraction(
            content_type=NarrativeContentType(result.get("content_type", "general")),
            topics=topics,
            decisions=decisions,
            action_items=action_items,
            key_statements=key_statements,
            open_questions=open_questions,
            ideas=ideas,
            tensions=tensions,
            sentiment_arc=sentiment_arc,
            raw_transcript=content[:50000],  # Keep full text for reference
        )
