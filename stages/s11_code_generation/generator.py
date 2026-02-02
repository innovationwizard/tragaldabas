"""Stage 11: Code generation."""

from __future__ import annotations

import json
import re
from typing import Dict, List, Optional

from openpyxl.utils.cell import coordinate_to_tuple

from core.interfaces import Stage
from core.models import (
    AppGenerationContext,
    CellClassificationResult,
    DataValidation,
    GeneratedProject,
    LogicExtractionResult,
)
from core.enums import InputType, CellRole


class CodeGenerator(Stage[AppGenerationContext, GeneratedProject]):
    """Generate application code from extracted logic."""

    @property
    def name(self) -> str:
        return "Code Generation"

    @property
    def stage_number(self) -> int:
        return 11

    def validate_input(self, input_data: AppGenerationContext) -> bool:
        return isinstance(input_data, AppGenerationContext)

    async def execute(self, input_data: AppGenerationContext) -> GeneratedProject:
        logic = input_data.logic_extraction
        inputs = self._build_input_fields(
            input_data.cell_classification, logic
        )
        outputs = self._build_output_fields(input_data.cell_classification, logic)
        files = {
            "README.md": self._readme_content(),
            "package.json": self._package_json(),
            "next.config.js": self._next_config(),
            "tsconfig.json": self._tsconfig(),
            ".gitignore": self._gitignore(),
            "prisma/schema.prisma": self._prisma_schema(inputs, outputs),
            "prisma/migrations/README.md": self._migration_stub(),
            "__tests__/calculations.test.ts": self._tests_stub(logic),
            "src/lib/prisma.ts": self._prisma_client(),
            "src/app/globals.css": self._globals_css(),
            "src/app/layout.tsx": self._layout_component(),
            "src/app/page.tsx": self._page_component(),
            "src/app/api/calculate/route.ts": self._calculate_route(),
            "src/app/api/scenarios/route.ts": self._scenarios_route(),
            "src/components/InputGroup.tsx": self._input_group_component(),
            "src/components/InputForm.tsx": self._input_form_component(),
            "src/components/ResultsDisplay.tsx": self._results_component(),
            "src/lib/inputs.ts": self._inputs_module(inputs, outputs, logic),
            "src/lib/calculations/index.ts": self._calculations_index(logic),
            "src/lib/calculations/types.ts": self._calculations_types(logic),
        }
        for calc in logic.calculations:
            files[f"src/lib/calculations/{self._calculation_filename(calc.id)}"] = (
                self._calculation_file(calc)
            )
        return GeneratedProject(
            files=files,
            dependencies={
                "next": "latest",
                "react": "latest",
                "react-dom": "latest",
                "@prisma/client": "latest",
                "zod": "latest",
            },
            prisma_schema=self._prisma_schema(inputs, outputs),
            test_suite=logic.test_suite,
        )

    def _readme_content(self) -> str:
        return "\n".join([
            "# Generated Excel App",
            "",
            "This project was generated from an Excel workbook.",
            "The calculation logic lives in `src/lib/calculations`.",
            "",
        ])

    def _package_json(self) -> str:
        content = {
            "name": "excel-app",
            "private": True,
            "scripts": {
                "dev": "next dev",
                "build": "next build",
                "start": "next start",
                "prisma:generate": "prisma generate",
            },
            "dependencies": {
                "next": "latest",
                "react": "latest",
                "react-dom": "latest",
                "@prisma/client": "latest",
                "zod": "latest",
            },
            "devDependencies": {
                "typescript": "latest",
                "@types/node": "latest",
                "@types/react": "latest",
                "@types/react-dom": "latest",
                "prisma": "latest",
                "vitest": "latest",
            },
        }
        return json.dumps(content, indent=2)

    def _next_config(self) -> str:
        return "\n".join([
            "/** @type {import('next').NextConfig} */",
            "const nextConfig = {",
            "  reactStrictMode: true,",
            "};",
            "",
            "module.exports = nextConfig;",
            "",
        ])

    def _tsconfig(self) -> str:
        return json.dumps(
            {
                "compilerOptions": {
                    "target": "es2020",
                    "lib": ["dom", "dom.iterable", "esnext"],
                    "allowJs": True,
                    "skipLibCheck": True,
                    "strict": False,
                    "noEmit": True,
                    "esModuleInterop": True,
                    "module": "esnext",
                    "moduleResolution": "bundler",
                    "resolveJsonModule": True,
                    "isolatedModules": True,
                    "jsx": "preserve",
                    "incremental": True,
                },
                "include": ["next-env.d.ts", "**/*.ts", "**/*.tsx"],
                "exclude": ["node_modules"],
            },
            indent=2,
        )

    def _gitignore(self) -> str:
        return "\n".join([
            "node_modules",
            ".next",
            "dist",
            ".env",
            ".env.local",
            "prisma/dev.db",
            "npm-debug.log",
            "",
        ])

    def _globals_css(self) -> str:
        return "\n".join([
            ":root {",
            "  color-scheme: light;",
            "}",
            "",
            "body {",
            "  margin: 0;",
            "  font-family: ui-sans-serif, system-ui, -apple-system, Segoe UI, sans-serif;",
            "  background: #0c0a09;",
            "  color: #e7e5e4;",
            "}",
            "",
            "main {",
            "  max-width: 960px;",
            "  margin: 0 auto;",
            "}",
            "",
            ".card {",
            "  background: #1c1917;",
            "  border: 1px solid #44403c;",
            "  border-radius: 12px;",
            "  padding: 24px;",
            "}",
            "",
            "button {",
            "  background: #f59e0b;",
            "  border: none;",
            "  color: #0c0a09;",
            "  padding: 10px 16px;",
            "  border-radius: 8px;",
            "  font-weight: 600;",
            "  cursor: pointer;",
            "}",
            "",
            "button:disabled {",
            "  opacity: 0.6;",
            "  cursor: not-allowed;",
            "}",
            "",
            "textarea {",
            "  width: 100%;",
            "  min-height: 140px;",
            "  border-radius: 8px;",
            "  border: 1px solid #44403c;",
            "  background: #0c0a09;",
            "  color: #e7e5e4;",
            "  padding: 12px;",
            "  font-family: ui-monospace, SFMono-Regular, Menlo, monospace;",
            "}",
            "",
        ])

    def _layout_component(self) -> str:
        return "\n".join([
            "import './globals.css';",
            "",
            "export const metadata = {",
            "  title: 'Generated Excel App',",
            "  description: 'Generated from an Excel workbook',",
            "};",
            "",
            "export default function RootLayout({ children }: { children: React.ReactNode }) {",
            "  return (",
            "    <html lang=\"en\">",
            "      <body>{children}</body>",
            "    </html>",
            "  );",
            "}",
            "",
        ])

    def _prisma_schema(
        self,
        inputs: List[Dict[str, object]],
        outputs: List[Dict[str, object]],
    ) -> str:
        input_fields = self._prisma_fields(inputs, prefix="input_")
        output_fields = self._prisma_fields(outputs, prefix="output_", optional=True)
        return "\n".join([
            "generator client {",
            "  provider = \"prisma-client-js\"",
            "}",
            "",
            "datasource db {",
            "  provider = \"sqlite\"",
            "  url      = env(\"DATABASE_URL\")",
            "}",
            "",
            "model Scenario {",
            "  id        String   @id @default(cuid())",
            "  name      String",
            *input_fields,
            *output_fields,
            "  createdAt DateTime @default(now())",
            "  updatedAt DateTime @updatedAt",
            "}",
            "",
        ])

    def _migration_stub(self) -> str:
        return "\n".join([
            "# Prisma migrations",
            "",
            "Run the following after setting DATABASE_URL:",
            "",
            "```\n",
            "npx prisma migrate dev --name init",
            "```\n",
        ])

    def _prisma_client(self) -> str:
        return "\n".join([
            "import { PrismaClient } from '@prisma/client';",
            "",
            "export const prisma = globalThis.prisma || new PrismaClient();",
            "",
            "if (process.env.NODE_ENV !== 'production') {",
            "  (globalThis as any).prisma = prisma;",
            "}",
            "",
        ])

    def _prisma_fields(
        self,
        fields: List[Dict[str, object]],
        prefix: str,
        optional: bool = False,
    ) -> List[str]:
        prisma_lines: List[str] = []
        for field in fields:
            field_id = str(field.get("id"))
            field_type = str(field.get("type", "unknown"))
            prisma_type = "String"
            if field_type in {"number", "currency", "percentage"}:
                prisma_type = "Float"
            elif field_type == "boolean":
                prisma_type = "Boolean"
            elif field_type == "date":
                prisma_type = "DateTime"
            elif field_type == "enum":
                prisma_type = "String"
            nullable = "?" if optional else ""
            prisma_lines.append(f"  {prefix}{field_id} {prisma_type}{nullable}")
        return prisma_lines

    def _tests_stub(self, input_data: LogicExtractionResult) -> str:
        lines = [
            "import { calculations } from '../src/lib/calculations';",
            "",
            "describe('Generated calculations', () => {",
        ]
        if not input_data.calculations:
            lines.append("  it('has no calculations', () => {")
            lines.append("    expect(Object.keys(calculations)).toHaveLength(0);")
            lines.append("  });")
        else:
            if input_data.test_suite:
                for test in input_data.test_suite:
                    lines.append(f"  it('calculates {test.name}', () => {{")
                    calc_id = test.name.split('_')[0]
                    lines.append(f"    const result = calculations['{calc_id}']({json.dumps(test.inputs)});")
                    lines.append("    expect(result).toBeDefined();")
                    lines.append("  });")
            else:
                for calc in input_data.calculations:
                    lines.append(f"  it('calculates {calc.id}', () => {{")
                    lines.append(f"    const result = calculations['{calc.id}']({{}});")
                    lines.append("    expect(result).toBeDefined();")
                    lines.append("  });")
        lines.append("});")
        lines.append("")
        return "\n".join(lines)
    def _calculate_route(self) -> str:
        return "\n".join([
            "import { NextResponse } from 'next/server';",
            "import { calculations } from '@/lib/calculations';",
            "import { outputFields, calculationMeta, outputSchema } from '@/lib/inputs';",
            "",
            "export async function POST(request: Request) {",
            "  const payload = await request.json();",
            "  const { calculationId, inputs } = payload || {};",
            "  if (calculationId && calculations[calculationId]) {",
            "    try {",
            "      const result = calculations[calculationId](inputs ?? {});",
            "      const outputValidation = outputSchema.safeParse(result);",
            "      if (!outputValidation.success) {",
            "        return NextResponse.json({",
            "          ok: false,",
            "          calculationId,",
            "          error: 'Output validation failed',",
            "          issues: outputValidation.error.issues,",
            "          outputFields,",
            "          calculationMeta,",
            "        }, { status: 422 });",
            "      }",
            "      return NextResponse.json({ ok: true, calculationId, result, outputFields, calculationMeta });",
            "    } catch (error) {",
            "      const message = error instanceof Error ? error.message : 'Calculation failed';",
            "      return NextResponse.json({ ok: false, calculationId, error: message, outputFields, calculationMeta }, { status: 400 });",
            "    }",
            "  }",
            "  return NextResponse.json({",
            "    ok: true,",
            "    calculations,",
            "    input: payload,",
            "    outputFields,",
            "    calculationMeta,",
            "  });",
            "}",
            "",
        ])

    def _scenarios_route(self) -> str:
        return "\n".join([
            "import { NextResponse } from 'next/server';",
            "import { prisma } from '@/lib/prisma';",
            "import { inputFields, outputFields } from '@/lib/inputs';",
            "",
            "export async function GET() {",
            "  const scenarios = await prisma.scenario.findMany({ orderBy: { createdAt: 'desc' } });",
            "  const shaped = scenarios.map((scenario) => {",
            "    const inputs: Record<string, any> = {};",
            "    const outputs: Record<string, any> = {};",
            "    for (const field of inputFields) {",
            "      const key = `input_${field.id}`;",
            "      inputs[field.address] = (scenario as any)[key] ?? null;",
            "    }",
            "    for (const field of outputFields) {",
            "      const key = `output_${field.id}`;",
            "      outputs[field.address] = (scenario as any)[key] ?? null;",
            "    }",
            "    return {",
            "      id: scenario.id,",
            "      name: scenario.name,",
            "      inputs,",
            "      outputs,",
            "      createdAt: scenario.createdAt,",
            "      updatedAt: scenario.updatedAt,",
            "    };",
            "  });",
            "  return NextResponse.json({ ok: true, scenarios: shaped });",
            "}",
            "",
            "export async function POST(request: Request) {",
            "  const payload = await request.json();",
            "  const data: Record<string, any> = {",
            "    name: payload.name || 'Scenario',",
            "  };",
            "  for (const field of inputFields) {",
            "    const key = `input_${field.id}`;",
            "    data[key] = payload.inputs?.[field.address] ?? null;",
            "  }",
            "  for (const field of outputFields) {",
            "    const key = `output_${field.id}`;",
            "    data[key] = payload.outputs?.[field.address] ?? null;",
            "  }",
            "  const scenario = await prisma.scenario.create({ data });",
            "  return NextResponse.json({ ok: true, scenario });",
            "}",
            "",
            "export async function PUT(request: Request) {",
            "  const payload = await request.json();",
            "  if (!payload.id) {",
            "    return NextResponse.json({ ok: false, error: 'Missing id' }, { status: 400 });",
            "  }",
            "  const data: Record<string, any> = {",
            "    name: payload.name || 'Scenario',",
            "  };",
            "  for (const field of inputFields) {",
            "    const key = `input_${field.id}`;",
            "    data[key] = payload.inputs?.[field.address] ?? null;",
            "  }",
            "  for (const field of outputFields) {",
            "    const key = `output_${field.id}`;",
            "    data[key] = payload.outputs?.[field.address] ?? null;",
            "  }",
            "  const scenario = await prisma.scenario.update({ where: { id: payload.id }, data });",
            "  return NextResponse.json({ ok: true, scenario });",
            "}",
            "",
            "export async function DELETE(request: Request) {",
            "  const payload = await request.json();",
            "  if (!payload.id) {",
            "    return NextResponse.json({ ok: false, error: 'Missing id' }, { status: 400 });",
            "  }",
            "  await prisma.scenario.delete({ where: { id: payload.id } });",
            "  return NextResponse.json({ ok: true });",
            "}",
            "",
        ])

    def _input_form_component(self) -> str:
        return "\n".join([
            "'use client';",
            "",
            "import { useMemo, useState } from 'react';",
            "import { calculationIds, calculationMeta, inputFields, inputSchema } from '@/lib/inputs';",
            "import InputGroup from '@/components/InputGroup';",
            "",
            "type InputFormProps = {",
            "  onSubmit: (payload: Record<string, unknown>) => void;",
            "  onSaveScenario: (name: string, payload: Record<string, unknown>) => void;",
            "  onLoadScenario: (inputs: Record<string, unknown>) => void;",
            "  initialValues?: Record<string, unknown>;",
            "};",
            "",
            "export default function InputForm({ onSubmit, onSaveScenario, onLoadScenario, initialValues }: InputFormProps) {",
            "  const defaults = useMemo(() => {",
            "    const base: Record<string, unknown> = {};",
            "    for (const field of inputFields) {",
            "      base[field.id] = field.type === 'boolean' ? false : '';",
            "    }",
            "    return base;",
            "  }, []);",
            "  const [values, setValues] = useState<Record<string, unknown>>({ ...defaults, ...(initialValues || {}) });",
            "  const [calculationId, setCalculationId] = useState<string>(() => calculationIds[0] ?? '');",
            "  const [scenarioName, setScenarioName] = useState<string>('');",
            "  const activeMeta = calculationId ? calculationMeta[calculationId] : null;",
            "  const [errors, setErrors] = useState<Record<string, string>>({});",
            "  const grouped = useMemo(() => {",
            "    const bySheet: Record<string, Record<string, typeof inputFields>> = {};",
            "    for (const field of inputFields) {",
            "      const sheet = field.sheet || 'Sheet';",
            "      const section = field.section || 'General';",
            "      bySheet[sheet] = bySheet[sheet] || {};",
            "      bySheet[sheet][section] = bySheet[sheet][section] || [];",
            "      bySheet[sheet][section].push(field);",
            "    }",
            "    return bySheet;",
            "  }, []);",
            "",
            "  const handleChange = (id: string, value: unknown) => {",
            "    setValues((prev) => ({ ...prev, [id]: value }));",
            "  };",
            "",
            "  const handleSubmit = () => {",
            "    const payload: Record<string, unknown> = {};",
            "    const nextErrors: Record<string, string> = {};",
            "    for (const field of inputFields) {",
            "      const value = values[field.id];",
            "      if (field.type === 'number' || field.type === 'currency' || field.type === 'percentage') {",
            "        payload[field.id] = value === '' ? null : Number(value);",
            "        if (value === '' || Number.isNaN(payload[field.id] as number)) {",
            "          nextErrors[field.id] = 'Number required';",
            "        }",
            "      } else if (field.type === 'boolean') {",
            "        payload[field.id] = Boolean(value);",
            "      } else if (field.type === 'date') {",
            "        payload[field.id] = value ? new Date(String(value)).toISOString() : null;",
            "        if (!payload[field.id]) {",
            "          nextErrors[field.id] = 'Date required';",
            "        }",
            "      } else {",
            "        payload[field.id] = value === '' ? null : value;",
            "        if (payload[field.id] === null) {",
            "          nextErrors[field.id] = 'Value required';",
            "        }",
            "      }",
            "    }",
            "    const schemaResult = inputSchema.safeParse(payload);",
            "    if (!schemaResult.success) {",
            "      schemaResult.error.issues.forEach((issue) => {",
            "        if (issue.path.length > 0) {",
            "          const key = String(issue.path[0]);",
            "          nextErrors[key] = issue.message;",
            "        }",
            "      });",
            "    }",
            "    if (Object.keys(nextErrors).length > 0) {",
            "      setErrors(nextErrors);",
            "      return;",
            "    }",
            "    setErrors({});",
            "    if (calculationId) {",
            "      payload.calculationId = calculationId;",
            "    }",
            "    onSubmit(payload);",
            "  };",
            "",
            "  const handleSave = () => {",
            "    const payload: Record<string, unknown> = {};",
            "    for (const field of inputFields) {",
            "      payload[field.address] = values[field.id];",
            "    }",
            "    onSaveScenario(scenarioName || 'Scenario', payload);",
            "  };",
            "",
            "  if (inputFields.length === 0) {",
            "    return (",
            "      <div className=\"card\">",
            "        <h2>Inputs</h2>",
            "        <p>No input fields detected in the workbook.</p>",
            "      </div>",
            "    );",
            "  }",
            "",
            "  return (",
            "    <div className=\"card\">",
            "      <h2>Inputs</h2>",
            "      {calculationIds.length > 1 && (",
            "        <label style={{ display: 'grid', gap: 8, marginTop: 16 }}>",
            "          <span>Calculation</span>",
            "          <select",
            "            value={calculationId}",
            "            onChange={(e) => setCalculationId(e.target.value)}",
            "            style={{ padding: 8, borderRadius: 8 }}",
            "          >",
            "            {calculationIds.map((id) => (",
            "              <option key={id} value={id}>{calculationMeta[id]?.name || id}</option>",
            "            ))}",
            "          </select>",
            "        </label>",
            "      )}",
            "      {activeMeta?.constraints?.length > 0 && (",
            "        <div style={{ marginTop: 12, padding: 12, border: '1px solid #f59e0b', borderRadius: 8 }}>",
            "          <strong style={{ color: '#f59e0b' }}>Constraints</strong>",
            "          <ul style={{ marginTop: 8, paddingLeft: 18, color: '#f59e0b' }}>",
            "            {activeMeta.constraints.map((constraint: string) => (",
            "              <li key={constraint}>{constraint}</li>",
            "            ))}",
            "          </ul>",
            "        </div>",
            "      )}",
            "      <div style={{ display: 'grid', gap: 24, marginTop: 16 }}>",
            "        {Object.entries(grouped).map(([sheet, sections]) => (",
            "          <div key={sheet} style={{ display: 'grid', gap: 16 }}>",
            "            <h3 style={{ margin: 0 }}>{sheet}</h3>",
            "            {Object.entries(sections).map(([section, fields]) => (",
            "              <InputGroup",
            "                key={section}",
            "                title={section}",
            "                fields={fields}",
            "                values={values}",
            "                errors={errors}",
            "                onChange={handleChange}",
            "              />",
            "            ))}",
            "          </div>",
            "        ))}",
            "      </div>",
            "      <div style={{ display: 'flex', gap: 12, marginTop: 16 }}>",
            "        <button onClick={handleSubmit}>Run Calculation</button>",
            "        <input",
            "          value={scenarioName}",
            "          onChange={(e) => setScenarioName(e.target.value)}",
            "          placeholder=\"Scenario name\"",
            "          style={{ padding: 8, borderRadius: 8, flex: 1 }}",
            "        />",
            "        <button onClick={handleSave}>Save Scenario</button>",
            "      </div>",
            "    </div>",
            "  );",
            "}",
            "",
        ])

    def _input_group_component(self) -> str:
        return "\n".join([
            "type InputGroupProps = {",
            "  title: string;",
            "  fields: any[];",
            "  values: Record<string, unknown>;",
            "  errors: Record<string, string>;",
            "  onChange: (id: string, value: unknown) => void;",
            "};",
            "",
            "export default function InputGroup({ title, fields, values, errors, onChange }: InputGroupProps) {",
            "  return (",
            "    <div style={{ display: 'grid', gap: 12 }}>",
            "      <h4 style={{ margin: 0, color: '#a8a29e' }}>{title}</h4>",
            "      <div style={{ display: 'grid', gap: 16 }}>",
            "        {fields.map((field) => (",
            "          <label key={field.id} style={{ display: 'grid', gap: 8 }}>",
            "            <span>{field.label}</span>",
            "            {field.type === 'enum' && field.options?.length ? (",
            "              <select",
            "                value={String(values[field.id] ?? '')}",
            "                onChange={(e) => onChange(field.id, e.target.value)}",
            "                style={{ padding: 8, borderRadius: 8 }}",
            "              >",
            "                <option value=\"\">Select</option>",
            "                {field.options.map((opt: string) => (",
            "                  <option key={opt} value={opt}>{opt}</option>",
            "                ))}",
            "              </select>",
            "            ) : field.type === 'boolean' ? (",
            "              <input",
            "                type=\"checkbox\"",
            "                checked={Boolean(values[field.id])}",
            "                onChange={(e) => onChange(field.id, e.target.checked)}",
            "              />",
            "            ) : (",
            "              <input",
            "                type={field.type === 'date' ? 'date' : 'text'}",
            "                value={String(values[field.id] ?? '')}",
            "                onChange={(e) => onChange(field.id, e.target.value)}",
            "                style={{ padding: 8, borderRadius: 8 }}",
            "              />",
            "            )}",
            "            {errors[field.id] && (",
            "              <span style={{ color: '#f87171' }}>{errors[field.id]}</span>",
            "            )}",
            "          </label>",
            "        ))}",
            "      </div>",
            "    </div>",
            "  );",
            "}",
            "",
        ])

    def _results_component(self) -> str:
        return "\n".join([
            "type ResultsDisplayProps = {",
            "  result: Record<string, unknown> | null;",
            "};",
            "",
            "export default function ResultsDisplay({ result }: ResultsDisplayProps) {",
            "  const error = result && typeof result === 'object' && 'error' in result",
            "    ? String((result as Record<string, unknown>).error)",
            "    : null;",
            "  const issues = (result as any)?.issues || null;",
            "  const outputs = result && typeof result === 'object' && 'result' in result",
            "    ? (result as Record<string, any>).result",
            "    : null;",
            "  const outputFields = (result as any)?.outputFields || null;",
            "  const calcId = (result as any)?.calculationId || null;",
            "  const meta = calcId ? (result as any)?.calculationMeta?.[calcId] : null;",
            "  const visibleOutputs = outputFields && meta?.outputs",
            "    ? outputFields.filter((field: any) => meta.outputs.includes(field.address))",
            "    : outputFields;",
            "  return (",
            "    <div className=\"card\" style={{ marginTop: 24 }}>",
            "      <h2>Results</h2>",
            "      {error && (",
            "        <p style={{ color: '#f87171', marginTop: 8 }}>{error}</p>",
            "      )}",
            "      {issues && (",
            "        <div style={{ marginTop: 8, color: '#f59e0b' }}>",
            "          <strong>Output validation issues</strong>",
            "          <ul style={{ marginTop: 6, paddingLeft: 18 }}>",
            "            {issues.map((issue: any, idx: number) => (",
            "              <li key={idx}>{issue.message}</li>",
            "            ))}",
            "          </ul>",
            "        </div>",
            "      )}",
            "      {meta && (",
            "        <div style={{ marginTop: 12 }}>",
            "          <strong>{meta.name}</strong>",
            "          {meta.description && <p style={{ marginTop: 4, color: '#a8a29e' }}>{meta.description}</p>}",
            "          {meta.constraints?.length > 0 && (",
            "            <ul style={{ marginTop: 8, paddingLeft: 18, color: '#f59e0b' }}>",
            "              {meta.constraints.map((constraint: string) => (",
            "                <li key={constraint}>{constraint}</li>",
            "              ))}",
            "            </ul>",
            "          )}",
            "        </div>",
            "      )}",
            "      {outputs && visibleOutputs && (",
            "        <div style={{ display: 'grid', gap: 12, marginTop: 12 }}>",
            "          {visibleOutputs.map((field: any) => (",
            "            <div key={field.id} style={{ display: 'grid', gap: 4 }}>",
            "              <span style={{ color: '#a8a29e' }}>{field.label}</span>",
            "              <strong>{String(outputs[field.address] ?? '')}</strong>",
            "            </div>",
            "          ))}",
            "        </div>",
            "      )}",
            "      <pre>{result ? JSON.stringify(result, null, 2) : 'No results yet.'}</pre>",
            "    </div>",
            "  );",
            "}",
            "",
        ])

    def _calculations_index(self, input_data: LogicExtractionResult) -> str:
        lines = [
            "import type { CalculationFn } from './types';",
            "",
        ]
        for calc in input_data.calculations:
            fn_name = self._calculation_function_name(calc.id)
            file_name = self._calculation_filename(calc.id).replace(".ts", "")
            lines.append(f"import {{ {fn_name} }} from './{file_name}';")
        lines.append("")
        lines.append("export const calculations: Record<string, CalculationFn> = {")
        for calc in input_data.calculations:
            fn_name = self._calculation_function_name(calc.id)
            lines.append(f"  \"{calc.id}\": {fn_name},")
        lines.append("};")
        lines.append("")
        return "\n".join(lines)

    def _calculations_types(self, input_data: LogicExtractionResult) -> str:
        ids = [calc.id for calc in input_data.calculations]
        union = " | ".join([f'\"{calc_id}\"' for calc_id in ids]) or "string"
        return "\n".join([
            f"export type CalculationId = {union};",
            "export type CalculationFn = (inputs: Record<string, unknown>) => Record<string, unknown>;",
            "",
        ])

    def _page_component(self) -> str:
        return "\n".join([
            "'use client';",
            "",
            "import { useState } from 'react';",
            "import InputForm from '@/components/InputForm';",
            "import ResultsDisplay from '@/components/ResultsDisplay';",
            "",
            "export default function Page() {",
            "  const [result, setResult] = useState<Record<string, unknown> | null>(null);",
            "  const [scenarios, setScenarios] = useState<any[]>([]);",
            "  const [loadedInputs, setLoadedInputs] = useState<Record<string, unknown> | undefined>(undefined);",
            "",
            "  const handleSubmit = async (payload: Record<string, unknown>) => {",
            "    const response = await fetch('/api/calculate', {",
            "      method: 'POST',",
            "      headers: { 'Content-Type': 'application/json' },",
            "      body: JSON.stringify({ calculationId: payload?.calculationId, inputs: payload }),",
            "    });",
            "    const data = await response.json();",
            "    setResult(data);",
            "  };",
            "",
            "  const handleSaveScenario = async (name: string, inputs: Record<string, unknown>) => {",
            "    const response = await fetch('/api/scenarios', {",
            "      method: 'POST',",
            "      headers: { 'Content-Type': 'application/json' },",
            "      body: JSON.stringify({ name, inputs, outputs: (result as any)?.result ?? null }),",
            "    });",
            "    const data = await response.json();",
            "    if (data?.scenario) {",
            "      setScenarios((prev) => [data.scenario, ...prev]);",
            "    }",
            "  };",
            "",
            "  const handleLoadScenario = (inputs: Record<string, unknown>) => {",
            "    setLoadedInputs(inputs);",
            "    handleSubmit(inputs);",
            "  };",
            "",
            "  const handleDeleteScenario = async (id: string) => {",
            "    await fetch('/api/scenarios', {",
            "      method: 'DELETE',",
            "      headers: { 'Content-Type': 'application/json' },",
            "      body: JSON.stringify({ id }),",
            "    });",
            "    setScenarios((prev) => prev.filter((item) => item.id !== id));",
            "  };",
            "",
            "  const handleUpdateScenario = async (scenario: any) => {",
            "    const response = await fetch('/api/scenarios', {",
            "      method: 'PUT',",
            "      headers: { 'Content-Type': 'application/json' },",
            "      body: JSON.stringify({",
            "        id: scenario.id,",
            "        name: scenario.name,",
            "        inputs: scenario.inputs,",
            "        outputs: (result as any)?.result ?? null,",
            "      }),",
            "    });",
            "    const data = await response.json();",
            "    if (data?.scenario) {",
            "      setScenarios((prev) => prev.map((item) => (item.id === data.scenario.id ? data.scenario : item)));",
            "    }",
            "  };",
            "",
            "  return (",
            "    <main className=\"min-h-screen p-8\">",
            "      <h1 className=\"text-2xl font-semibold\">Generated Excel App</h1>",
            "      <p className=\"mt-4 text-stone-500\">",
            "        Provide inputs as JSON and run the calculation engine.",
            "      </p>",
            "      <div style={{ marginTop: 24 }}>",
            "        <InputForm",
            "          onSubmit={handleSubmit}",
            "          onSaveScenario={handleSaveScenario}",
            "          onLoadScenario={handleLoadScenario}",
            "          initialValues={loadedInputs}",
            "        />",
            "        <ResultsDisplay result={result} />",
            "        {scenarios.length > 0 && (",
            "          <div className=\"card\" style={{ marginTop: 24 }}>",
            "            <h2>Saved Scenarios</h2>",
            "            <ul style={{ listStyle: 'none', padding: 0, margin: 0 }}>",
            "              {scenarios.map((scenario) => (",
            "                <li key={scenario.id} style={{ display: 'flex', gap: 12, alignItems: 'center', marginTop: 8 }}>",
            "                  <span style={{ flex: 1 }}>{scenario.name}</span>",
            "                  <button onClick={() => handleLoadScenario(scenario.inputs)}>Load</button>",
            "                  <button onClick={() => handleUpdateScenario(scenario)}>Update</button>",
            "                  <button onClick={() => handleDeleteScenario(scenario.id)}>Delete</button>",
            "                </li>",
            "              ))}",
            "            </ul>",
            "          </div>",
            "        )}",
            "      </div>",
            "    </main>",
            "  );",
            "}",
            "",
        ])

    def _inputs_module(
        self,
        inputs: List[Dict[str, object]],
        outputs: List[Dict[str, object]],
        input_data: LogicExtractionResult,
    ) -> str:
        meta = {
            rule.id: {
                "name": rule.name,
                "description": rule.description,
                "outputs": [out.name for out in rule.outputs],
                "constraints": rule.constraints,
            }
            for rule in input_data.business_rules
        }
        schema_fields = []
        output_schema_fields = []
        for field in inputs:
            key = field["id"]
            ftype = field["type"]
            if ftype in {"number", "currency", "percentage"}:
                schema_fields.append(f"{key}: z.number().nullable()")
            elif ftype == "boolean":
                schema_fields.append(f"{key}: z.boolean()")
            elif ftype == "date":
                schema_fields.append(f"{key}: z.string().nullable()")
            else:
                schema_fields.append(f"{key}: z.string().nullable()")
        for field in outputs:
            key = field["address"]
            otype = field.get("type", "unknown")
            if otype in {"number", "currency", "percentage"}:
                output_schema_fields.append(f'"{key}": z.number().nullable()')
            elif otype == "boolean":
                output_schema_fields.append(f'"{key}": z.boolean()')
            elif otype == "date":
                output_schema_fields.append(f'"{key}": z.number().nullable()')
            else:
                output_schema_fields.append(f'"{key}": z.any()')
        schema = f\"z.object({{{', '.join(schema_fields)}}})\"
        output_schema = f\"z.object({{{', '.join(output_schema_fields)}}})\"
        return "\n".join([
            "import { z } from 'zod';",
            "",
            "export type InputField = {",
            "  id: string;",
            "  label: string;",
            "  type: 'text' | 'number' | 'date' | 'boolean' | 'currency' | 'percentage' | 'enum';",
            "  address: string;",
            "  sheet?: string;",
            "  section?: string;",
            "  options?: string[];",
            "};",
            "",
            f"export const inputFields: InputField[] = {json.dumps(inputs, indent=2)};",
            f"export const outputFields = {json.dumps(outputs, indent=2)};",
            f"export const calculationIds = {json.dumps([calc.id for calc in input_data.calculations], indent=2)};",
            f"export const calculationMeta: Record<string, {{ name: string; description?: string; outputs?: string[]; constraints?: string[] }}> = {json.dumps(meta, indent=2)};",
            f"export const inputSchema = {schema};",
            f"export const outputSchema = {output_schema};",
            "",
        ])

    def _build_input_fields(
        self, classification: CellClassificationResult, logic: LogicExtractionResult
    ) -> List[Dict[str, object]]:
        label_map: Dict[str, Dict[Tuple[int, int], str]] = {}
        structural_rows: Dict[str, List[Tuple[int, str]]] = {}
        validation_map: Dict[str, DataValidation] = {}
        inferred_types: Dict[str, str] = {}
        semantic_labels: Dict[str, str] = {}
        output_semantic_labels: Dict[str, str] = {}
        for rule in logic.business_rules:
            for rule_input in rule.inputs:
                if rule_input.data_type:
                    inferred_types[rule_input.name] = rule_input.data_type
                if rule_input.description:
                    semantic_labels[rule_input.name] = rule_input.description
            for rule_output in rule.outputs:
                if rule_output.description:
                    output_semantic_labels[rule_output.name] = rule_output.description
        for validation in classification.data_validations:
            if validation.address:
                validation_map[validation.address] = validation

        for sheet in classification.sheets:
            sheet_labels: Dict[Tuple[int, int], str] = {}
            sheet_structural: List[Tuple[int, str]] = []
            for cell in sheet.cells:
                if cell.role in {CellRole.LABEL, CellRole.STRUCTURAL} and cell.label:
                    coord = self._parse_coordinate(cell.address)
                    if coord:
                        sheet_labels[coord] = cell.label
                        if cell.role == CellRole.STRUCTURAL:
                            sheet_structural.append((coord[0], cell.label))
            label_map[sheet.name] = sheet_labels
            structural_rows[sheet.name] = sorted(sheet_structural)

        inputs: List[Dict[str, object]] = []
        for sheet in classification.sheets:
            for cell in sheet.cells:
                if cell.role != CellRole.INPUT:
                    continue
                coord = self._parse_coordinate(cell.address)
                label = cell.address
                if coord:
                    label = self._find_label(sheet.name, coord, label_map) or label
                if cell.address in semantic_labels:
                    label = semantic_labels[cell.address]
                section = "General"
                if coord:
                    section = self._find_section(sheet.name, coord, structural_rows) or "General"
                validation = validation_map.get(cell.address)
                inferred = inferred_types.get(cell.address)
                input_type = cell.input_type or InputType.TEXT
                if inferred:
                    if inferred == "string":
                        input_type = InputType.TEXT
                    elif inferred == "number":
                        input_type = InputType.NUMBER
                    elif inferred == "boolean":
                        input_type = InputType.BOOLEAN
                    elif inferred == "date":
                        input_type = InputType.DATE
                field = {
                    "id": self._sanitize_id(cell.address),
                    "label": label,
                    "type": input_type.value,
                    "address": cell.address,
                    "sheet": sheet.name,
                    "section": section,
                }
                if validation and validation.options:
                    field["options"] = validation.options
                    field["type"] = "enum"
                inputs.append(field)

        return inputs

    def _build_output_fields(
        self, classification: CellClassificationResult, logic: LogicExtractionResult
    ) -> List[Dict[str, object]]:
        label_map: Dict[str, Dict[Tuple[int, int], str]] = {}
        structural_rows: Dict[str, List[Tuple[int, str]]] = {}
        inferred_types: Dict[str, str] = {}
        for rule in logic.business_rules:
            for rule_output in rule.outputs:
                if rule_output.data_type:
                    inferred_types[rule_output.name] = rule_output.data_type

        for sheet in classification.sheets:
            sheet_labels: Dict[Tuple[int, int], str] = {}
            sheet_structural: List[Tuple[int, str]] = []
            for cell in sheet.cells:
                if cell.role in {CellRole.LABEL, CellRole.STRUCTURAL} and cell.label:
                    coord = self._parse_coordinate(cell.address)
                    if coord:
                        sheet_labels[coord] = cell.label
                        if cell.role == CellRole.STRUCTURAL:
                            sheet_structural.append((coord[0], cell.label))
            label_map[sheet.name] = sheet_labels
            structural_rows[sheet.name] = sorted(sheet_structural)

        outputs: List[Dict[str, object]] = []
        for sheet in classification.sheets:
            for cell in sheet.cells:
                if cell.role != CellRole.OUTPUT:
                    continue
                coord = self._parse_coordinate(cell.address)
                label = cell.address
                if coord:
                    label = self._find_label(sheet.name, coord, label_map) or label
                section = "General"
                if coord:
                    section = self._find_section(sheet.name, coord, structural_rows) or "General"
                if cell.address in output_semantic_labels:
                    label = output_semantic_labels[cell.address]
                output_type = inferred_types.get(cell.address, "unknown")
                outputs.append(
                    {
                        "id": self._sanitize_id(cell.address),
                        "label": label,
                        "address": cell.address,
                        "sheet": sheet.name,
                        "section": section,
                        "type": output_type,
                    }
                )
        return outputs

    def _find_label(
        self,
        sheet_name: str,
        coord: Tuple[int, int],
        label_map: Dict[str, Dict[Tuple[int, int], str]],
    ) -> Optional[str]:
        sheet_labels = label_map.get(sheet_name, {})
        row, col = coord
        for left_col in range(col - 1, 0, -1):
            label = sheet_labels.get((row, left_col))
            if label:
                return label
        for above_row in range(row - 1, 0, -1):
            label = sheet_labels.get((above_row, col))
            if label:
                return label
        return None

    def _find_section(
        self,
        sheet_name: str,
        coord: Tuple[int, int],
        structural_rows: Dict[str, List[Tuple[int, str]]],
    ) -> str:
        row, _ = coord
        for struct_row, label in reversed(structural_rows.get(sheet_name, [])):
            if struct_row <= row and label:
                return label
        return "General"

    def _parse_coordinate(self, address: str) -> Optional[Tuple[int, int]]:
        if "!" not in address:
            return None
        _, coord = address.split("!", 1)
        try:
            return coordinate_to_tuple(coord)
        except ValueError:
            return None

    def _sanitize_id(self, address: str) -> str:
        return address.replace("!", "_").replace(":", "_")

    def _col_letter(self, col_idx: int) -> str:
        result = ""
        while col_idx > 0:
            col_idx, remainder = divmod(col_idx - 1, 26)
            result = chr(65 + remainder) + result
        return result

    def _calculation_filename(self, calc_id: str) -> str:
        return f"{self._sanitize_id(calc_id)}.ts"

    def _calculation_function_name(self, calc_id: str) -> str:
        base = self._sanitize_id(calc_id)
        return f"calculate_{base}"

    def _calculation_file(self, calc) -> str:
        fn_name = self._calculation_function_name(calc.id)
        inputs = ", ".join(calc.inputs) if calc.inputs else "none"
        formula = calc.formulas[0].raw if calc.formulas else ""
        expression = self._translate_formula(formula, calc.id)
        return "\n".join([
            "import type { CalculationFn } from './types';",
            "",
            "const toNumber = (value: unknown) => {",
            "  if (value === null || value === undefined || value === '') return 0;",
            "  if (typeof value === 'number') return value;",
            "  const raw = String(value).trim();",
            "  if (!raw) return 0;",
            "  const percent = raw.endsWith('%');",
            "  const cleaned = raw",
            "    .replace(/%/g, '')",
            "    .replace(/[\\s\\u00A0]/g, '')",
            "    .replace(/[\\$€£¥₩₽₹₺₫₱₦₴₪₡₲₵₸]/g, '')",
            "    .replace(/USD|EUR|GBP|JPY|MXN|COP|CLP|PEN|BRL|ARS|CAD|AUD/gi, '');",
            "  const lastDot = cleaned.lastIndexOf('.');",
            "  const lastComma = cleaned.lastIndexOf(',');",
            "  let normalized = cleaned;",
            "  if (lastDot > -1 || lastComma > -1) {",
            "    const decimalSep = lastDot > lastComma ? '.' : ',';",
            "    const thousandSep = decimalSep === '.' ? ',' : '.';",
            "    normalized = cleaned.split(thousandSep).join('');",
            "    if (decimalSep === ',') {",
            "      normalized = normalized.replace(',', '.');",
            "    }",
            "  }",
            "  const num = Number(normalized);",
            "  if (Number.isNaN(num)) return 0;",
            "  return percent ? num / 100 : num;",
            "};",
            "const excelSerialFromDate = (year: number, month: number, day: number) => {",
            "  const base = new Date(Date.UTC(1899, 11, 30));",
            "  const target = new Date(Date.UTC(year, month - 1, day));",
            "  let days = Math.round((target.getTime() - base.getTime()) / 86400000);",
            "  if (target >= new Date(Date.UTC(1900, 2, 1))) {",
            "    days += 1;",
            "  }",
            "  return days;",
            "};",
            "const dateFromSerial = (serial: number) => {",
            "  const base = new Date(Date.UTC(1899, 11, 30));",
            "  let days = Math.floor(serial);",
            "  if (days >= 60) days -= 1;",
            "  return new Date(base.getTime() + days * 86400000);",
            "};",
            "const toDate = (value: unknown) => {",
            "  if (value instanceof Date) return value;",
            "  if (typeof value === 'number') {",
            "    return dateFromSerial(value);",
            "  }",
            "  if (typeof value === 'string') {",
            "    const iso = new Date(value);",
            "    if (!Number.isNaN(iso.getTime())) return iso;",
            "  }",
            "  const date = new Date(String(value));",
            "  return Number.isNaN(date.getTime()) ? new Date(0) : date;",
            "};",
            "const flatten = (values: unknown[]) => values.flat(Infinity);",
            "",
            "const keyFor = (address: string) => address.replace(/[!:]/g, '_');",
            "const getValue = (address: string, inputs: Record<string, unknown>) => inputs[keyFor(address)];",
            "const sum = (...values: unknown[]) => flatten(values).reduce((acc, v) => acc + toNumber(v), 0);",
            "const average = (...values: unknown[]) => {",
            "  const flat = flatten(values).map(toNumber);",
            "  return flat.length ? flat.reduce((acc, v) => acc + v, 0) / flat.length : 0;",
            "};",
            "const min = (...values: unknown[]) => {",
            "  const flat = flatten(values).map(toNumber);",
            "  return flat.length ? Math.min(...flat) : 0;",
            "};",
            "const max = (...values: unknown[]) => {",
            "  const flat = flatten(values).map(toNumber);",
            "  return flat.length ? Math.max(...flat) : 0;",
            "};",
            "const abs = (value: unknown) => Math.abs(toNumber(value));",
            "const round = (value: unknown, digits: unknown = 0) => {",
            "  const factor = 10 ** toNumber(digits);",
            "  return Math.round(toNumber(value) * factor) / factor;",
            "};",
            "const roundUp = (value: unknown, digits: unknown = 0) => {",
            "  const factor = 10 ** toNumber(digits);",
            "  return Math.ceil(toNumber(value) * factor) / factor;",
            "};",
            "const roundDown = (value: unknown, digits: unknown = 0) => {",
            "  const factor = 10 ** toNumber(digits);",
            "  return Math.floor(toNumber(value) * factor) / factor;",
            "};",
            "const concat = (...values: unknown[]) => values.flat().map((v) => `${v ?? ''}`).join('');",
            "const andFunc = (...values: unknown[]) => values.flat().every((v) => Boolean(v));",
            "const orFunc = (...values: unknown[]) => values.flat().some((v) => Boolean(v));",
            "const notFunc = (value: unknown) => !Boolean(value);",
            "const ifError = (value: unknown, fallback: unknown) => {",
            "  if (value === null || value === undefined) return fallback;",
            "  if (typeof value === 'number' && Number.isNaN(value)) return fallback;",
            "  return value;",
            "};",
            "const today = () => excelSerialFromDate(",
            "  new Date().getUTCFullYear(),",
            "  new Date().getUTCMonth() + 1,",
            "  new Date().getUTCDate()",
            ");",
            "const now = () => {",
            "  const date = new Date();",
            "  const serial = excelSerialFromDate(",
            "    date.getUTCFullYear(),",
            "    date.getUTCMonth() + 1,",
            "    date.getUTCDate()",
            "  );",
            "  return serial + (date.getUTCHours() * 3600 + date.getUTCMinutes() * 60 + date.getUTCSeconds()) / 86400;",
            "};",
            "const dateFunc = (year: unknown, month: unknown, day: unknown) => (",
            "  excelSerialFromDate(toNumber(year), toNumber(month), toNumber(day))",
            ");",
            "const yearFunc = (value: unknown) => toDate(value).getUTCFullYear();",
            "const monthFunc = (value: unknown) => toDate(value).getUTCMonth() + 1;",
            "const dayFunc = (value: unknown) => toDate(value).getUTCDate();",
            "const datedif = (start: unknown, end: unknown, unit: unknown) => {",
            "  const startDate = toDate(start);",
            "  const endDate = toDate(end);",
            "  const unitStr = String(unit || 'D').toUpperCase();",
            "  if (unitStr === 'D') {",
            "    return Math.floor((endDate.getTime() - startDate.getTime()) / 86400000);",
            "  }",
            "  if (unitStr === 'M') {",
            "    return (endDate.getUTCFullYear() - startDate.getUTCFullYear()) * 12",
            "      + (endDate.getUTCMonth() - startDate.getUTCMonth());",
            "  }",
            "  if (unitStr === 'Y') {",
            "    return endDate.getUTCFullYear() - startDate.getUTCFullYear();",
            "  }",
            "  if (unitStr === 'MD') {",
            "    const temp = new Date(Date.UTC(startDate.getUTCFullYear(), startDate.getUTCMonth(), endDate.getUTCDate()));",
            "    return Math.floor((temp.getTime() - startDate.getTime()) / 86400000);",
            "  }",
            "  if (unitStr === 'YM') {",
            "    return endDate.getUTCMonth() - startDate.getUTCMonth() + (endDate.getUTCFullYear() - startDate.getUTCFullYear()) * 12;",
            "  }",
            "  if (unitStr === 'YD') {",
            "    const startOfYear = new Date(Date.UTC(endDate.getUTCFullYear(), 0, 1));",
            "    return Math.floor((endDate.getTime() - startOfYear.getTime()) / 86400000);",
            "  }",
            "  return 0;",
            "};",
            "const eomonth = (start: unknown, months: unknown) => {",
            "  const date = toDate(start);",
            "  const offset = toNumber(months);",
            "  const end = new Date(Date.UTC(date.getUTCFullYear(), date.getUTCMonth() + offset + 1, 0));",
            "  return excelSerialFromDate(end.getUTCFullYear(), end.getUTCMonth() + 1, end.getUTCDate());",
            "};",
            "const workday = (start: unknown, days: unknown, holidays: unknown = []) => {",
            "  let date = toDate(start);",
            "  let remaining = toNumber(days);",
            "  const holidayList = (Array.isArray(holidays) ? holidays : [holidays])",
            "    .map((h) => toDate(h).toDateString());",
            "  const step = remaining >= 0 ? 1 : -1;",
            "  while (remaining !== 0) {",
            "    date = new Date(date.getTime() + step * 86400000);",
            "    const day = date.getUTCDay();",
            "    const isWeekend = day === 0 || day === 6;",
            "    const isHoliday = holidayList.includes(date.toDateString());",
            "    if (!isWeekend && !isHoliday) {",
            "      remaining -= step;",
            "    }",
            "  }",
            "  return excelSerialFromDate(date.getUTCFullYear(), date.getUTCMonth() + 1, date.getUTCDate());",
            "};",
            "const matchFunc = (lookup: unknown, range: unknown[], matchType: unknown = 0) => {",
            "  const list = flatten(range);",
            "  const match = Number(matchType);",
            "  if (match === 0) {",
            "    return list.findIndex((item) => item === lookup) + 1;",
            "  }",
            "  const nums = list.map(toNumber);",
            "  const val = toNumber(lookup);",
            "  if (match > 0) {",
            "    let idx = -1;",
            "    nums.forEach((num, i) => { if (num <= val) idx = i; });",
            "    return idx + 1;",
            "  }",
            "  let idx = -1;",
            "  nums.forEach((num, i) => { if (num >= val && idx === -1) idx = i; });",
            "  return idx + 1;",
            "};",
            "const indexFunc = (table: unknown, row: unknown, col: unknown = 1) => {",
            "  const r = toNumber(row) - 1;",
            "  const c = toNumber(col) - 1;",
            "  if (Array.isArray(table)) {",
            "    const rows = table as unknown[];",
            "    const rowValue = rows[r];",
            "    if (Array.isArray(rowValue)) {",
            "      return (rowValue as unknown[])[c];",
            "    }",
            "    return rowValue;",
            "  }",
            "  return null;",
            "};",
            "const vlookup = (lookup: unknown, table: unknown, col: unknown, rangeLookup: unknown = false) => {",
            "  if (!Array.isArray(table)) return null;",
            "  const colIndex = toNumber(col) - 1;",
            "  const rows = table as unknown[];",
            "  if (!rows.length) return null;",
            "  const exact = !Boolean(rangeLookup);",
            "  const match = exact",
            "    ? rows.find((row) => Array.isArray(row) && row[0] === lookup)",
            "    : rows.find((row) => Array.isArray(row) && toNumber(row[0]) <= toNumber(lookup));",
            "  if (!match || !Array.isArray(match)) return null;",
            "  return match[colIndex] ?? null;",
            "};",
            "const matchesCriteria = (value: unknown, criteria: unknown) => {",
            "  if (criteria === null || criteria === undefined) return false;",
            "  if (typeof criteria === 'number') return toNumber(value) === criteria;",
            "  const crit = String(criteria);",
            "  const opMatch = crit.match(/^(>=|<=|<>|=|>|<)(.*)$/);",
            "  const raw = opMatch ? opMatch[2] : crit;",
            "  const rawValue = raw.replace(/^\"|\"$/g, '');",
            "  if (rawValue.includes('*')) {",
            "    const pattern = new RegExp('^' + rawValue.replace(/\\*/g, '.*') + '$', 'i');",
            "    return pattern.test(String(value ?? ''));",
            "  }",
            "  const left = toNumber(value);",
            "  const right = toNumber(rawValue);",
            "  const op = opMatch ? opMatch[1] : '=';",
            "  switch (op) {",
            "    case '>': return left > right;",
            "    case '<': return left < right;",
            "    case '>=': return left >= right;",
            "    case '<=': return left <= right;",
            "    case '<>': return left !== right;",
            "    default: return String(value ?? '') === rawValue;",
            "  }",
            "};",
            "const sumIf = (range: unknown, criteria: unknown, sumRange?: unknown) => {",
            "  const list = flatten([range]);",
            "  const sums = sumRange ? flatten([sumRange]) : list;",
            "  return list.reduce((acc, value, idx) => {",
            "    if (matchesCriteria(value, criteria)) {",
            "      return acc + toNumber(sums[idx]);",
            "    }",
            "    return acc;",
            "  }, 0);",
            "};",
            "const sumIfs = (sumRange: unknown, ...criteriaPairs: unknown[]) => {",
            "  const sums = flatten([sumRange]);",
            "  const pairs: Array<{ range: unknown[]; criteria: unknown }> = [];",
            "  for (let i = 0; i < criteriaPairs.length; i += 2) {",
            "    pairs.push({ range: flatten([criteriaPairs[i]]), criteria: criteriaPairs[i + 1] });",
            "  }",
            "  return sums.reduce((acc, value, idx) => {",
            "    const matches = pairs.every((pair) => matchesCriteria(pair.range[idx], pair.criteria));",
            "    return matches ? acc + toNumber(value) : acc;",
            "  }, 0);",
            "};",
            "const countIf = (range: unknown, criteria: unknown) => {",
            "  const list = flatten([range]);",
            "  return list.reduce((acc, value) => acc + (matchesCriteria(value, criteria) ? 1 : 0), 0);",
            "};",
            "const xlookup = (lookup: unknown, lookupArray: unknown, returnArray: unknown, notFound: unknown = null) => {",
            "  const lookupList = flatten([lookupArray]);",
            "  const returnList = flatten([returnArray]);",
            "  const idx = lookupList.findIndex((item) => item === lookup);",
            "  if (idx === -1) return notFound;",
            "  return returnList[idx] ?? notFound;",
            "};",
            "const ifFunc = (cond: unknown, a: unknown, b: unknown) => (cond ? a : b);",
            "const unsupportedRange = (range: string) => {",
            "  throw new Error(`Unsupported range: ${range}`);",
            "};",
            "",
            f"// Inputs: {inputs}",
            f"// Output: {calc.id}",
            f"export const {fn_name}: CalculationFn = (inputs) => {{",
            f"  const required = {json.dumps(calc.inputs)};",
            "  const missing = required.filter((addr) => {",
            "    const value = getValue(addr, inputs);",
            "    return value === null || value === undefined || value === '';",
            "  });",
            "  if (missing.length) {",
            "    throw new Error(`Missing required inputs: ${missing.join(', ')}`);",
            "  }",
            f"  const result = {expression};",
            "  return {",
            f"    \"{calc.id}\": result,",
            "  };",
            "};",
            "",
        ])

    def _translate_formula(self, formula: str, default_address: str) -> str:
        if not formula:
            return "null"
        default_sheet = default_address.split("!", 1)[0] if "!" in default_address else ""
        expr = formula.lstrip("=")
        expr = expr.replace(";", ",")
        expr, string_literals = self._extract_string_literals(expr)
        expr, range_replacements = self._extract_range_placeholders(expr, default_sheet)
        expr = self._replace_cell_refs(expr, default_sheet)
        for token, replacement in range_replacements.items():
            expr = expr.replace(token, replacement)
        expr = self._replace_functions(expr)
        expr = self._replace_operators(expr)
        for token, literal in string_literals.items():
            expr = expr.replace(token, literal)
        return expr

    def _extract_range_placeholders(
        self, expr: str, default_sheet: str
    ) -> tuple[str, Dict[str, str]]:
        range_pattern = re.compile(
            r"(?P<sheet>[A-Za-z0-9_ ]+!)?"
            r"(?P<start>\$?[A-Z]{1,3}\$?\d+):"
            r"(?P<end>\$?[A-Z]{1,3}\$?\d+)"
        )
        replacements: Dict[str, str] = {}
        index = 0

        def _replace(match):
            nonlocal index
            sheet = match.group("sheet")[:-1] if match.group("sheet") else default_sheet
            start = match.group("start").replace("$", "")
            end = match.group("end").replace("$", "")
            if not sheet:
                replacement = f'unsupportedRange("{start}:{end}")'
            else:
                addresses = self._expand_range(sheet, start, end, limit=200)
                if addresses is None:
                    replacement = f'unsupportedRange("{sheet}!{start}:{end}")'
                else:
                    values = ", ".join([f'getValue("{addr}", inputs)' for addr in addresses])
                    replacement = f"[{values}]"
            token = f"__RANGE_{index}__"
            replacements[token] = replacement
            index += 1
            return token

        return range_pattern.sub(_replace, expr), replacements

    def _replace_cell_refs(self, expr: str, default_sheet: str) -> str:
        cell_pattern = re.compile(
            r"(?<![A-Za-z0-9_])"
            r"(?P<sheet>[A-Za-z0-9_ ]+!)?"
            r"(?P<cell>\$?[A-Z]{1,3}\$?\d+)"
        )

        def _replace(match):
            sheet = match.group("sheet")[:-1] if match.group("sheet") else default_sheet
            cell = match.group("cell").replace("$", "")
            if sheet:
                return f'getValue("{sheet}!{cell}", inputs)'
            return f'getValue("{cell}", inputs)'

        return cell_pattern.sub(_replace, expr)

    def _extract_string_literals(self, expr: str) -> tuple[str, Dict[str, str]]:
        string_pattern = re.compile(r'"([^"]*)"')
        replacements: Dict[str, str] = {}
        index = 0

        def _replace(match):
            nonlocal index
            token = f"__STR_{index}__"
            replacements[token] = f"\"{match.group(1)}\""
            index += 1
            return token

        return string_pattern.sub(_replace, expr), replacements

    def _replace_functions(self, expr: str) -> str:
        replacements = {
            "SUM": "sum",
            "SUMIF": "sumIf",
            "SUMIFS": "sumIfs",
            "AVERAGE": "average",
            "MIN": "min",
            "MAX": "max",
            "ABS": "abs",
            "ROUND": "round",
            "ROUNDUP": "roundUp",
            "ROUNDDOWN": "roundDown",
            "CONCAT": "concat",
            "CONCATENATE": "concat",
            "AND": "andFunc",
            "OR": "orFunc",
            "NOT": "notFunc",
            "IFERROR": "ifError",
            "IF": "ifFunc",
            "TODAY": "today",
            "NOW": "now",
            "DATE": "dateFunc",
            "DATEDIF": "datedif",
            "EOMONTH": "eomonth",
            "WORKDAY": "workday",
            "YEAR": "yearFunc",
            "MONTH": "monthFunc",
            "DAY": "dayFunc",
            "MATCH": "matchFunc",
            "INDEX": "indexFunc",
            "VLOOKUP": "vlookup",
            "XLOOKUP": "xlookup",
            "COUNTIF": "countIf",
        }
        for excel_name, js_name in replacements.items():
            expr = re.sub(rf"\\b{excel_name}\\s*\\(", f"{js_name}(", expr, flags=re.IGNORECASE)
        return expr

    def _replace_operators(self, expr: str) -> str:
        expr = expr.replace("^", "**")
        expr = expr.replace("&", "+")
        expr = expr.replace("<>", "!=")
        expr = expr.replace(">=", "__GE__").replace("<=", "__LE__")
        expr = expr.replace("=", "==")
        expr = expr.replace("__GE__", ">=").replace("__LE__", "<=")
        expr = re.sub(r"(\\d+(?:\\.\\d+)?)%", r"(\\1/100)", expr)
        return expr

    def _expand_range(
        self, sheet: str, start: str, end: str, limit: int = 200
    ) -> Optional[List[List[str]]]:
        try:
            start_row, start_col = coordinate_to_tuple(start)
            end_row, end_col = coordinate_to_tuple(end)
        except ValueError:
            return None
        min_row = min(start_row, end_row)
        max_row = max(start_row, end_row)
        min_col = min(start_col, end_col)
        max_col = max(start_col, end_col)
        total = (max_row - min_row + 1) * (max_col - min_col + 1)
        if total > limit:
            return None
        rows: List[List[str]] = []
        for row in range(min_row, max_row + 1):
            row_values: List[str] = []
            for col in range(min_col, max_col + 1):
                row_values.append(f"{sheet}!{self._col_letter(col)}{row}")
            rows.append(row_values)
        return rows
