"""Stage 10: Business logic extraction."""

from __future__ import annotations

import re
import json
from typing import Dict, List, Set, Tuple, Any

from core.interfaces import Stage
from core.models import (
    DependencyGraph,
    LogicExtractionResult,
    CalculationUnit,
    ParsedFormula,
    UnsupportedFeature,
    BusinessRule,
    RuleInput,
    RuleOutput,
    LogicRepresentation,
    TestCase,
)
from llm.client import LLMClient
from core.exceptions import LLMError


class LogicExtractor(Stage[DependencyGraph, LogicExtractionResult]):
    """Extract business logic from formulas and dependencies."""

    UNSUPPORTED_FUNCTIONS = {"INDIRECT", "OFFSET", "ADDRESS"}
    FUNCTION_PATTERN = re.compile(r"([A-Z][A-Z0-9_]*)\s*\(")
    OPERATOR_PATTERN = re.compile(r"(\+|\-|\*|/|\^|=|<>|>=|<=|>|<)")
    TOKEN_PATTERN = re.compile(
        r'''
        (?P<ws>\s+)
        |(?P<number>\d+(?:\.\d+)?)
        |(?P<string>"[^"]*")
        |(?P<range>(?:[A-Za-z0-9_ ]+!)?\$?[A-Z]{1,3}\$?\d+:\$?[A-Z]{1,3}\$?\d+)
        |(?P<op><>|>=|<=|=|>|<|\+|\-|\*|/|\^|&)
        |(?P<comma>,)
        |(?P<lparen>\()
        |(?P<rparen>\))
        |(?P<ref>(?:[A-Za-z0-9_ ]+!)?\$?[A-Z]{1,3}\$?\d+)
        |(?P<name>[A-Za-z_][A-Za-z0-9_]*)
        ''',
        re.VERBOSE,
    )
    CELL_REF_PATTERN = re.compile(
        r"(?:(?P<sheet>[A-Za-z0-9_ ]+)!|)"
        r"(?P<cell>\$?[A-Z]{1,3}\$?\d+)"
    )

    @property
    def name(self) -> str:
        return "Logic Extraction"

    @property
    def stage_number(self) -> int:
        return 10

    def validate_input(self, input_data: DependencyGraph) -> bool:
        return isinstance(input_data, DependencyGraph)

    async def execute(self, input_data: DependencyGraph) -> LogicExtractionResult:
        unsupported: List[UnsupportedFeature] = []
        calculations: List[CalculationUnit] = []
        business_rules: List[BusinessRule] = []
        test_suite: List[TestCase] = []

        for node in input_data.nodes.values():
            if not node.formula:
                continue

            formula_upper = node.formula.upper()
            for func in self.UNSUPPORTED_FUNCTIONS:
                if f"{func}(" in formula_upper:
                    unsupported.append(
                        UnsupportedFeature(
                            feature_type="DYNAMIC_REFERENCE",
                            cell_address=node.address,
                            formula=node.formula,
                            explanation=(
                                f"{func} creates runtime references that cannot be "
                                "safely converted to static code."
                            ),
                            suggested_fix=(
                                "Replace dynamic references with explicit ranges, "
                                "or restructure data to avoid runtime cell selection."
                            ),
                        )
                    )

        if input_data.clusters:
            calculations, business_rules, test_suite = self._build_from_clusters(input_data)
        else:
            for node in input_data.nodes.values():
                if not node.formula:
                    continue
                parsed = self._parse_formula(node.formula, node.address)
                calculations.append(
                    CalculationUnit(
                        id=node.address,
                        name=node.address,
                        formulas=[parsed],
                        inputs=parsed.references,
                        outputs=[node.address],
                    )
                )
                test = self._build_test_case(node.address, parsed.references, [parsed])
                if test:
                    test_suite.append(test)

        # DISABLED: LLM enrichment causes expensive API calls and I/O deadlocks
        # business_rules = await self._enrich_with_llm(business_rules)

        return LogicExtractionResult(
            business_rules=business_rules,
            calculations=calculations,
            lookup_tables=[],
            pivot_definitions=[],
            ui_hints=[],
            unsupported_features=unsupported,
            test_suite=test_suite,
        )

    def _parse_formula(self, formula: str, address: str) -> ParsedFormula:
        functions = self._extract_functions(formula)
        references = sorted(self._extract_cell_references(formula, address))
        ast, constants = self._parse_to_ast(formula, address)
        return ParsedFormula(
            raw=formula,
            ast=ast,
            functions=functions,
            references=references,
            constants=constants,
        )

    def _extract_functions(self, formula: str) -> List[str]:
        matches = self.FUNCTION_PATTERN.findall(formula.upper())
        seen = []
        for match in matches:
            if match not in seen:
                seen.append(match)
        return seen

    def _extract_cell_references(self, formula: str, address: str) -> Set[str]:
        default_sheet = address.split("!", 1)[0]
        refs: Set[str] = set()
        for match in self.CELL_REF_PATTERN.finditer(formula):
            sheet = match.group("sheet") or default_sheet
            cell = match.group("cell")
            refs.add(f"{sheet}!{cell.replace('$', '')}")
        return refs

    def _build_ast(
        self,
        formula: str,
        functions: List[str],
        references: List[str],
    ) -> Dict[str, object]:
        operators = self.OPERATOR_PATTERN.findall(formula)
        return {
            "type": "formula",
            "functions": functions,
            "references": references,
            "operators": operators,
        }

    def _parse_to_ast(self, formula: str, address: str) -> Tuple[Dict[str, Any], List[Any]]:
        expr = formula.lstrip("=")
        tokens = self._tokenize(expr)
        ast = self._parse_expression(tokens, address)
        constants = self._collect_constants(ast)
        return ast, constants

    def _tokenize(self, expr: str) -> List[Dict[str, str]]:
        tokens: List[Dict[str, str]] = []
        for match in self.TOKEN_PATTERN.finditer(expr):
            kind = match.lastgroup
            value = match.group(kind) if kind else ""
            if kind == "ws":
                continue
            tokens.append({"type": kind or "", "value": value})
        return tokens

    def _parse_expression(self, tokens: List[Dict[str, str]], address: str) -> Dict[str, Any]:
        output: List[Dict[str, Any]] = []
        operators: List[Dict[str, str]] = []

        def precedence(op: str) -> int:
            if op in ("^",):
                return 4
            if op in ("*", "/"):
                return 3
            if op in ("+", "-", "&"):
                return 2
            if op in ("=", "<>", ">=", "<=", ">", "<"):
                return 1
            return 0

        def apply_operator(op: str):
            if op == "UNARY_MINUS":
                if not output:
                    output.append({"type": "error", "operator": "-", "reason": "missing_operand"})
                    return
                right = output.pop()
                output.append({"type": "unary", "operator": "-", "value": right})
                return
            if len(output) < 2:
                output.append({"type": "error", "operator": op, "reason": "missing_operand"})
                return
            right = output.pop()
            left = output.pop()
            output.append({"type": "binary", "operator": op, "left": left, "right": right})

        idx = 0
        last_type = None
        while idx < len(tokens):
            token = tokens[idx]
            ttype = token["type"]
            value = token["value"]

            if ttype == "number":
                output.append({"type": "number", "value": float(value)})
                last_type = "number"
            elif ttype == "string":
                output.append({"type": "string", "value": value.strip('"')})
                last_type = "string"
            elif ttype == "ref":
                output.append({"type": "reference", "value": self._normalize_reference(value, address)})
                last_type = "ref"
            elif ttype == "range":
                output.append({"type": "range", "value": self._normalize_range(value, address)})
                last_type = "range"
            elif ttype == "name":
                # function or named constant
                if idx + 1 < len(tokens) and tokens[idx + 1]["type"] == "lparen":
                    operators.append({"type": "func", "value": value})
                else:
                    output.append({"type": "name", "value": value})
                last_type = "name"
            elif ttype == "lparen":
                operators.append({"type": "lparen", "value": value})
                last_type = "lparen"
            elif ttype == "rparen":
                while operators and operators[-1]["type"] != "lparen":
                    op_token = operators.pop()
                    if op_token["type"] == "func":
                        args = self._collect_args(output)
                        output.append({"type": "function", "name": op_token["value"], "args": args})
                    else:
                        apply_operator(op_token["value"])
                if operators and operators[-1]["type"] == "lparen":
                    operators.pop()
                if operators and operators[-1]["type"] == "func":
                    op_token = operators.pop()
                    args = self._collect_args(output)
                    output.append({"type": "function", "name": op_token["value"], "args": args})
                last_type = "rparen"
            elif ttype == "comma":
                while operators and operators[-1]["type"] != "lparen":
                    op_token = operators.pop()
                    if op_token["type"] == "func":
                        break
                    apply_operator(op_token["value"])
                output.append({"type": "arg_sep"})
                last_type = "comma"
            elif ttype == "op":
                op = value
                if op == "-" and last_type in {None, "op", "lparen", "comma"}:
                    op = "UNARY_MINUS"
                while operators and operators[-1]["type"] == "op":
                    top = operators[-1]["value"]
                    if precedence(top) >= precedence(op):
                        apply_operator(operators.pop()["value"])
                    else:
                        break
                operators.append({"type": "op", "value": op})
                last_type = "op"
            idx += 1

        while operators:
            op_token = operators.pop()
            if op_token["type"] == "func":
                args = self._collect_args(output)
                output.append({"type": "function", "name": op_token["value"], "args": args})
            elif op_token["type"] == "op":
                apply_operator(op_token["value"])
        if not output:
            return {"type": "empty"}
        return output[-1]

    def _collect_args(self, output: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
        args: List[Dict[str, Any]] = []
        current: List[Dict[str, Any]] = []
        while output:
            node = output.pop()
            if node.get("type") == "arg_sep":
                if current:
                    args.append(current[-1])
                    current = []
            else:
                current.append(node)
        if current:
            args.append(current[-1])
        args.reverse()
        return args

    def _collect_constants(self, ast: Dict[str, Any]) -> List[Any]:
        constants: List[Any] = []

        def visit(node: Dict[str, Any]):
            ntype = node.get("type")
            if ntype in {"number", "string"}:
                constants.append(node.get("value"))
            elif ntype == "binary":
                visit(node.get("left", {}))
                visit(node.get("right", {}))
            elif ntype == "unary":
                visit(node.get("value", {}))
            elif ntype == "function":
                for arg in node.get("args", []):
                    visit(arg)
            elif ntype == "range":
                constants.append(node.get("value"))

        visit(ast)
        return constants

    def _normalize_reference(self, ref: str, address: str) -> str:
        ref = ref.replace("$", "")
        if "!" in ref:
            sheet, cell = ref.split("!", 1)
            return f"{sheet}!{cell}"
        default_sheet = address.split("!", 1)[0]
        return f"{default_sheet}!{ref}"

    def _normalize_range(self, ref: str, address: str) -> str:
        ref = ref.replace("$", "")
        if "!" in ref:
            sheet, rng = ref.split("!", 1)
            return f"{sheet}!{rng}"
        default_sheet = address.split("!", 1)[0]
        return f"{default_sheet}!{ref}"

    def _build_from_clusters(
        self, input_data: DependencyGraph
    ) -> tuple[List[CalculationUnit], List[BusinessRule], List[TestCase]]:
        calculations: List[CalculationUnit] = []
        business_rules: List[BusinessRule] = []
        test_suite: List[TestCase] = []
        node_map = input_data.nodes
        order_index = {addr: idx for idx, addr in enumerate(input_data.execution_order)}

        for cluster in input_data.clusters:
            members = set(cluster.inputs + cluster.outputs + cluster.intermediates)
            formulas: List[ParsedFormula] = []
            inputs: Set[str] = set()
            outputs = list(cluster.outputs)

            ordered = sorted(
                [node for node in members if node in node_map and node_map[node].formula],
                key=lambda addr: order_index.get(addr, 0),
            )
            for node_id in ordered:
                node = node_map[node_id]
                parsed = self._parse_formula(node.formula, node.address)
                if isinstance(parsed.ast, dict):
                    parsed.ast["target"] = node_id
                formulas.append(parsed)
                inputs.update(parsed.references)

            input_types, output_types = self._infer_types_for_formulas(formulas)
            calculation_id = cluster.id
            calculations.append(
                CalculationUnit(
                    id=calculation_id,
                    name=calculation_id,
                    formulas=formulas,
                    inputs=sorted(inputs),
                    outputs=outputs or ordered,
                )
            )

            pseudocode_lines = [
                f"{node_id} = {node_map[node_id].formula}"
                for node_id in ordered
                if node_map[node_id].formula
            ]
            test_case = self._build_test_case(cluster.id, sorted(inputs), formulas)
            if test_case:
                test_suite.append(test_case)
            seeded = self._build_test_case_seeded(cluster.id, sorted(inputs), formulas, 1)
            if seeded:
                test_suite.append(seeded)
            const_seed = self._seed_from_constants(formulas)
            if const_seed is not None:
                seeded_const = self._build_test_case_seeded(
                    cluster.id, sorted(inputs), formulas, const_seed
                )
                if seeded_const:
                    test_suite.append(seeded_const)
            business_rules.append(
                BusinessRule(
                    id=cluster.id,
                    name=self._humanize_cluster_name(cluster, outputs or ordered),
                    description=self._cluster_description(cluster, formulas),
                    inputs=[
                        RuleInput(name=addr, data_type=input_types.get(addr))
                        for addr in sorted(inputs)
                    ],
                    outputs=[
                        RuleOutput(name=addr, data_type=output_types.get(addr))
                        for addr in (outputs or ordered)
                    ],
                    logic=LogicRepresentation(
                        pseudocode="\n".join(pseudocode_lines),
                        typescript=self._typescript_from_ast(
                            cluster.id, sorted(inputs), formulas, outputs or ordered
                        ),
                        validation=self._validation_schema(sorted(inputs), input_types),
                    ),
                    constraints=self._constraint_hints(formulas),
                    test_cases=[test_case] if test_case else [],
                )
            )

        return calculations, business_rules, test_suite

    def _humanize_cluster_name(self, cluster: CalculationCluster, outputs: List[str]) -> str:
        base = cluster.id.replace("cluster_", "").replace("_", " ").strip()
        purpose = (cluster.semantic_purpose or "").replace("_", " ").title()
        output_hint = outputs[0] if outputs else ""
        if purpose and base:
            return f"{purpose} - {base.title()}"
        if purpose:
            return f"{purpose} Calculation"
        if base:
            return base.title()
        if output_hint:
            return output_hint
        return cluster.id

    def _cluster_description(
        self, cluster: CalculationCluster, formulas: List[ParsedFormula]
    ) -> str:
        if cluster.semantic_purpose:
            details = self._formula_keywords(formulas)
            if details:
                return f"Auto-extracted {cluster.semantic_purpose} cluster ({details})"
            return f"Auto-extracted {cluster.semantic_purpose} calculation cluster"
        return "Auto-extracted calculation cluster"

    def _typescript_stub(
        self, cluster_id: str, inputs: List[str], outputs: List[str]
    ) -> str:
        inputs_list = ", ".join([f'"{addr}"' for addr in inputs])
        outputs_list = ", ".join([f'"{addr}"' for addr in outputs])
        return "\n".join([
            f"// Cluster: {cluster_id}",
            f"// Inputs: [{inputs_list}]",
            f"// Outputs: [{outputs_list}]",
            "export function calculate(inputs: Record<string, unknown>) {",
            "  // TODO: Implement using translated formulas",
            "  return {};",
            "}",
        ])

    def _formula_keywords(self, formulas: List[ParsedFormula]) -> str:
        text = " ".join([f.raw.upper() for f in formulas])
        hints = []
        for keyword in ["TAX", "DISCOUNT", "RATE", "MARGIN", "TOTAL", "PROFIT"]:
            if keyword in text:
                hints.append(keyword.lower())
        return ", ".join(hints)

    def _constraint_hints(self, formulas: List[ParsedFormula]) -> List[str]:
        hints: List[str] = []
        text = " ".join([f.raw.upper() for f in formulas])
        for func in self.UNSUPPORTED_FUNCTIONS:
            if f"{func}(" in text:
                hints.append(f"Unsupported function: {func}")
        return hints

    def _seed_from_constants(self, formulas: List[ParsedFormula]) -> Optional[float]:
        for formula in formulas:
            for constant in formula.constants:
                if isinstance(constant, (int, float)) and constant != 0:
                    return float(constant)
        return None

    async def _enrich_with_llm(self, rules: List[BusinessRule]) -> List[BusinessRule]:
        if not rules:
            return rules
        try:
            client = LLMClient()
        except LLMError:
            return rules

        enriched: List[BusinessRule] = []
        for rule in rules:
            prompt = self._semantic_prompt(rule)
            try:
                response = await client.complete(prompt, system=self._semantic_system())
                data = self._parse_llm_json(response)
                rule.name = data.get("name") or rule.name
                rule.description = data.get("description") or rule.description
                constraints = data.get("constraints")
                if isinstance(constraints, list):
                    rule.constraints = [str(item) for item in constraints if item]
            except Exception:
                pass
            enriched.append(rule)
        return enriched

    def _semantic_system(self) -> str:
        return (
            "You are a business analyst. "
            "Return strict JSON only. "
            "No markdown or commentary."
        )

    def _semantic_prompt(self, rule: BusinessRule) -> str:
        return "\n".join([
            "Analyze this Excel-derived calculation cluster and provide a concise business-friendly name,",
            "a one-sentence description, and any constraints or caveats.",
            "",
            f"Inputs: {', '.join([inp.name for inp in rule.inputs])}",
            f"Outputs: {', '.join([out.name for out in rule.outputs])}",
            "Formulas:",
            rule.logic.pseudocode,
            "",
            "Return JSON:",
            "{",
            '  "name": "<short business name>",',
            '  "description": "<one sentence>",',
            '  "constraints": ["<constraint>", ...]',
            "}",
        ])

    def _parse_llm_json(self, response: str) -> Dict[str, Any]:
        text = response.strip()
        if text.startswith("```"):
            text = text.split("```")[1]
            if text.startswith("json"):
                text = text[4:]
        return json.loads(text)

    def _typescript_from_ast(
        self,
        cluster_id: str,
        inputs: List[str],
        formulas: List[ParsedFormula],
        outputs: List[str],
    ) -> str:
        lines = [
            f"// Cluster: {cluster_id}",
            f"// Inputs: {', '.join(inputs) if inputs else 'none'}",
            f"// Outputs: {', '.join(outputs) if outputs else 'none'}",
            "export function calculate(inputs: Record<string, unknown>) {",
        ]
        output_map: List[str] = []
        for idx, formula in enumerate(formulas):
            target = ""
            if isinstance(formula.ast, dict):
                target = str(formula.ast.get("target", ""))
            ts_expr = self._ast_to_ts(formula.ast)
            var_name = f"value_{idx}"
            if target:
                var_name = self._sanitize_var(target)
            lines.append(f"  // {formula.raw}")
            lines.append(f"  const {var_name} = {ts_expr};")
            if target:
                output_map.append(f"    \"{target}\": {var_name},")
        lines.append("  return {")
        if output_map:
            lines.extend(output_map)
        lines.append("  };")
        lines.append("}")
        return "\n".join(lines)

    def _validation_schema(self, inputs: List[str], type_map: Dict[str, str]) -> str:
        if not inputs:
            return "z.object({})"
        fields = []
        for addr in inputs:
            inferred = type_map.get(addr, "unknown")
            if inferred == "number":
                schema = "z.number()"
            elif inferred == "string":
                schema = "z.string()"
            elif inferred == "boolean":
                schema = "z.boolean()"
            elif inferred == "date":
                schema = "z.date()"
            else:
                schema = "z.any()"
            fields.append(f'"{addr}": {schema}')
        return f"z.object({{{', '.join(fields)}}})"

    def _ast_to_ts(self, node: Dict[str, Any]) -> str:
        ntype = node.get("type")
        if ntype == "number":
            return str(node.get("value"))
        if ntype == "string":
            return f"\"{node.get('value', '')}\""
        if ntype == "reference":
            return f"inputs['{node.get('value')}']"
        if ntype == "range":
            return f"rangeValues('{node.get('value')}', inputs)"
        if ntype == "name":
            return str(node.get("value"))
        if ntype == "unary":
            return f"(-{self._ast_to_ts(node.get('value', {}))})"
        if ntype == "binary":
            op = node.get("operator")
            left = self._ast_to_ts(node.get("left", {}))
            right = self._ast_to_ts(node.get("right", {}))
            if op == "&":
                op = "+"
            if op == "=":
                op = "=="
            if op == "<>":
                op = "!="
            return f"({left} {op} {right})"
        if ntype == "function":
            name = str(node.get("name", "")).lower()
            args = ", ".join([self._ast_to_ts(arg) for arg in node.get("args", [])])
            return f"{name}({args})"
        return "null"

    def _infer_types_for_formulas(
        self, formulas: List[ParsedFormula]
    ) -> tuple[Dict[str, str], Dict[str, str]]:
        input_types: Dict[str, Set[str]] = {}
        output_types: Dict[str, str] = {}

        def add_input_type(ref: str, inferred: str):
            if inferred == "unknown":
                return
            input_types.setdefault(ref, set()).add(inferred)

        def unify(a: str, b: str) -> str:
            if a == b:
                return a
            if a == "unknown":
                return b
            if b == "unknown":
                return a
            return "unknown"

        def infer_node(node: Dict[str, Any], expected: str) -> str:
            ntype = node.get("type")
            if ntype == "number":
                return "number"
            if ntype == "string":
                return "string"
            if ntype == "reference":
                ref = node.get("value")
                if expected:
                    add_input_type(ref, expected)
                return output_types.get(ref, expected or "unknown")
            if ntype == "unary":
                return infer_node(node.get("value", {}), "number")
            if ntype == "binary":
                op = node.get("operator")
                if op in {"+", "-", "*", "/", "^"}:
                    left = infer_node(node.get("left", {}), "number")
                    right = infer_node(node.get("right", {}), "number")
                    return unify(left, right)
                if op == "&":
                    infer_node(node.get("left", {}), "string")
                    infer_node(node.get("right", {}), "string")
                    return "string"
                if op in {"=", "<>", ">=", "<=", ">", "<"}:
                    infer_node(node.get("left", {}), "number")
                    infer_node(node.get("right", {}), "number")
                    return "boolean"
            if ntype == "function":
                name = str(node.get("name", "")).upper()
                args = node.get("args", [])
                if name in {"SUM", "SUMIF", "SUMIFS", "AVERAGE", "MIN", "MAX", "COUNT", "COUNTIF"}:
                    for arg in args:
                        infer_node(arg, "number")
                    return "number"
                if name in {"ROUND", "ROUNDUP", "ROUNDDOWN", "ABS"}:
                    for arg in args:
                        infer_node(arg, "number")
                    return "number"
                if name in {"DATE"}:
                    for arg in args:
                        infer_node(arg, "number")
                    return "date"
                if name in {"TODAY", "NOW"}:
                    return "date"
                if name in {"YEAR", "MONTH", "DAY"}:
                    for arg in args:
                        infer_node(arg, "date")
                    return "number"
                if name in {"CONCAT", "CONCATENATE", "TEXT", "LEFT", "RIGHT", "MID"}:
                    for arg in args:
                        infer_node(arg, "string")
                    return "string"
                if name in {"IF", "IFS"}:
                    if args:
                        infer_node(args[0], "boolean")
                    true_type = infer_node(args[1], expected) if len(args) > 1 else "unknown"
                    false_type = infer_node(args[2], expected) if len(args) > 2 else "unknown"
                    return unify(true_type, false_type)
                if name in {"VLOOKUP", "XLOOKUP", "INDEX"}:
                    for arg in args:
                        infer_node(arg, "unknown")
                    return "unknown"
                if name in {"MATCH"}:
                    for arg in args:
                        infer_node(arg, "unknown")
                    return "number"
            return "unknown"

        for formula in formulas:
            ast = formula.ast if isinstance(formula.ast, dict) else {}
            target = ast.get("target")
            inferred = infer_node(ast, "unknown")
            if target:
                output_types[target] = inferred

        flattened_inputs = {
            ref: list(types)[0] if len(types) == 1 else "unknown"
            for ref, types in input_types.items()
        }
        return flattened_inputs, output_types

    def _build_test_case(
        self, cluster_id: str, inputs: List[str], formulas: List[ParsedFormula]
    ) -> Optional[TestCase]:
        if not inputs:
            return None
        input_payload = {addr: 0 for addr in inputs}
        expected = self._evaluate_formulas(formulas, input_payload)
        return TestCase(
            name=f"{cluster_id}_default",
            inputs=input_payload,
            expected=expected,
        )

    def _build_test_case_seeded(
        self, cluster_id: str, inputs: List[str], formulas: List[ParsedFormula], seed: float
    ) -> Optional[TestCase]:
        if not inputs:
            return None
        input_payload = {addr: seed for addr in inputs}
        expected = self._evaluate_formulas(formulas, input_payload)
        return TestCase(
            name=f"{cluster_id}_seed_{seed}",
            inputs=input_payload,
            expected=expected,
        )

    def _evaluate_formulas(
        self, formulas: List[ParsedFormula], inputs: Dict[str, Any]
    ) -> Dict[str, Any]:
        context: Dict[str, Any] = {}
        for formula in formulas:
            target = ""
            if isinstance(formula.ast, dict):
                target = str(formula.ast.get("target", ""))
            value = self._evaluate_ast(formula.ast, inputs, context)
            if target:
                context[target] = value
        return context

    def _evaluate_ast(
        self, node: Dict[str, Any], inputs: Dict[str, Any], context: Dict[str, Any]
    ) -> Any:
        ntype = node.get("type")
        if ntype == "number":
            return node.get("value")
        if ntype == "string":
            return node.get("value")
        if ntype == "reference":
            ref = node.get("value")
            if ref in context:
                return context.get(ref)
            return inputs.get(ref, 0)
        if ntype == "range":
            return self._range_values(node.get("value"), inputs, context)
        if ntype == "unary":
            value = self._evaluate_ast(node.get("value", {}), inputs, context)
            return -self._coerce_number(value)
        if ntype == "binary":
            left = self._evaluate_ast(node.get("left", {}), inputs, context)
            right = self._evaluate_ast(node.get("right", {}), inputs, context)
            op = node.get("operator")
            if op in {"+", "-", "*", "/", "^"}:
                left = self._coerce_number(left)
                right = self._coerce_number(right)
            if op == "+":
                return left + right
            if op == "-":
                return left - right
            if op == "*":
                return left * right
            if op == "/":
                return left / right if right != 0 else 0
            if op == "^":
                return left ** right
            if op == "=":
                if isinstance(left, (list, str)) or isinstance(right, (list, str)):
                    left = self._coerce_number(left)
                    right = self._coerce_number(right)
                return left == right
            if op == "<>":
                if isinstance(left, (list, str)) or isinstance(right, (list, str)):
                    left = self._coerce_number(left)
                    right = self._coerce_number(right)
                return left != right
            if op == ">":
                if isinstance(left, (list, str)) or isinstance(right, (list, str)):
                    left = self._coerce_number(left)
                    right = self._coerce_number(right)
                return left > right
            if op == "<":
                if isinstance(left, (list, str)) or isinstance(right, (list, str)):
                    left = self._coerce_number(left)
                    right = self._coerce_number(right)
                return left < right
            if op == ">=":
                if isinstance(left, (list, str)) or isinstance(right, (list, str)):
                    left = self._coerce_number(left)
                    right = self._coerce_number(right)
                return left >= right
            if op == "<=":
                if isinstance(left, (list, str)) or isinstance(right, (list, str)):
                    left = self._coerce_number(left)
                    right = self._coerce_number(right)
                return left <= right
            if op == "&":
                return f"{left}{right}"
        if ntype == "function":
            name = str(node.get("name", "")).upper()
            args = [self._evaluate_ast(arg, inputs, context) for arg in node.get("args", [])]
            if name == "SUM":
                return self._sum_values(args)
            if name == "IF":
                return args[1] if len(args) > 1 and args[0] else (args[2] if len(args) > 2 else 0)
            if name == "AVERAGE":
                values = self._flatten(args)
                return sum(values) / len(values) if values else 0
            if name == "MIN":
                values = self._flatten(args)
                return min(values) if values else 0
            if name == "MAX":
                values = self._flatten(args)
                return max(values) if values else 0
            if name == "ROUND":
                value = self._coerce_number(args[0])
                digits = int(self._coerce_number(args[1])) if len(args) > 1 else 0
                return round(value, digits)
            if name == "ROUNDUP":
                value = self._coerce_number(args[0])
                digits = int(self._coerce_number(args[1])) if len(args) > 1 else 0
                factor = 10 ** digits
                return (int(value * factor + (0 if value < 0 else 0.999999)) / factor)
            if name == "ROUNDDOWN":
                value = self._coerce_number(args[0])
                digits = int(self._coerce_number(args[1])) if len(args) > 1 else 0
                factor = 10 ** digits
                return (int(value * factor) / factor)
            if name == "CONCAT" or name == "CONCATENATE":
                return "".join([str(v) for v in self._flatten(args)])
            if name == "SUMIF":
                return self._sumif(args)
            if name == "SUMIFS":
                return self._sumifs(args)
            if name == "COUNTIF":
                return self._countif(args)
            if name == "COUNTIFS":
                return self._countifs(args)
            if name == "AVERAGEIFS":
                return self._averageifs(args)
            if name == "DATE":
                if len(args) >= 3:
                    return self._excel_serial_from_date(
                        int(self._coerce_number(args[0])),
                        int(self._coerce_number(args[1])),
                        int(self._coerce_number(args[2])),
                    )
                return 0
            if name in {"YEAR", "MONTH", "DAY"}:
                value = self._coerce_number(args[0]) if args else 0
                date = self._date_from_value(value)
                if name == "YEAR":
                    return date[0]
                if name == "MONTH":
                    return date[1]
                if name == "DAY":
                    return date[2]
                return 0
            if name == "MATCH":
                return self._match(args)
            if name == "INDEX":
                return self._index(args)
            if name == "VLOOKUP":
                return self._vlookup(args)
            if name == "XLOOKUP":
                return self._xlookup(args)
        return 0

    def _sanitize_var(self, address: str) -> str:
        return "value_" + re.sub(r"[^a-zA-Z0-9_]", "_", address)

    def _flatten(self, args: List[Any]) -> List[float]:
        values: List[float] = []
        for arg in args:
            if hasattr(arg, "tolist"):
                try:
                    arg = arg.tolist()
                except Exception:
                    pass
            if isinstance(arg, (list, tuple, set)):
                values.extend(self._flatten(list(arg)))
            else:
                try:
                    values.append(float(arg))
                except Exception:
                    values.append(0.0)
        return values

    def _coerce_number(self, value: Any) -> float:
        if hasattr(value, "tolist"):
            try:
                value = value.tolist()
            except Exception:
                pass
        if isinstance(value, (list, tuple, set)):
            return float(sum(self._flatten(list(value))))
        try:
            return float(value)
        except Exception:
            return 0.0

    def _sum_values(self, args: List[Any]) -> float:
        return sum(self._flatten(args))

    def _range_values(
        self, range_ref: Optional[str], inputs: Dict[str, Any], context: Dict[str, Any]
    ) -> List[Any]:
        if not range_ref:
            return []
        try:
            sheet, rng = range_ref.split("!", 1)
        except ValueError:
            return []
        try:
            start, end = rng.split(":")
        except ValueError:
            return []
        addresses = self._expand_range(sheet, start, end)
        values = []
        for addr in addresses:
            if addr in context:
                values.append(context[addr])
            else:
                values.append(inputs.get(addr, 0))
        return values

    def _expand_range(self, sheet: str, start: str, end: str) -> List[str]:
        def col_to_idx(col: str) -> int:
            value = 0
            for ch in col:
                value = value * 26 + (ord(ch.upper()) - 64)
            return value

        def idx_to_col(idx: int) -> str:
            result = ""
            while idx > 0:
                idx, rem = divmod(idx - 1, 26)
                result = chr(65 + rem) + result
            return result

        start_col = re.match(r"[A-Z]+", start.upper())
        end_col = re.match(r"[A-Z]+", end.upper())
        start_row = int(re.sub(r"[^0-9]", "", start))
        end_row = int(re.sub(r"[^0-9]", "", end))
        if not start_col or not end_col:
            return []
        min_col = col_to_idx(start_col.group(0))
        max_col = col_to_idx(end_col.group(0))
        min_row = min(start_row, end_row)
        max_row = max(start_row, end_row)
        addresses = []
        for row in range(min_row, max_row + 1):
            for col in range(min_col, max_col + 1):
                addresses.append(f"{sheet}!{idx_to_col(col)}{row}")
        return addresses

    def _matches_criteria(self, value: Any, criteria: Any) -> bool:
        if criteria is None:
            return False
        if isinstance(criteria, (int, float)):
            return float(value) == float(criteria)
        crit = str(criteria)
        match = re.match(r"^(>=|<=|<>|=|>|<)(.*)$", crit)
        if match:
            op, rhs = match.groups()
            try:
                lhs_val = float(value)
                rhs_val = float(rhs)
            except Exception:
                lhs_val = str(value)
                rhs_val = rhs
            if op == ">":
                return lhs_val > rhs_val
            if op == "<":
                return lhs_val < rhs_val
            if op == ">=":
                return lhs_val >= rhs_val
            if op == "<=":
                return lhs_val <= rhs_val
            if op == "<>":
                return lhs_val != rhs_val
            return lhs_val == rhs_val
        return str(value) == crit

    def _sumif(self, args: List[Any]) -> float:
        if len(args) < 2:
            return 0.0
        range_vals = self._flatten([args[0]])
        criteria = args[1]
        sum_vals = self._flatten([args[2]]) if len(args) > 2 else range_vals
        total = 0.0
        for idx, val in enumerate(range_vals):
            if self._matches_criteria(val, criteria):
                total += sum_vals[idx] if idx < len(sum_vals) else 0.0
        return total

    def _sumifs(self, args: List[Any]) -> float:
        if len(args) < 3:
            return 0.0
        sum_vals = self._flatten([args[0]])
        criteria_pairs = args[1:]
        total = 0.0
        for idx, sum_val in enumerate(sum_vals):
            matches = True
            for i in range(0, len(criteria_pairs), 2):
                if i + 1 >= len(criteria_pairs):
                    break
                range_vals = self._flatten([criteria_pairs[i]])
                criteria = criteria_pairs[i + 1]
                if idx >= len(range_vals) or not self._matches_criteria(range_vals[idx], criteria):
                    matches = False
                    break
            if matches:
                total += sum_val
        return total

    def _countifs(self, args: List[Any]) -> float:
        if len(args) < 2:
            return 0.0
        criteria_pairs = args
        max_len = 0
        ranges: List[List[float]] = []
        criteria: List[Any] = []
        for i in range(0, len(criteria_pairs), 2):
            if i + 1 >= len(criteria_pairs):
                break
            range_vals = self._flatten([criteria_pairs[i]])
            ranges.append(range_vals)
            criteria.append(criteria_pairs[i + 1])
            max_len = max(max_len, len(range_vals))
        total = 0.0
        for idx in range(max_len):
            matches = True
            for r_idx, range_vals in enumerate(ranges):
                if idx >= len(range_vals) or not self._matches_criteria(range_vals[idx], criteria[r_idx]):
                    matches = False
                    break
            if matches:
                total += 1.0
        return total

    def _averageifs(self, args: List[Any]) -> float:
        if len(args) < 3:
            return 0.0
        sum_vals = self._flatten([args[0]])
        criteria_pairs = args[1:]
        total = 0.0
        count = 0
        for idx, sum_val in enumerate(sum_vals):
            matches = True
            for i in range(0, len(criteria_pairs), 2):
                if i + 1 >= len(criteria_pairs):
                    break
                range_vals = self._flatten([criteria_pairs[i]])
                criteria = criteria_pairs[i + 1]
                if idx >= len(range_vals) or not self._matches_criteria(range_vals[idx], criteria):
                    matches = False
                    break
            if matches:
                total += sum_val
                count += 1
        return total / count if count else 0.0

    def _countif(self, args: List[Any]) -> float:
        if len(args) < 2:
            return 0.0
        range_vals = self._flatten([args[0]])
        criteria = args[1]
        return float(sum(1 for val in range_vals if self._matches_criteria(val, criteria)))

    def _match(self, args: List[Any]) -> float:
        if len(args) < 2:
            return 0.0
        lookup = args[0]
        values = self._flatten([args[1]])
        if lookup in values:
            return float(values.index(lookup) + 1)
        return 0.0

    def _index(self, args: List[Any]) -> Any:
        if len(args) < 2:
            return 0
        values = self._flatten([args[0]])
        row = int(self._coerce_number(args[1])) - 1
        if row < 0 or row >= len(values):
            return 0
        return values[row]

    def _vlookup(self, args: List[Any]) -> Any:
        if len(args) < 3:
            return 0
        lookup = args[0]
        table = args[1]
        col_index = int(args[2]) - 1
        if not isinstance(table, list):
            return 0
        for row in table:
            if isinstance(row, list) and row and row[0] == lookup:
                return row[col_index] if col_index < len(row) else 0
        return 0

    def _xlookup(self, args: List[Any]) -> Any:
        if len(args) < 3:
            return 0
        lookup = args[0]
        lookup_array = self._flatten([args[1]])
        return_array = self._flatten([args[2]])
        not_found = args[3] if len(args) > 3 else 0
        match_mode = (
            int(self._coerce_number(args[4]))
            if len(args) > 4 and str(args[4]).strip() != ""
            else 0
        )
        search_mode = (
            int(self._coerce_number(args[5]))
            if len(args) > 5 and str(args[5]).strip() != ""
            else 1
        )

        indices = range(len(lookup_array))
        if search_mode == -1:
            indices = range(len(lookup_array) - 1, -1, -1)

        if match_mode == 0:
            for idx in indices:
                if lookup_array[idx] == lookup:
                    return return_array[idx] if idx < len(return_array) else not_found
            return not_found

        if match_mode == -1:
            best_idx = None
            best_val = None
            for idx in indices:
                val = lookup_array[idx]
                if val <= lookup and (best_val is None or val > best_val):
                    best_val = val
                    best_idx = idx
            if best_idx is not None:
                return return_array[best_idx] if best_idx < len(return_array) else not_found
            return not_found

        if match_mode == 1:
            best_idx = None
            best_val = None
            for idx in indices:
                val = lookup_array[idx]
                if val >= lookup and (best_val is None or val < best_val):
                    best_val = val
                    best_idx = idx
            if best_idx is not None:
                return return_array[best_idx] if best_idx < len(return_array) else not_found
            return not_found

        return not_found

    def _excel_serial_from_date(self, year: int, month: int, day: int) -> float:
        if month <= 0:
            month = 1
        if day <= 0:
            day = 1
        if month > 12:
            month = 12
        from datetime import date
        base = date(1899, 12, 30)
        target = date(year, month, day)
        delta = (target - base).days
        if target >= date(1900, 3, 1):
            delta += 1  # Excel's fake 1900-02-29
        return float(delta)

    def _date_from_serial(self, serial: float) -> Tuple[int, int, int]:
        from datetime import date, timedelta
        base = date(1899, 12, 30)
        serial_int = int(serial)
        if serial_int >= 60:
            serial_int -= 1
        target = base + timedelta(days=serial_int)
        return target.year, target.month, target.day

    def _date_from_value(self, value: Any) -> Tuple[int, int, int]:
        if isinstance(value, (int, float)):
            return self._date_from_serial(float(value))
        if isinstance(value, str):
            parts = value.strip().split("T")[0].split("-")
            if len(parts) >= 3:
                try:
                    return int(parts[0]), int(parts[1]), int(parts[2])
                except Exception:
                    return (1900, 1, 1)
        return (1900, 1, 1)
