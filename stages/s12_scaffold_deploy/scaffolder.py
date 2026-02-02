"""Stage 12: Scaffold and deployment."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

from config import settings
from core.interfaces import Stage
from core.models import GeneratedProject, ScaffoldResult, TestResults, GenerationReport


class Scaffolder(Stage[GeneratedProject, ScaffoldResult]):
    """Scaffold a deployable project from generated files."""

    @property
    def name(self) -> str:
        return "Scaffold & Deploy"

    @property
    def stage_number(self) -> int:
        return 12

    def validate_input(self, input_data: GeneratedProject) -> bool:
        return isinstance(input_data, GeneratedProject)

    async def execute(self, input_data: GeneratedProject) -> ScaffoldResult:
        project_dir = self._write_project(input_data)
        test_results = TestResults(passed=0, failed=0, failures=[])
        report = GenerationReport(
            total_inputs=0,
            total_outputs=0,
            business_rules=len(input_data.test_suite),
            unsupported_features=[],
            manual_review_required=[
                "Run prisma migrations",
                "Install dependencies and run tests",
                "Configure environment variables",
            ],
        )
        return ScaffoldResult(
            project_path=str(project_dir),
            github_url="",
            deployment_url="",
            database_url="",
            test_results=test_results,
            generation_report=report,
        )

    def _write_project(self, input_data: GeneratedProject) -> Path:
        base_dir = Path(settings.OUTPUT_DIR).resolve()
        timestamp = datetime.utcnow().strftime("%Y%m%d%H%M%S")
        project_dir = base_dir / "generated-apps" / f"excel-app-{timestamp}"
        project_dir.mkdir(parents=True, exist_ok=True)

        for rel_path, content in input_data.files.items():
            target_path = project_dir / rel_path
            target_path.parent.mkdir(parents=True, exist_ok=True)
            target_path.write_text(content, encoding="utf-8")

        return project_dir
