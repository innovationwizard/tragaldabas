"""Pipeline orchestrator"""

from dataclasses import dataclass
from typing import Optional

from core.models import *
from core.exceptions import PipelineError, StageError
from core.enums import ContentType, FileType
from stages import (
    Receiver, Classifier, StructureInferrer, Archaeologist,
    Reconciler, ETLManager, Analyzer, OutputManager,
    CellClassifier, DependencyGraphBuilder, LogicExtractor,
    CodeGenerator, Scaffolder
)
from ui.progress import ProgressTracker
from ui.prompts import UserPrompt
from config import settings


@dataclass
class PipelineContext:
    """Shared context passed through pipeline"""
    file_path: str
    reception: Optional[ReceptionResult] = None
    classification: Optional[ContentClassification] = None
    structure: Optional[StructureResult] = None
    archaeology: Optional[ArchaeologyResult] = None
    reconciliation: Optional[ReconciliationResult] = None
    etl: Optional[ETLResult] = None
    analysis: Optional[AnalysisResult] = None
    output: Optional[OutputResult] = None
    cell_classification: Optional[CellClassificationResult] = None
    dependency_graph: Optional[DependencyGraph] = None
    logic_extraction: Optional[LogicExtractionResult] = None
    generated_project: Optional[GeneratedProject] = None
    scaffold: Optional[ScaffoldResult] = None


class Orchestrator:
    """Pipeline coordinator"""
    
    def __init__(
        self,
        progress: ProgressTracker,
        prompt: UserPrompt,
        db_connection_string: Optional[str] = None
    ):
        self.progress = progress
        self.prompt = prompt
        self.db_connection_string = db_connection_string
        
        # Initialize stages
        self.stages = {
            0: Receiver(),
            1: Classifier(),
            2: StructureInferrer(),
            3: Archaeologist(),
            4: Reconciler(),
            5: ETLManager(db_connection_string),
            6: Analyzer(),
            7: OutputManager(),
            8: CellClassifier(),
            9: DependencyGraphBuilder(),
            10: LogicExtractor(),
            11: CodeGenerator(),
            12: Scaffolder(),
        }
    
    async def run(self, file_path: str) -> PipelineContext:
        """Execute full pipeline"""
        ctx = PipelineContext(file_path=file_path)
        
        try:
            # Stage 0: Reception
            ctx.reception = await self._execute_stage(0, file_path)

            # Audio language confirmation (optional)
            if ctx.reception and ctx.reception.metadata.file_type == FileType.AUDIO:
                detected = ctx.reception.metadata.transcript_language
                if detected:
                    language, confirmed = await self.prompt.confirm_language(detected)
                    ctx.reception.metadata.transcript_language_confirmed = confirmed
                    ctx.reception.metadata.transcript_language = language
            
            # Stage 1: Classification
            ctx.classification = await self._execute_stage(1, ctx.reception)
            ctx.classification = await self._confirm_classification(ctx.classification)
            
            # Branch based on content type
            if ctx.classification.primary_type == ContentType.NARRATIVE:
                ctx = await self._narrative_path(ctx)
            else:
                ctx = await self._structured_path(ctx)
            
            # Stage 6: Analysis
            ctx.analysis = await self._execute_stage(6, {
                "etl": ctx.etl,
                "domain": ctx.classification.domain
            })
            
            # Stage 7: Output
            ctx.output = await self._execute_stage(7, ctx.analysis)

            if self._should_generate_app(ctx):
                ctx = await self._app_generation_path(ctx)
            
            # Handle both sync and async progress trackers
            complete_result = self.progress.complete()
            if hasattr(complete_result, '__await__'):
                await complete_result
            
            return ctx
            
        except StageError as e:
            # Handle both sync and async progress trackers
            fail_result = self.progress.fail(e.stage, str(e))
            if hasattr(fail_result, '__await__'):
                await fail_result
            raise PipelineError(f"Pipeline failed at stage {e.stage}: {e}", stage=e.stage)

    async def run_app_generation(self, file_path: str) -> PipelineContext:
        """Execute app generation stages (8-12) only."""
        ctx = PipelineContext(file_path=file_path)
        try:
            ctx = await self._app_generation_path(ctx)

            complete_result = self.progress.complete()
            if hasattr(complete_result, '__await__'):
                await complete_result

            return ctx
        except StageError as e:
            fail_result = self.progress.fail(e.stage, str(e))
            if hasattr(fail_result, '__await__'):
                await fail_result
            raise PipelineError(f"Pipeline failed at stage {e.stage}: {e}", stage=e.stage)

    async def run_etl_only(self, file_path: str) -> PipelineContext:
        """Execute stages 0-5 to load data into a target database."""
        ctx = PipelineContext(file_path=file_path)
        try:
            ctx.reception = await self._execute_stage(0, file_path)
            ctx.classification = await self._execute_stage(1, ctx.reception)

            if ctx.classification.primary_type == ContentType.NARRATIVE:
                ctx = await self._narrative_path(ctx)
            else:
                ctx = await self._structured_path(ctx)

            complete_result = self.progress.complete()
            if hasattr(complete_result, '__await__'):
                await complete_result

            return ctx
        except StageError as e:
            fail_result = self.progress.fail(e.stage, str(e))
            if hasattr(fail_result, '__await__'):
                await fail_result
            raise PipelineError(f"Pipeline failed at stage {e.stage}: {e}", stage=e.stage)
    
    async def _structured_path(self, ctx: PipelineContext) -> PipelineContext:
        """Process structured data (Excel, CSV)"""
        
        # Stage 2: Structure Inference
        ctx.structure = await self._execute_stage(2, ctx.reception)
        
        # Stage 3: Archaeology
        ctx.archaeology = await self._execute_stage(3, {
            "reception": ctx.reception,
            "structure": ctx.structure
        })
        
        # Stage 4: Reconciliation (if multi-sheet)
        if len(ctx.reception.previews) > 1:
            ctx.reconciliation = await self._execute_stage(4, ctx.archaeology)
        
        # Stage 5: ETL
        etl_input = ctx.reconciliation or ctx.archaeology
        ctx.etl = await self._execute_stage(5, etl_input)
        
        return ctx
    
    async def _narrative_path(self, ctx: PipelineContext) -> PipelineContext:
        """Process narrative documents (Word)"""
        
        # Stage 2: Document structure
        ctx.structure = await self._execute_stage(2, ctx.reception)
        
        # Skip stages 3-4 (not applicable)
        # Stage 5: Extract facts, persist as structured
        ctx.etl = await self._execute_stage(5, {
            "reception": ctx.reception,
            "structure": ctx.structure,
            "narrative_mode": True
        })
        
        return ctx

    async def _app_generation_path(self, ctx: PipelineContext) -> PipelineContext:
        """Generate a web app from Excel workbooks (Stages 8-12)."""
        ctx.cell_classification = await self._execute_stage(8, ctx.file_path)
        ctx.dependency_graph = await self._execute_stage(9, ctx.cell_classification)
        ctx.logic_extraction = await self._execute_stage(10, ctx.dependency_graph)
        ctx.generated_project = await self._execute_stage(
            11,
            AppGenerationContext(
                cell_classification=ctx.cell_classification,
                logic_extraction=ctx.logic_extraction,
                dependency_graph=ctx.dependency_graph,
            ),
        )
        ctx.scaffold = await self._execute_stage(12, ctx.generated_project)
        return ctx

    def _should_generate_app(self, ctx: PipelineContext) -> bool:
        if not settings.EXCEL_APP_GENERATION_ENABLED:
            return False
        if not ctx.reception:
            return False
        return ctx.reception.metadata.file_type in {
            FileType.EXCEL_XLSX,
            FileType.EXCEL_XLS,
        }
    
    async def _execute_stage(self, stage_num: int, input_data) -> any:
        """Execute a single stage with progress tracking"""
        stage = self.stages[stage_num]
        
        # Handle both sync and async progress trackers
        start_result = self.progress.start_stage(stage_num, stage.name)
        if hasattr(start_result, '__await__'):
            await start_result
        
        if not stage.validate_input(input_data):
            raise StageError(stage_num, "Invalid input")
        
        result = await stage.execute(input_data)
        
        # Handle both sync and async progress trackers
        complete_result = self.progress.complete_stage(stage_num)
        if hasattr(complete_result, '__await__'):
            await complete_result
        
        return result
    
    async def _confirm_classification(
        self, 
        classification: ContentClassification
    ) -> ContentClassification:
        """User checkpoint: confirm domain if low confidence"""
        if classification.confidence < settings.CONFIDENCE_THRESHOLD:
            confirmed = await self.prompt.yes_no(
                f"I detected this as {classification.domain.value}. Correct?"
            )
            if not confirmed:
                new_domain = await self.prompt.select_domain()
                classification.domain = new_domain
            classification.user_confirmed = True
        return classification

