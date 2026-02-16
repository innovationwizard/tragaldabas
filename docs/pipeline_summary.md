# Pipeline Summary

This document is a concise refresher on how the app processes Excel workbooks. It describes
the standard pipeline (stages 1–7) and the Genesis pipeline (stages 8–12).

The purpose of the pipeline is to input Excel files and output the code necessary to build a web app to fully and completely eliminate the need for the user to continue using the input Excel files. 

## High-Level Flow

- Files are uploaded to Supabase Storage and a `pipeline_jobs` row is created.
- The worker (local or deployed) downloads the file, runs the pipeline, and stores results.
- For app-generation jobs, the standard pipeline runs first (1–7), then Genesis runs (8–12).

## Standard Pipeline (Stages 1–7)

1. **Reception**  
   Loads the Excel file and prepares basic workbook metadata and raw sheets.  
   Output: normalized workbook model (sheets, raw cells, metadata).

2. **Classification**  
   Scans cells to detect roles (input, output, label, structural) and data validations.  
   Output: `CellClassificationResult` with labeled cells and validation rules.

3. **Structure Inference**  
   Groups cells into structural concepts (sections, tables, blocks) and annotates the model.  
   Output: structured layout annotations tied to classified cells.

4. **Archaeology**  
   Extracts deeper layout metadata (pivot tables, named ranges, special formatting).  
   Output: enriched workbook metadata (pivots, ranges, formatting hints).

5. **Reconciliation**  
   Aligns earlier stage outputs into a consistent internal model and resolves conflicts.  
   Output: reconciled, internally consistent workbook representation.

6. **Analysis**  
   Performs higher-level analysis and derived insights over the workbook structure.  
   Output: analysis artifacts used by downstream output generation.

7. **Output**  
   Produces human-readable artifacts (text/markdown/pptx) and stores in Supabase Storage.  
   Output: output files + `OutputResult` metadata stored in Supabase.

## Genesis Pipeline (Stages 8–12)

Genesis runs only after stage 7 is complete and the job is approved for app generation.
These stages build a code project based on the extracted business logic.

8. **Cell Classification (Genesis)**  
   Builds a focused classification model for app generation (inputs/outputs and UI hints).  
   Output: refined `CellClassificationResult` for app-generation use.

9. **Dependency Graph**  
   Parses formulas and dependencies between cells, producing a graph and clusters.  
   Output: `DependencyGraph` with edges, execution order, and clusters.

10. **Logic Extraction**  
   Parses formulas into ASTs, builds calculation units, and creates test cases.
   This stage is sensitive to mixed types (ranges, strings, numbers) and must safely
   coerce values while evaluating formulas for tests.  
   Output: `LogicExtractionResult` (rules, calculations, tests, unsupported features).

11. **Code Generation**  
   Generates a Next.js app scaffold: UI components, calculation modules, schemas,
   API routes, and tests. Inputs/outputs are derived from classification and logic results.  
   Output: `GeneratedProject` (file map, deps, Prisma schema, test suite).

12. **Scaffold & Deploy**  
   Writes the generated project to disk (`OUTPUT_DIR`) and returns a scaffold result
   with paths and summary metadata.  
   Output: `ScaffoldResult` with project path and generation report.

## Storage and Job State Notes

- Results are stored as JSON in Supabase Storage under `results/result.json` and the DB
  row points to the storage path.
- Job state transitions: `pending` → `running` → `completed` (or `ready_for_genesis` for app generation).
- Genesis transitions: `pending_genesis` → `genesis_running` → `completed` (or `failed`).
