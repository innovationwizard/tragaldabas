"""Alpha Strike Engine: Synthetic Board of Directors Red Team analysis.

Runs a single high-compute Chain-of-Thought prompt with three personas:
- Numeric path: Forensic Accountant, Contrarian Investor, Industry Oracle
- Narrative path: Pattern Analyst, Devil's Advocate, Industry Oracle
"""

import json
from pathlib import Path
from typing import Optional

import pandas as pd

from core.models import AnalysisResult, GeniusInsight, ETLResult, NarrativeExtraction
from core.enums import Domain
from llm.client import LLMClient
from config import settings


# Map domain to industry for market trend search
DOMAIN_TO_INDUSTRY = {
    Domain.FINANCIAL: "financial services",
    Domain.OPERATIONAL: "operations manufacturing",
    Domain.SALES: "sales retail",
    Domain.HR: "human resources workforce",
    Domain.INVENTORY: "inventory supply chain",
    Domain.GENERAL: "business",
}


def _fetch_market_trends(industry: str) -> str:
    """Fetch 2026 industry tailwinds via web search. Graceful fallback if unavailable."""
    try:
        from duckduckgo_search import DDGS

        query = f"2026 {industry} industry trends tailwinds"
        results = list(DDGS().text(query, max_results=5))
        if not results:
            return "Market trend data unavailable. Proceed with domain expertise."
        snippets = [r.get("body", "")[:300] for r in results if r.get("body")]
        return "\n".join(snippets[:3]) if snippets else "Market trend data unavailable."
    except ImportError:
        return "Web search unavailable (duckduckgo-search not installed). Proceed with domain expertise."
    except Exception:
        return "Market trend fetch failed. Proceed with domain expertise."


def _build_genius_prompt_numeric(
    data_summary: str,
    domain: str,
    metrics_computed: list[str],
    patterns_detected: list[str],
    insights_summary: str,
    market_trends: str,
) -> str:
    """Chain-of-Thought prompt for numeric/tabular data."""
    return f"""You are a Synthetic Board of Directors performing a Red Team analysis. Your job is to triangulate ONE standout strategic insight—"The Genius Move"—by adopting three distinct personas in sequence.

## CONTEXT
- Domain: {domain}
- Data summary (describe, columns, stats): {data_summary[:4000]}
- Metrics computed: {metrics_computed}
- Patterns detected: {patterns_detected}
- Standard insights (for context, do not repeat): {insights_summary[:1500]}

## MARKET CONFLUENCE (2026 trends)
{market_trends}

## PERSONA SEQUENCE (Chain of Thought)

### 1. The Forensic Accountant
Adopt this persona first. Scan the data for "Leaking Cash"—inefficiencies, waste, misallocated spend, or hidden costs the user likely hasn't noticed. What is the single biggest leak?

### 2. The Contrarian Investor
Now adopt this persona. Find "Unpriced Alpha"—an underutilized asset, segment, or capability with 10x potential that the market (or the user) is ignoring. What is the one structural anomaly?

### 3. The Industry Oracle
Finally, connect the Excel data to real-time 2026 market trends above. Why does this opportunity matter RIGHT NOW? What tailwind or headwind makes timing critical?

## SYNTHESIS
Combine the three perspectives into ONE bold "Genius Move." Think Warren Buffett meets Nassim Taleb: ignore minor variances, find the structural anomaly that could drive 20%+ EBITDA improvement.

## OUTPUT FORMAT
Respond with valid JSON only. No markdown, no explanation.

{{
    "thesis": "<Bold, contrarian statement about where the money is. One sentence.>",
    "mechanism": "<Step 1: ... Step 2: ... Step 3: ... Exactly how to extract the value.>",
    "market_confluence": "<Why this matters right now based on 2026 market trends.>",
    "estimated_upside": "<Dollar amount or % margin expansion. Be specific even if speculative.>",
    "kill_switch": "<The one thing that could make this strategy fail. Adds credibility.>"
}}
"""


def _build_genius_prompt_narrative(
    extraction_summary: str,
    domain: str,
    narrative_metrics: list[str],
    insights_summary: str,
    market_trends: str,
) -> str:
    """Chain-of-Thought prompt for narrative content (meetings, notes). Adapted personas."""
    return f"""You are a Synthetic Board of Directors performing a Red Team analysis on meeting/notes content. Triangulate ONE standout strategic insight—"The Genius Move"—by adopting three distinct personas in sequence.

## CONTEXT
- Domain: {domain}
- Extracted content summary: {extraction_summary[:4000]}
- Narrative metrics: {narrative_metrics}
- Standard insights (for context, do not repeat): {insights_summary[:1500]}

## MARKET CONFLUENCE (2026 trends)
{market_trends}

## PERSONA SEQUENCE (Chain of Thought)

### 1. The Pattern Analyst (replaces Forensic Accountant)
Adopt this persona first. Find contradictions between what was said and what was decided. Identify commitments that conflict with prior commitments. Where are the gaps between rhetoric and action?

### 2. The Devil's Advocate (replaces Contrarian Investor)
Now adopt this persona. Challenge the strongest ideas from the discussion. Identify groupthink. What alternative view is being suppressed or overlooked?

### 3. The Industry Oracle
Finally, connect the meeting/notes content to real-time 2026 market trends above. Why do these decisions or ideas matter RIGHT NOW?

## SYNTHESIS
Combine the three perspectives into ONE bold "Genius Move" relevant to this narrative content.

## OUTPUT FORMAT
Respond with valid JSON only. No markdown, no explanation.

{{
    "thesis": "<Bold, contrarian statement. One sentence.>",
    "mechanism": "<Step 1: ... Step 2: ... Step 3: ... How to act on this.>",
    "market_confluence": "<Why this matters right now based on 2026 market trends.>",
    "estimated_upside": "<Dollar amount or % margin expansion. Be specific even if speculative.>",
    "kill_switch": "<The one thing that could make this strategy fail.>"
}}
"""


def _build_genius_prompt(
    data_summary: str,
    domain: str,
    metrics_computed: list[str],
    patterns_detected: list[str],
    insights_summary: str,
    market_trends: str,
    narrative: bool = False,
    narrative_metrics: list[str] | None = None,
) -> str:
    """Dispatch to numeric or narrative prompt."""
    if narrative and narrative_metrics is not None:
        return _build_genius_prompt_narrative(
            data_summary, domain, narrative_metrics, insights_summary, market_trends
        )
    return _build_genius_prompt_numeric(
        data_summary, domain, metrics_computed, patterns_detected, insights_summary, market_trends
    )


def _parse_genius_response(response: str) -> Optional[dict]:
    """Parse LLM response into GeniusInsight dict. Tolerant of markdown/code blocks."""
    text = response.strip()
    if "```" in text:
        parts = text.split("```")
        for p in parts:
            p = p.strip()
            if p.startswith("json"):
                p = p[4:].strip()
            if p.startswith("{"):
                try:
                    return json.loads(p)
                except json.JSONDecodeError:
                    continue
    try:
        start = text.find("{")
        if start >= 0:
            return json.loads(text[start:])
    except json.JSONDecodeError:
        pass
    return None


class AlphaStrikeEngine:
    """Runs the Strategic Alpha / Genius Move prompt after standard analysis."""

    def __init__(self):
        self.llm = LLMClient()

    async def run(
        self,
        analysis: AnalysisResult,
        etl: Optional[ETLResult] = None,
        narrative_extraction: Optional[NarrativeExtraction] = None,
        domain: Domain = None,
    ) -> AnalysisResult:
        """
        Enrich AnalysisResult with a single GeniusInsight. Does not modify existing insights.
        Supports both numeric (etl) and narrative (narrative_extraction) paths.
        """
        if not settings.ALPHA_STRIKE_ENABLED:
            return analysis

        domain = domain or Domain.GENERAL
        data_summary = ""
        narrative = narrative_extraction is not None

        if narrative and narrative_extraction:
            # Build summary from narrative extraction
            parts = []
            if narrative_extraction.decisions:
                parts.append("Decisions: " + "; ".join(d.what[:80] for d in narrative_extraction.decisions[:5]))
            if narrative_extraction.action_items:
                parts.append("Action items: " + "; ".join(a.task[:80] for a in narrative_extraction.action_items[:5]))
            if narrative_extraction.ideas:
                parts.append("Ideas: " + "; ".join(i.concept[:80] for i in narrative_extraction.ideas[:5]))
            if narrative_extraction.tensions:
                parts.append("Tensions: " + "; ".join(t.opposing_views[:80] for t in narrative_extraction.tensions[:3]))
            data_summary = "\n".join(parts) or narrative_extraction.raw_transcript[:3000]
        elif etl and etl.data_file_path and Path(etl.data_file_path).exists():
            try:
                df = pd.read_csv(etl.data_file_path)
                data_summary = df.describe().to_string()
                if len(data_summary) < 100:
                    data_summary = df.head(20).to_string()
            except Exception:
                pass

        if not analysis.insights and not data_summary:
            return analysis

        industry = DOMAIN_TO_INDUSTRY.get(domain, "business")
        market_trends = _fetch_market_trends(industry)

        insights_summary = "\n".join(
            f"- {i.headline}: {i.detail}" for i in analysis.insights[:5]
        ) or "No standard insights."

        prompt = _build_genius_prompt(
            data_summary=data_summary,
            domain=domain.value,
            metrics_computed=analysis.metrics_computed or [],
            patterns_detected=analysis.patterns_detected or [],
            insights_summary=insights_summary,
            market_trends=market_trends,
            narrative=narrative,
            narrative_metrics=analysis.narrative_metrics if narrative else None,
        )

        try:
            response = await self.llm.complete(
                prompt,
                system="You are a strategic analyst. Respond only with valid JSON.",
                max_tokens=1024,
                temperature=0.3,
            )
            parsed = _parse_genius_response(response)
            if parsed:
                genius = GeniusInsight(
                    thesis=parsed.get("thesis", ""),
                    mechanism=parsed.get("mechanism", ""),
                    market_confluence=parsed.get("market_confluence", ""),
                    estimated_upside=parsed.get("estimated_upside", ""),
                    kill_switch=parsed.get("kill_switch", ""),
                )
                analysis.genius_insight = genius
        except Exception:
            pass  # Graceful degradation: keep analysis unchanged

        return analysis
