"""Stage 1: Content Classification"""

from datetime import datetime
from core.interfaces import Stage
from core.models import ReceptionResult, ContentClassification
from core.enums import ContentType, Domain, NarrativeContentType
from core.pipeline_router import is_narrative_file_type
from core.exceptions import StageError
from llm.client import LLMClient
from llm.prompts import ClassificationPrompt
from config import settings


class Classifier(Stage[ReceptionResult, ContentClassification]):
    """Stage 1: Classify content type and domain (or narrative_content_type for narrative path)"""
    
    @property
    def name(self) -> str:
        return "Content Classification"
    
    @property
    def stage_number(self) -> int:
        return 1
    
    def __init__(self):
        self.llm = LLMClient()
        self.prompt_builder = ClassificationPrompt()
    
    def validate_input(self, input_data: ReceptionResult) -> bool:
        """Validate reception result"""
        return isinstance(input_data, ReceptionResult) and input_data.previews
    
    async def execute(self, input_data: ReceptionResult) -> ContentClassification:
        """Execute classification stage"""
        try:
            # Build preview text from first sheet
            preview = input_data.previews[0]
            preview_text = self._build_preview_text(preview)
            
            # Use narrative prompt for audio, documents, notes
            narrative = is_narrative_file_type(input_data.metadata.file_type)
            
            # Build prompt context
            context = {
                "file_name": input_data.metadata.file_name,
                "file_type": input_data.metadata.file_type.value,
                "sheets": [p.sheet_name for p in input_data.previews],
                "preview": preview_text,
                "narrative": narrative,
            }
            
            # Get LLM classification
            prompt = self.prompt_builder.build_prompt(context)
            response = await self.llm.complete(prompt)
            result = self.prompt_builder.parse_response(response)
            
            # Parse dates if present
            time_start = None
            time_end = None
            if result.get("time_period_start"):
                try:
                    time_start = datetime.fromisoformat(result["time_period_start"].replace('Z', '+00:00'))
                except Exception:
                    pass
            if result.get("time_period_end"):
                try:
                    time_end = datetime.fromisoformat(result["time_period_end"].replace('Z', '+00:00'))
                except Exception:
                    pass
            
            # Parse narrative_content_type for narrative path
            narrative_content_type = None
            if narrative and result.get("narrative_content_type"):
                try:
                    narrative_content_type = NarrativeContentType(result["narrative_content_type"])
                except ValueError:
                    narrative_content_type = NarrativeContentType.GENERAL
            
            classification = ContentClassification(
                primary_type=ContentType(result.get("primary_type", "structured")),
                domain=Domain(result.get("domain", "general")),
                narrative_content_type=narrative_content_type,
                entity_name=result.get("entity_name"),
                time_period_start=time_start,
                time_period_end=time_end,
                confidence=result.get("confidence", 0.5),
                user_confirmed=False
            )
            
            return classification
            
        except Exception as e:
            raise StageError(self.stage_number, f"Classification failed: {e}") from e
    
    def _build_preview_text(self, preview) -> str:
        """Build text preview from sheet preview"""
        lines = []
        for row in preview.preview_rows[:50]:  # More rows for narrative
            line = " | ".join(str(cell)[:80] if cell else "" for cell in row)
            lines.append(line)
        return "\n".join(lines)

