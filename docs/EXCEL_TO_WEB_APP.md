# Excel to Web App Generator (Stages 8-12)
 
## Overview
This document extends the existing pipeline with stages 8-12 to interpret Excel workbooks
as interactive business logic and generate a deployable web application that replaces the spreadsheet.
 
## Pipeline Extension Summary
Stages 8-12 come after Stage 7 (Output) and focus on understanding formulas, extracting business logic,
and generating a Next.js + Prisma + TypeScript app.
 
```
Stage 8  -> Cell Classification
Stage 9  -> Dependency Graph
Stage 10 -> Logic Extraction
Stage 11 -> Code Generation
Stage 12 -> Scaffold & Deploy
```
 
## Stage 8: Cell Classification
**Purpose**: Categorize every cell by functional role and capture validation, formatting, and macro behavior.
 
### Cell Role Taxonomy
```typescript
enum CellRole {
  INPUT = "input",                 // User-editable, feeds formulas
  FORMULA = "formula",             // Contains calculation
  OUTPUT = "output",               // Formula result, not referenced elsewhere
  INTERMEDIATE = "intermediate",   // Formula referenced by other formulas
  STATIC = "static",               // Constant, not referenced
  LABEL = "label",                 // Descriptive text
  STRUCTURAL = "structural",       // Headers, section dividers
}
 
enum InputType {
  TEXT = "text",
  NUMBER = "number",
  DATE = "date",
  BOOLEAN = "boolean",
  CURRENCY = "currency",
  PERCENTAGE = "percentage",
  ENUM = "enum",                   // Data validation list
}
```
 
### Classification Flow (logic)
```
Cell has formula?
  YES -> Referenced by other formulas?
           YES -> INTERMEDIATE
           NO  -> OUTPUT
  NO  -> Referenced by formulas?
           YES -> Has data validation?
                    YES -> INPUT (typed)
                    NO  -> INPUT (infer)
           NO  -> Adjacent to INPUT/OUTPUT?
                    YES -> LABEL
                    NO  -> STATIC
```
 
### Data Validation Extraction
| Excel Validation | Mapped Input Type |
|------------------|-------------------|
| List             | enum with options |
| Whole number     | number with min/max |
| Decimal          | number with precision |
| Date             | date with range constraints |
| Text length      | text with maxLength |
| Custom formula   | validation function |
 
### VBA Macro Analysis (if present)
1. Extract VBA modules via `oletools`/`openpyxl`
2. Parse for worksheet events, assignments, and conditional logic
3. LLM semantic mapping to TypeScript functions
4. Flag unsupported patterns (COM objects, external calls)
 
### Output Model (Stage 8)
```typescript
interface CellClassificationResult {
  sheets: SheetClassification[];
  namedRanges: NamedRange[];
  vbaMacros: VBAMacro[];
  dataValidations: DataValidation[];
  conditionalFormats: ConditionalFormat[];
  pivotTables: PivotTableDefinition[];
}
 
interface SheetClassification {
  name: string;
  cells: ClassifiedCell[];
  inputGroups: InputGroup[];        // Logically related inputs
  outputGroups: OutputGroup[];      // Logically related outputs
  sections: SheetSection[];         // Structural divisions
}
 
interface ClassifiedCell {
  address: string;                  // "A1", "Sheet2!B5"
  role: CellRole;
  inputType?: InputType;
  label?: string;
  formula?: string;
  value?: unknown;
  validation?: DataValidation;
  formatting?: CellFormatting;
  referencedBy: string[];
  references: string[];
}
```
 
## Stage 9: Dependency Graph Construction
**Purpose**: Build a complete calculation dependency graph with execution order and clustering.
 
```typescript
interface DependencyGraph {
  nodes: Map<string, GraphNode>;
  edges: Edge[];
  executionOrder: string[];         // Topological sort
  clusters: CalculationCluster[];   // Independent subgraphs
  circularRefs: CircularRef[];      // Error or iterative calc
}
 
interface GraphNode {
  address: string;
  role: CellRole;
  formula?: ParsedFormula;
  inDegree: number;
  outDegree: number;
  depth: number;                    // Distance from inputs
  cluster: string;
}
 
interface Edge {
  from: string;                     // Source cell
  to: string;                       // Target cell
  type: "direct" | "range" | "named" | "cross_sheet";
}
 
interface CalculationCluster {
  id: string;
  inputs: string[];
  outputs: string[];
  intermediates: string[];
  semanticPurpose?: string;         // LLM-inferred: "Tax calculation"
}
```
 
### Cross-Sheet Resolution
All references are normalized to fully-qualified addresses (e.g., `Sheet2!B5`).
Named ranges are expanded into explicit ranges for graph construction.
 
### Circular Reference Handling
```typescript
interface CircularRef {
  cycle: string[];                  // ["A1", "B1", "C1", "A1"]
  type: "error" | "iterative";
  maxIterations?: number;
  convergenceThreshold?: number;
}
```
If iterative, generate equivalent loop with convergence checks; otherwise flag for resolution.
 
## Stage 10: Business Logic Extraction
**Purpose**: Parse formulas into an IR and infer semantic business rules.
 
### Parsed Formula Model
```typescript
interface ParsedFormula {
  raw: string;                      // "=IF(A1>100,A1*0.1,0)"
  ast: FormulaAST;
  functions: FunctionCall[];
  references: CellReference[];
  constants: Constant[];
  semanticType?: SemanticType;      // LLM-inferred
}
 
interface FormulaAST {
  type: "function" | "operator" | "reference" | "literal" | "array";
  value?: unknown;
  children?: FormulaAST[];
  metadata?: {
    excelFunction: string;
    typescriptEquivalent: string;
  };
}
```
 
### Function Mapping (examples)
| Excel Function | TypeScript Equivalent | Notes |
|---|---|---|
| SUM | `array.reduce((a,b) => a + b, 0)` | |
| IF | Ternary `? :` | |
| VLOOKUP | `Map.get()` or `array.find()` | |
| INDEX/MATCH | `array[index]` | |
| SUMIF | `array.filter().reduce()` | |
| ARRAYFORMULA | `.map()` | |
| LAMBDA | Arrow function | direct mapping |
| LET | Variable declarations | |
| OFFSET | Dynamic range | complex |
| INDIRECT | Runtime references | very complex |
 
### Semantic Type Inference
```typescript
enum SemanticType {
  TAX_CALCULATION = "tax_calculation",
  DISCOUNT_LOGIC = "discount_logic",
  AGGREGATION = "aggregation",
  LOOKUP = "lookup",
  CONDITIONAL_LOGIC = "conditional_logic",
  DATE_CALCULATION = "date_calculation",
  FINANCIAL_FORMULA = "financial_formula",
  STATISTICAL = "statistical",
  STRING_MANIPULATION = "string_manipulation",
  CUSTOM_BUSINESS_RULE = "custom_business_rule",
}
```
 
### Business Rule Extraction
```typescript
interface BusinessRule {
  id: string;
  name: string;                     // "Volume Discount Calculation"
  description: string;              // "Applies 10% discount for orders > $1000"
  inputs: RuleInput[];
  outputs: RuleOutput[];
  logic: LogicRepresentation;
  constraints: Constraint[];
  testCases: TestCase[];            // Derived from current data
}
 
interface LogicRepresentation {
  pseudocode: string;
  typescript: string;
  validation: string;               // Zod schema
}
```
 
### Pivot Tables and Conditional Formatting
- Pivot tables become aggregation definitions (group-by + aggregation).
- Conditional formats are translated into UI hints (highlight, badges, severity).
 
### Output Model (Stage 10)
```typescript
interface LogicExtractionResult {
  businessRules: BusinessRule[];
  calculations: CalculationUnit[];
  lookupTables: LookupTable[];
  pivotDefinitions: PivotDefinition[];
  uiHints: UIHint[];
  unsupportedFeatures: UnsupportedFeature[];
  testSuite: TestCase[];
}
```
 
## Stage 11: Code Generation
**Purpose**: Generate a production-ready Next.js + Prisma + TypeScript application.
 
### Generation Pipeline (conceptual)
```
LogicExtractionResult
  -> Schema generation (prisma/schema.prisma)
  -> Types and validation (src/types)
  -> Calculation engine (src/lib/calculations)
  -> API routes (src/app/api)
  -> UI components (src/components, src/app)
  -> Tests (__tests__)
```
 
### Generated Project Structure (example)
```
generated-app/
  prisma/
    schema.prisma
  src/
    app/
      layout.tsx
      page.tsx
      api/
        calculate/route.ts
        scenarios/route.ts
        export/route.ts
      scenarios/page.tsx
    components/
      InputForm.tsx
      ResultsDisplay.tsx
      InputGroup.tsx
      OutputGroup.tsx
    lib/
      calculations/
      lookups/
      validation/
    types/
  __tests__/
```
 
## Stage 12: Scaffold and Deploy
**Purpose**: Create a deployable project, run migrations, and publish.
 
### Scaffold Flow
1. Create project directory
2. Write generated files
3. Initialize git repository
4. Install dependencies
5. Run Prisma migrations
6. Run tests (match Excel outputs)
7. Create Vercel project
8. Push to GitHub (deploy)
9. Return deployment URL
 
```typescript
interface DeploymentConfig {
  projectName: string;
  vercelTeam?: string;
  githubOrg: string;
  databaseProvider: "supabase" | "vercel-postgres" | "neon";
  envVars: {
    DATABASE_URL: string;
    NEXTAUTH_SECRET: string;
  };
}
 
interface ScaffoldResult {
  projectPath: string;
  githubUrl: string;
  deploymentUrl: string;
  databaseUrl: string;
  testResults: {
    passed: number;
    failed: number;
    failures: TestFailure[];
  };
  generationReport: {
    totalInputs: number;
    totalOutputs: number;
    businessRules: number;
    unsupportedFeatures: UnsupportedFeature[];
    manualReviewRequired: string[];
  };
}
```
 
## Data Models Summary (Pydantic additions)
```python
# Stage 8
class ClassifiedCell(BaseModel):
    address: str
    role: CellRole
    input_type: Optional[InputType]
    label: Optional[str]
    formula: Optional[str]
    value: Any
    validation: Optional[DataValidation]
    referenced_by: List[str]
    references: List[str]
 
class CellClassificationResult(BaseModel):
    sheets: List[SheetClassification]
    named_ranges: List[NamedRange]
    vba_macros: List[VBAMacro]
    data_validations: List[DataValidation]
    conditional_formats: List[ConditionalFormat]
    pivot_tables: List[PivotTableDefinition]
 
# Stage 9
class DependencyGraph(BaseModel):
    nodes: Dict[str, GraphNode]
    edges: List[Edge]
    execution_order: List[str]
    clusters: List[CalculationCluster]
    circular_refs: List[CircularRef]
 
# Stage 10
class BusinessRule(BaseModel):
    id: str
    name: str
    description: str
    inputs: List[RuleInput]
    outputs: List[RuleOutput]
    logic: LogicRepresentation
    constraints: List[Constraint]
    test_cases: List[TestCase]
 
class LogicExtractionResult(BaseModel):
    business_rules: List[BusinessRule]
    calculations: List[CalculationUnit]
    lookup_tables: List[LookupTable]
    pivot_definitions: List[PivotDefinition]
    ui_hints: List[UIHint]
    unsupported_features: List[UnsupportedFeature]
    test_suite: List[TestCase]
 
# Stage 11-12
class GeneratedProject(BaseModel):
    files: Dict[str, str]           # path -> content
    dependencies: Dict[str, str]    # package -> version
    prisma_schema: str
    test_suite: List[TestCase]
 
class ScaffoldResult(BaseModel):
    project_path: str
    github_url: str
    deployment_url: str
    database_url: str
    test_results: TestResults
    generation_report: GenerationReport
```
 
## LLM Prompting Strategy
### Stage 8: Cell Role Inference
```
Given this Excel cell context:
- Address: {address}
- Value: {value}
- Formula: {formula}
- Adjacent cells: {adjacent}
- Data validation: {validation}
- Conditional formatting: {formatting}
 
Classify this cell's role and semantic purpose.
Return JSON: {role, inputType, semanticLabel, confidence}
```
 
### Stage 10: Business Rule Extraction
```
Analyze this calculation cluster from an Excel spreadsheet:
 
Inputs:
{inputs with labels and sample values}
 
Formulas (in dependency order):
{formulas with addresses}
 
Outputs:
{outputs with labels and sample values}
 
Extract the business rules. For each rule:
1. Name (concise, business-friendly)
2. Description (what it does, when it applies)
3. Pseudocode logic
4. TypeScript implementation
5. Zod validation schema for inputs
6. Test cases (at least 3, including edge cases)
 
Return structured JSON.
```
 
## Unsupported Dynamic References
Dynamic references such as `INDIRECT` and `OFFSET` must be detected and reported.
They are blocked by default because they cannot be reliably converted to static code.
 
### Error Report Contract (example)
```typescript
interface GenerationErrorReport {
  canProceed: boolean;
  criticalErrors: UnsupportedFeatureError[];
  warnings: UnsupportedFeatureError[];
  affectedCells: {
    address: string;
    formula: string;
    dependents: string[];
  }[];
  impactAnalysis: {
    totalCells: number;
    affectedCells: number;
    percentageAffected: number;
    blockedOutputs: string[];
  };
}
```
