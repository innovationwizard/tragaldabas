# Upgrade Summary (Excel → Web App)

This document summarizes the upgrade work that extends Tragaldabas from the original 7-stage ingestion pipeline to a full Excel-to-web-app generator (Stages 8–12).

## What’s New

### Stage 8: Cell Classification
- Cell role classification (inputs, outputs, labels, structural)
- Validation extraction (including list ranges)
- Conditional formatting hints with severity
- Pivot table metadata extraction
- VBA macro extraction (full module text via oletools)

### Stage 9: Dependency Graph
- Topological execution order
- Clustering of independent calculation subgraphs
- Semantic purpose inference
- Label-aware cluster naming

### Stage 10: Logic Extraction
- Formula AST parsing (including ranges)
- Type inference for inputs and outputs
- Test case synthesis (default + seeded)
- Evaluator supports core Excel functions and date serial semantics
- LLM semantic inference for business rule naming/description

### Stage 11: Code Generation
- Next.js + Prisma project scaffold
- Input and output UI grouped by sheet/section
- Validation (client + server) using Zod
- Calculation engine with translated formulas
- Scenario CRUD + storage with Prisma
- Output rendering with semantic metadata

### Stage 12: Scaffold & Deploy
- Generated project written to disk
- Manual deploy instructions provided

## Key Docs

- `docs/EXCEL_TO_WEB_APP.md`: Architecture and data models for the extension
- `docs/STAGE12_MANUAL_DEPLOY.md`: Manual scaffold + deploy steps

## Current Gaps (if any)

- Deployment automation remains manual (by design)
- Deeper VBA semantic mapping is optional and can be extended if needed

## Next Suggested Steps

- Use `docs/STAGE12_MANUAL_DEPLOY.md` to scaffold and deploy a test workbook
- Validate calculation outputs against source Excel
- Add any missing Excel function mappings as needed
