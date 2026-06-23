"""Constraints for the model's output: a GBNF grammar (llama.cpp/ik_llama) and a JSON schema
(Anthropic/BYOK), plus a compact human-readable schema hint for the prompt.

v1 ships a coarse "valid JSON object" GBNF — it guarantees parseable JSON, and `change_set.py`'s
strict validator does the fine-grained op checking. The strong form (a GBNF generated from the
*language's own* POS / morph-type / headword inventories so the model can only emit valid symbols) is
a fast-follow; see the design doc.
"""

from __future__ import annotations

from .change_set import OP_TYPES

# Standard compact JSON grammar (after llama.cpp's json.gbnf). Constrains decoding to any JSON value;
# we request an object. Fine-grained shape is enforced by validate_change_set().
_JSON_GBNF = r"""
root   ::= object
value  ::= object | array | string | number | ("true" | "false" | "null") ws
object ::= "{" ws ( string ":" ws value ("," ws string ":" ws value)* )? "}" ws
array  ::= "[" ws ( value ("," ws value)* )? "]" ws
string ::= "\"" ( [^"\\\x7F\x00-\x1F] | "\\" (["\\bfnrt/] | "u" [0-9a-fA-F]{4}) )* "\"" ws
number ::= ("-"? ([0-9] | [1-9] [0-9]{0,15})) ("." [0-9]+)? ([eE] [-+]? [0-9]+)? ws
ws     ::= [ \t\n]{0,64}
""".strip()


def change_set_gbnf() -> str:
    """GBNF constraining output to a JSON value (object). Pass via the openai_compat `grammar` kwarg."""
    return _JSON_GBNF


def change_set_json_schema() -> dict:
    """JSON schema for `{"ops": [...]}`. Used on the Anthropic/BYOK path (`json_schema`).

    Permissive on per-op fields (validated precisely downstream); enumerates the op vocabulary so the
    model is steered to valid op types.
    """
    return {
        "type": "object",
        "properties": {
            "ops": {
                "type": "array",
                "items": {
                    "type": "object",
                    "properties": {
                        "op": {"type": "string", "enum": sorted(OP_TYPES)},
                        "rationale": {"type": "string"},
                        "confidence": {"type": "number"},
                    },
                    "required": ["op"],
                },
            }
        },
        "required": ["ops"],
    }


def schema_hint() -> str:
    """A compact, deterministic description of the op vocabulary to embed in the prompt."""
    lines = ["Emit ONLY a JSON object: {\"ops\": [ ... ]}. Each op is one of:"]
    for op_type in sorted(OP_TYPES):
        required = ", ".join(OP_TYPES[op_type])
        lines.append(f'  - {{"op": "{op_type}", {_req_hint(required)}}}')
    lines.append('Optional on any op: "rationale" (str), "confidence" (0..1), "impact", "provenance".')
    lines.append("Emit nothing but the JSON object — no prose, no code fences.")
    return "\n".join(lines)


def _req_hint(required: str) -> str:
    return ", ".join(f'"{f}": ...' for f in required.split(", ") if f)
