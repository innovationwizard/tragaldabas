"""Main entry point for Tragaldabas"""

import asyncio
import argparse
import sys
from pathlib import Path

from orchestrator import Orchestrator
from ui.progress import ConsoleProgress
from ui.prompts import ConsolePrompt
from auth.cli import auth_cli
from config import settings


def main():
    # Check if auth command
    if len(sys.argv) > 1 and sys.argv[1] == 'auth':
        auth_cli()
        return 0
    
    parser = argparse.ArgumentParser(
        description="Tragaldabas - Universal Data Ingestor",
        epilog="Use 'python main.py auth --help' for authentication commands"
    )
    parser.add_argument("file", type=Path, help="Input file path")
    parser.add_argument(
        "--db",
        type=str,
        default=settings.DATABASE_URL,
        help="PostgreSQL connection string"
    )
    parser.add_argument(
        "--output-dir",
        type=Path,
        default=settings.OUTPUT_DIR,
        help="Output directory"
    )
    
    args = parser.parse_args()
    
    if not args.file.exists():
        print(f"Error: File not found: {args.file}")
        return 1
    
    progress = ConsoleProgress()
    prompt = ConsolePrompt()
    
    orchestrator = Orchestrator(
        progress=progress,
        prompt=prompt,
        db_connection_string=args.db
    )
    
    try:
        ctx = asyncio.run(orchestrator.run(str(args.file)))
        
        print(f"\n✓ Pipeline complete")
        print(f"  Insights: {ctx.output.text_file_path if ctx.output else 'N/A'}")
        print(f"  Presentation: {ctx.output.pptx_file_path if ctx.output else 'N/A'}")
        print(f"  Schema: {ctx.etl.schema_sql[:100] + '...' if ctx.etl else 'N/A'}")
        
        return 0
        
    except Exception as e:
        print(f"\n✗ Pipeline failed: {e}")
        import traceback
        traceback.print_exc()
        return 1


if __name__ == "__main__":
    exit(main())
