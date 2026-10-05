#!/usr/bin/env python3
"""Validate and render a developer request without writes or network access."""
import argparse
import json
import re
import sys
from pathlib import Path

SCHEMA = Path(__file__).resolve().parent.parent / "guides" / "developer-request.schema.json"


def schema_errors(value, schema, path="$request"):
    """Evaluate the JSON Schema keywords used by the owning schema (stdlib only)."""
    errors = []
    types = {
        "object": lambda v: isinstance(v, dict),
        "array": lambda v: isinstance(v, list),
        "string": lambda v: isinstance(v, str),
        "boolean": lambda v: isinstance(v, bool),
        "integer": lambda v: isinstance(v, int) and not isinstance(v, bool),
    }
    if "type" in schema and not types[schema["type"]](value):
        return [path + ": expected " + schema["type"]]
    if "const" in schema and (type(value) is not type(schema["const"]) or value != schema["const"]):
        errors.append(path + ": must equal " + json.dumps(schema["const"]))
    if "enum" in schema and value not in schema["enum"]:
        errors.append(path + ": must be one of " + ", ".join(map(str, schema["enum"])))
    if isinstance(value, dict):
        for field in schema.get("required", []):
            if field not in value:
                errors.append(path + "." + field + ": required")
        properties = schema.get("properties", {})
        for field, child in value.items():
            if field in properties:
                errors.extend(schema_errors(child, properties[field], path + "." + field))
            elif schema.get("additionalProperties") is False:
                errors.append(path + "." + field + ": unknown field")
    if isinstance(value, list):
        if len(value) < schema.get("minItems", 0):
            errors.append(path + ": needs at least " + str(schema["minItems"]) + " items")
        if "maxItems" in schema and len(value) > schema["maxItems"]:
            errors.append(path + ": permits at most " + str(schema["maxItems"]) + " items")
        if "items" in schema:
            for index, child in enumerate(value):
                errors.extend(schema_errors(child, schema["items"], path + "[" + str(index) + "]"))
    if isinstance(value, str):
        if len(value) < schema.get("minLength", 0) or ("pattern" in schema and not re.search(schema["pattern"], value)):
            errors.append(path + ": must be non-empty text")
    for child in schema.get("allOf", []):
        errors.extend(schema_errors(value, child, path))
    if "if" in schema and not schema_errors(value, schema["if"], path):
        errors.extend(schema_errors(value, schema.get("then", {}), path))
    if "not" in schema and not schema_errors(value, schema["not"], path):
        errors.append(path + ": field is not allowed for this request kind or combination")
    if "oneOf" in schema and sum(not schema_errors(value, child, path) for child in schema["oneOf"]) != 1:
        errors.append(path + ": supply exactly one of intentBasis or intentBasisUnavailableReason")
    return errors


def validate_request(request):
    schema = json.loads(SCHEMA.read_text(encoding="utf-8"))
    if not isinstance(request, dict):
        return request, ["$request: expected object"]
    required = set(schema["required"])
    normalized = {key: value for key, value in request.items()
                  if key not in schema["properties"] or key in required or value not in (None, "", [], {})}
    errors = schema_errors(normalized, schema)
    options = normalized.get("options")
    recommendation = normalized.get("recommendation")
    if isinstance(options, list):
        labels = [option.get("label") for option in options if isinstance(option, dict) and isinstance(option.get("label"), str)]
        if len(labels) != len(set(labels)):
            errors.append("$request.options: labels must be unique")
        if isinstance(recommendation, dict) and recommendation.get("option") not in labels:
            errors.append("$request.recommendation.option: must name an option label exactly")
    elif recommendation is not None:
        errors.append("$request.recommendation: requires options")
    return normalized, errors


def literal_strings(value):
    """Keep supplied text literal in Markdown, including every newline."""
    if isinstance(value, str):
        lines = value.replace("\r\n", "\n").replace("\r", "\n").split("\n")
        escaped = []
        for line in lines:
            line = re.sub(r"([\\`*_\[\]<>|])", r"\\\1", line)
            line = re.sub(r"~{3,}", lambda match: "\\~" * len(match[0]), line)
            line = re.sub(r"^([ \t]*)([#\-+])", r"\1\\\2", line)
            line = re.sub(r"^([ \t]*[0-9]+)\.", r"\1\\.", line)
            # A literal prefix prevents supplied indentation becoming a code block.
            if line.startswith("    ") or line.startswith("\t"):
                line = "\\" + line
            escaped.append(line)
        return "  \n".join(escaped)
    if isinstance(value, list):
        return [literal_strings(child) for child in value]
    if isinstance(value, dict):
        return {key: literal_strings(child) for key, child in value.items()}
    return value


def render_request(request):
    request = literal_strings(request)
    lines = ["## Developer " + request["kind"] + ": " + request["title"], "", request["question"], "", "**Context:** " + request["context"]]
    for field, label in (("acceptance", "Accepting"), ("needed", "Needed"), ("requiredAction", "Required action")):
        if field in request:
            lines.extend(["", "**" + label + ":** " + request[field]])
    lines.extend(["", "**Intent basis (primary):**"])
    if "intentBasis" in request:
        for basis in request["intentBasis"]:
            lines.append("- " + basis["source"] + " — " + basis["reference"] + ": " + basis["relevance"])
    else:
        lines.append("None available or applicable: " + request["intentBasisUnavailableReason"])
    if "options" in request:
        lines.extend(["", "**Options:**"])
        for option in request["options"]:
            lines.extend(["", "### " + option["label"], "- Strengths: " + "; ".join(option["strengths"]), "- Weaknesses: " + "; ".join(option["weaknesses"]), "- Downstream: " + option["downstream"]])
    if "recommendation" in request:
        recommendation = request["recommendation"]
        lines.extend(["", "**Recommendation:** " + recommendation["option"] + " — " + recommendation["rationale"]])
    if "maintainability" in request:
        lines.extend(["", "**Maintainability (secondary):** " + request["maintainability"]])
    lines.extend(["", "**Blocking:** " + ("Yes — work cannot continue without the developer's action." if request["blocking"] else "No — work can continue independently.")])
    return "\n".join(lines) + "\n"


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    inputs = parser.add_mutually_exclusive_group(required=True)
    inputs.add_argument("--request", help="JSON request object; no file is read")
    inputs.add_argument("--stdin", action="store_true", help="Read the JSON request object from standard input")
    args = parser.parse_args()
    try:
        request = json.loads(sys.stdin.read() if args.stdin else args.request)
        normalized, errors = validate_request(request)
    except (ValueError, OSError) as error:
        print("Developer request: " + str(error), file=sys.stderr)
        return 1
    if errors:
        print("\n".join(errors), file=sys.stderr)
        return 1
    print(render_request(normalized), end="")
    return 0


if __name__ == "__main__":
    sys.exit(main())
