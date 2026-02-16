"""Stage 12: Scaffold and deployment."""

from __future__ import annotations

from datetime import datetime
from pathlib import Path

from config import settings
from core.exceptions import StageError
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
        if not isinstance(input_data, GeneratedProject):
            return False
        if not hasattr(input_data, "files") or not isinstance(input_data.files, dict):
            return False
        if not input_data.files:
            return False
        if not hasattr(input_data, "test_suite"):
            return False
        return True

    async def execute(self, input_data: GeneratedProject) -> ScaffoldResult:
        try:
            project_dir = self._write_project(input_data)
        except Exception as exc:
            raise StageError(self.stage_number, f"Failed to write project files: {exc}") from exc
        test_results = TestResults(passed=0, failed=0, failures=[])
        test_suite = getattr(input_data, "test_suite", []) or []
        report = GenerationReport(
            total_inputs=0,
            total_outputs=0,
            business_rules=len(test_suite),
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
        if not settings.OUTPUT_DIR:
            raise StageError(self.stage_number, "OUTPUT_DIR is not configured")
        base_dir = Path(settings.OUTPUT_DIR).resolve()
        base_dir.mkdir(parents=True, exist_ok=True)
        timestamp = datetime.utcnow().strftime("%Y%m%d%H%M%S")
        project_dir = base_dir / "generated-apps" / f"excel-app-{timestamp}"
        project_dir.mkdir(parents=True, exist_ok=True)

        if not input_data.files or not isinstance(input_data.files, dict):
            raise StageError(self.stage_number, "GeneratedProject.files is empty or invalid")

        project_root = project_dir.resolve()
        written = 0
        for rel_path, content in input_data.files.items():
            if not isinstance(rel_path, str) or not rel_path:
                raise StageError(self.stage_number, f"Invalid file path: {rel_path!r}")
            target_path = (project_dir / rel_path).resolve()
            if not str(target_path).startswith(str(project_root)):
                raise StageError(self.stage_number, f"Path traversal detected: {rel_path}")
            target_path.parent.mkdir(parents=True, exist_ok=True)
            if content is None:
                content = ""
            if not isinstance(content, str):
                raise StageError(
                    self.stage_number,
                    f"File content must be string for {rel_path}, got {type(content).__name__}",
                )
            target_path.write_text(content, encoding="utf-8")
            written += 1

        if written == 0:
            raise StageError(self.stage_number, "No files were written")

        return project_dir
