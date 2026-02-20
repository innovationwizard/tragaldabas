"""Narrative analysis stage: narrative metrics and insight qualification for meetings/notes."""

import uuid
from typing import Dict, Any

from core.interfaces import Stage
from core.models import (
    NarrativeExtraction,
    AnalysisResult,
    Insight,
    NarrativeEvidence,
)
from core.enums import Domain, Severity, VisualizationType, NarrativeContentType
from core.exceptions import StageError
from llm.client import LLMClient
from llm.prompts import NarrativeInsightsPrompt
from config import settings


def _compute_narrative_metrics(extraction: NarrativeExtraction) -> list[str]:
    """Compute narrative metrics from extraction."""
    metrics = []
    n_decisions = len(extraction.decisions)
    n_actions = len(extraction.action_items)
    n_questions = len(extraction.open_questions)
    n_ideas = len(extraction.ideas)
    n_tensions = len(extraction.tensions)

    # Decision density (placeholder: per-doc, not per-minute without duration)
    if n_decisions > 0:
        metrics.append(f"decisions_count={n_decisions}")

    # Action item completion risk: items without owners or deadlines
    unowned = sum(1 for a in extraction.action_items if not (a.owner or "").strip())
    undeadlined = sum(1 for a in extraction.action_items if not (a.deadline or "").strip())
    if n_actions > 0:
        metrics.append(f"action_items={n_actions}")
        if unowned > 0:
            metrics.append(f"unowned_action_items={unowned}")
        if undeadlined > 0:
            metrics.append(f"action_items_without_deadline={undeadlined}")

    # Topic coherence (simplified: number of distinct topics)
    if extraction.topics:
        metrics.append(f"topics_count={len(extraction.topics)}")

    # Unresolved ratio
    if n_questions > 0:
        metrics.append(f"open_questions={n_questions}")

    if n_ideas > 0:
        metrics.append(f"ideas_count={n_ideas}")
    if n_tensions > 0:
        metrics.append(f"tensions_count={n_tensions}")

    return metrics


def _build_preliminary_insights(extraction: NarrativeExtraction) -> list[dict]:
    """Build preliminary insights from extraction for qualification prompt."""
    insights = []

    # Unowned action items
    for a in extraction.action_items:
        if not (a.owner or "").strip():
            insights.append({
                "headline": f"Unowned action: {a.task[:50]}...",
                "detail": f"Task '{a.task}' has no assigned owner.",
                "evidence": {
                    "source_type": "absence",
                    "reference": a.task,
                    "speaker": None,
                    "timestamp": None,
                    "context": "Action item without owner",
                },
                "implication": "Risk of task falling through the cracks.",
                "severity": "warning",
                "included": True,
            })

    # Action items without deadline
    for a in extraction.action_items:
        if not (a.deadline or "").strip() and (a.owner or "").strip():
            insights.append({
                "headline": f"No deadline: {a.task[:50]}...",
                "detail": f"Task assigned to {a.owner} has no deadline.",
                "evidence": {
                    "source_type": "absence",
                    "reference": a.task,
                    "speaker": a.owner,
                    "timestamp": None,
                    "context": "Action item without deadline",
                },
                "implication": "May be deprioritized indefinitely.",
                "severity": "info",
                "included": True,
            })

    # Open questions
    for q in extraction.open_questions[:5]:  # Limit
        insights.append({
            "headline": f"Open question: {q.question[:50]}...",
            "detail": q.question,
            "evidence": {
                "source_type": "quote",
                "reference": q.question,
                "speaker": q.raised_by,
                "timestamp": None,
                "context": q.context or "",
            },
            "implication": "Unresolved item may block progress.",
            "severity": "info",
            "included": True,
        })

    # Tensions
    for t in extraction.tensions[:3]:
        insights.append({
            "headline": f"Tension: {t.opposing_views[:50]}...",
            "detail": t.opposing_views,
            "evidence": {
                "source_type": "pattern",
                "reference": t.opposing_views,
                "speaker": None,
                "timestamp": None,
                "context": f"Resolution: {t.resolution_status}",
            },
            "implication": "May need facilitation to resolve.",
            "severity": "warning" if t.resolution_status.lower() != "resolved" else "info",
            "included": True,
        })

    # High-novelty ideas with no follow-up (simplified)
    for idea in extraction.ideas[:3]:
        if (idea.novelty or "").lower() in ("high", "novel", "innovative"):
            insights.append({
                "headline": f"High-novelty idea: {idea.concept[:50]}...",
                "detail": idea.concept,
                "evidence": {
                    "source_type": "quote",
                    "reference": idea.concept,
                    "speaker": idea.proposer,
                    "timestamp": None,
                    "context": f"Feasibility: {idea.feasibility}",
                },
                "implication": "Consider explicit follow-up or ownership.",
                "severity": "info",
                "included": True,
            })

    return insights[: settings.MAX_INSIGHTS_PER_ANALYSIS * 2]  # Over-fetch for filtering


class NarrativeAnalyzer(Stage[Dict[str, Any], AnalysisResult]):
    """Analyze narrative extraction and produce insights with NarrativeEvidence."""

    @property
    def name(self) -> str:
        return "Narrative Analysis"

    @property
    def stage_number(self) -> int:
        return 6

    def __init__(self):
        self.llm = LLMClient()
        self.insights_prompt = NarrativeInsightsPrompt()

    def validate_input(self, input_data: Dict[str, Any]) -> bool:
        return (
            isinstance(input_data, dict)
            and "narrative_extraction" in input_data
            and "classification" in input_data
        )

    async def execute(self, input_data: Dict[str, Any]) -> AnalysisResult:
        extraction: NarrativeExtraction = input_data["narrative_extraction"]
        classification = input_data["classification"]
        domain = getattr(classification, "domain", None) or Domain.GENERAL

        metrics = _compute_narrative_metrics(extraction)
        preliminary = _build_preliminary_insights(extraction)

        if not preliminary:
            return AnalysisResult(
                domain=domain,
                narrative_metrics=metrics,
                insights=[],
            )

        # Qualify insights via LLM
        context = {
            "content_type": extraction.content_type.value,
            "metrics": metrics,
            "insights": preliminary,
        }
        prompt = self.insights_prompt.build_prompt(context)
        response = await self.llm.complete(
            prompt,
            system="You qualify narrative insights. Respond only with valid JSON.",
            max_tokens=2048,
            temperature=0.2,
        )
        result = self.insights_prompt.parse_response(response)

        insights = []
        for item in result.get("qualified_insights", [])[: settings.MAX_INSIGHTS_PER_ANALYSIS]:
            if not item.get("included", True):
                continue
            ev = item.get("evidence", {})
            evidence = NarrativeEvidence(
                source_type=ev.get("source_type", "quote"),
                reference=ev.get("reference", ""),
                speaker=ev.get("speaker"),
                timestamp=ev.get("timestamp"),
                context=ev.get("context", ""),
            )
            insight = Insight(
                id=str(uuid.uuid4()),
                headline=item.get("headline", ""),
                detail=item.get("detail", ""),
                evidence=evidence,
                implication=item.get("implication", ""),
                severity=Severity(item.get("severity", "info")),
                visualization_hint=VisualizationType(
                    item.get("visualization_hint", "metric_callout")
                ),
                included=item.get("included", True),
            )
            insights.append(insight)

        return AnalysisResult(
            domain=domain,
            narrative_metrics=metrics,
            patterns_detected=[],
            insights=insights,
        )
