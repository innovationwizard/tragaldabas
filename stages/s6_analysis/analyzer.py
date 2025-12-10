"""Stage 6: Analysis & Insight Generation"""

import pandas as pd
from typing import Dict, Any
import uuid

from core.interfaces import Stage
from core.models import ETLResult, AnalysisResult, Insight, Evidence
from core.enums import Domain, Severity, VisualizationType
from core.exceptions import StageError
from llm.client import LLMClient
from llm.prompts import AnalysisPrompt, InsightsPrompt
from config import settings


class Analyzer(Stage[Dict[str, Any], AnalysisResult]):
    """Stage 6: Generate insights and analysis"""
    
    @property
    def name(self) -> str:
        return "Analysis & Insight Generation"
    
    @property
    def stage_number(self) -> int:
        return 6
    
    def __init__(self):
        self.llm = LLMClient()
        self.analysis_prompt = AnalysisPrompt()
        self.insights_prompt = InsightsPrompt()
    
    def validate_input(self, input_data: Dict[str, Any]) -> bool:
        return "etl" in input_data or "reconciliation" in input_data
    
    async def execute(self, input_data: Dict[str, Any]) -> AnalysisResult:
        """Execute analysis stage"""
        # Get data and domain
        etl: ETLResult = input_data.get("etl")
        domain: Domain = input_data.get("domain", Domain.GENERAL)
        
        if not etl:
            return AnalysisResult(domain=domain, insights=[])
        
        # Load data
        df = pd.read_csv(etl.data_file_path)
        
        # Build analysis context
        context = {
            "domain": domain.value,
            "table_name": etl.schema.table_name,
            "row_count": len(df),
            "columns": [col.name for col in etl.schema.columns],
            "data_summary": df.describe().to_string()
        }
        
        # Get LLM analysis
        prompt = self.analysis_prompt.build_prompt(context)
        response = await self.llm.complete(prompt)
        result = self.analysis_prompt.parse_response(response)
        
        # Filter insights
        insights_context = {
            "domain": domain.value,
            "insights": result.get("preliminary_insights", [])
        }
        
        insights_prompt = self.insights_prompt.build_prompt(insights_context)
        insights_response = await self.llm.complete(insights_prompt)
        qualified = self.insights_prompt.parse_response(insights_response)
        
        # Build insight objects
        insights = []
        for insight_data in qualified.get("qualified_insights", [])[:settings.MAX_INSIGHTS_PER_ANALYSIS]:
            if not insight_data.get("included", True):
                continue
            
            evidence = Evidence(
                metric=insight_data.get("evidence", {}).get("metric", ""),
                value=insight_data.get("evidence", {}).get("value", 0.0),
                comparison=insight_data.get("evidence", {}).get("comparison"),
                delta=insight_data.get("evidence", {}).get("delta"),
                delta_percent=insight_data.get("evidence", {}).get("delta_percent")
            )
            
            insight = Insight(
                id=str(uuid.uuid4()),
                headline=insight_data.get("headline", ""),
                detail=insight_data.get("detail", ""),
                evidence=evidence,
                implication=insight_data.get("implication", ""),
                severity=Severity(insight_data.get("severity", "info")),
                visualization_hint=VisualizationType(insight_data.get("visualization_hint", "none")),
                included=insight_data.get("included", True)
            )
            insights.append(insight)
        
        return AnalysisResult(
            domain=domain,
            metrics_computed=result.get("metrics_computed", []),
            patterns_detected=result.get("patterns_detected", []),
            insights=insights
        )

