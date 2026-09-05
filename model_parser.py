from __future__ import annotations

import math
import re
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Iterable

TIME_NAMES = {"initial time", "final time", "time step", "saveper"}
UNSUPPORTED_EXTERNAL_PATTERNS = (
    "GET XLS DATA",
    "GET XLS CONSTANTS",
    "GET DIRECT DATA",
    "GET DIRECT CONSTANTS",
    "GET VDF",
)


@dataclass
class VariableMeta:
    name: str
    label: str
    unit: str
    default: float | None = None
    min: float | None = None
    max: float | None = None
    step: float | None = None

    def to_dict(self) -> dict:
        return asdict(self)


@dataclass
class ParsedModel:
    name: str
    inputs: list[VariableMeta]
    outputs: list[VariableMeta]
    time: dict


def _strip_sketch(text: str) -> str:
    marker = r"\\\---///"
    return text.split(marker, 1)[0] if marker in text else text


def _entries(text: str) -> Iterable[tuple[str, str, str]]:
    """Yield equation, unit, and comment from Vensim records."""
    core = _strip_sketch(text)
    for raw in core.split("|"):
        if "=" not in raw or raw.lstrip().startswith(":"):
            continue
        parts = raw.split("~")
        equation = parts[0].strip()
        unit = parts[1].strip() if len(parts) > 1 else ""
        comment = parts[2].strip() if len(parts) > 2 else ""
        if equation:
            yield equation, unit, comment


def _split_equation(equation: str) -> tuple[str, str] | None:
    if "=" not in equation:
        return None
    left, right = equation.split("=", 1)
    name = " ".join(left.replace("\n", " ").split()).strip()
    name = re.sub(r"^\{[^}]+\}\s*", "", name).strip()
    expr = " ".join(right.replace("\n", " ").split()).strip()
    if not name or not expr:
        return None
    return name, expr


def _numeric(expr: str) -> float | None:
    cleaned = expr.strip()
    if re.fullmatch(r"[-+]?(?:\d+(?:\.\d*)?|\.\d+)(?:[Ee][-+]?\d+)?", cleaned):
        try:
            return float(cleaned)
        except ValueError:
            return None
    return None


def _annotation_value(comment: str, key: str) -> str | None:
    pattern = rf"\b{re.escape(key)}\s*=\s*(?:\"([^\"]+)\"|'([^']+)'|([^\s@]+))"
    match = re.search(pattern, comment, flags=re.IGNORECASE)
    if not match:
        return None
    return next((group for group in match.groups() if group is not None), None)


def _label(comment: str, fallback: str) -> str:
    return _annotation_value(comment, "label") or fallback


def _smart_range(value: float) -> tuple[float, float, float]:
    if value == 0:
        return -1.0, 1.0, 0.02

    magnitude = abs(value)
    if value > 0:
        lo, hi = 0.0, value * 2.0
    else:
        lo, hi = value * 2.0, 0.0

    span = hi - lo
    raw_step = span / 100.0
    if raw_step <= 0:
        raw_step = magnitude / 100.0 or 0.01

    power = 10 ** math.floor(math.log10(raw_step)) if raw_step > 0 else 0.01
    step = round(raw_step / power, 1) * power
    return lo, hi, max(step, power / 10)


def parse_model_text(text: str, filename: str = "model.mdl") -> ParsedModel:
    upper = text.upper()
    external_hits = [pattern for pattern in UNSUPPORTED_EXTERNAL_PATTERNS if pattern in upper]
    if external_hits:
        raise ValueError(
            "This educational version accepts self-contained .mdl files only. "
            "External data references were found: " + ", ".join(external_hits)
        )

    variables: list[dict] = []
    time_values: dict[str, float] = {}

    for equation, unit, comment in _entries(text):
        split = _split_equation(equation)
        if not split:
            continue

        name, expr = split
        clean_name = name.strip('"')
        lower_name = clean_name.lower()
        value = _numeric(expr)

        if lower_name in TIME_NAMES and value is not None:
            time_values[lower_name] = value

        variables.append(
            {
                "name": clean_name,
                "expr": expr,
                "unit": unit,
                "comment": comment,
                "numeric": value,
                "is_stock": bool(re.search(r"\bINTEG\s*\(", expr, flags=re.IGNORECASE)),
                "tag_input": bool(re.search(r"@input\b", comment, flags=re.IGNORECASE)),
                "tag_output": bool(re.search(r"@output\b", comment, flags=re.IGNORECASE)),
            }
        )

    tagged_inputs = [variable for variable in variables if variable["tag_input"]]
    if tagged_inputs:
        input_vars = tagged_inputs[:12]
    else:
        input_vars = [
            variable
            for variable in variables
            if variable["numeric"] is not None and variable["name"].lower() not in TIME_NAMES
        ][:8]

    inputs: list[VariableMeta] = []
    for variable in input_vars:
        default = variable["numeric"]
        if default is None:
            continue

        auto_min, auto_max, auto_step = _smart_range(default)
        min_value = float(_annotation_value(variable["comment"], "min") or auto_min)
        max_value = float(_annotation_value(variable["comment"], "max") or auto_max)
        step_value = float(_annotation_value(variable["comment"], "step") or auto_step)

        if max_value <= min_value:
            raise ValueError(
                f"Invalid slider range for '{variable['name']}': max must be greater than min."
            )
        if step_value <= 0:
            raise ValueError(f"Invalid slider step for '{variable['name']}': step must be positive.")

        inputs.append(
            VariableMeta(
                name=variable["name"],
                label=_label(variable["comment"], variable["name"]),
                unit=variable["unit"],
                default=default,
                min=min_value,
                max=max_value,
                step=step_value,
            )
        )

    tagged_outputs = [variable for variable in variables if variable["tag_output"]]
    if tagged_outputs:
        output_vars = tagged_outputs[:6]
    else:
        stocks = [variable for variable in variables if variable["is_stock"]]
        output_vars = stocks[:4]
        if not output_vars:
            input_names = {item.name for item in inputs}
            output_vars = [
                variable
                for variable in variables
                if variable["name"] not in input_names and variable["name"].lower() not in TIME_NAMES
            ][:4]

    outputs = [
        VariableMeta(
            name=variable["name"],
            label=_label(variable["comment"], variable["name"]),
            unit=variable["unit"],
        )
        for variable in output_vars
    ]

    if not outputs:
        raise ValueError(
            "No plottable variables were found. Add @output to at least one variable comment."
        )

    initial = time_values.get("initial time", 0.0)
    final = time_values.get("final time", initial + 100.0)
    step = time_values.get("time step", 1.0)
    if final <= initial:
        raise ValueError("FINAL TIME must be greater than INITIAL TIME.")
    if step <= 0:
        raise ValueError("TIME STEP must be positive.")

    time_unit = ""
    for variable in variables:
        if variable["name"].lower() == "initial time":
            time_unit = variable["unit"]
            break

    return ParsedModel(
        name=Path(filename).stem.replace("_", " ").replace("-", " ").strip().title(),
        inputs=inputs,
        outputs=outputs,
        time={"initial": initial, "final": final, "step": step, "unit": time_unit},
    )
