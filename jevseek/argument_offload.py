"""No-model arguments only when a reviewed schema subset fixes every value.

This is deterministic code, not a Jev semantic prediction. Optional/free fields,
unknown constraints and reference schemas keep the original model path. No I/O,
source truncation, authorization or execution happens here.
"""
from __future__ import annotations
from copy import deepcopy
import json
from jsonschema import Draft202012Validator

VERSION = 'schema-determined-arguments-v1'
_MISSING = object()
_ANNOTATIONS = {'title', 'description', 'default', 'examples', '$comment',
                'deprecated', 'readOnly', 'writeOnly'}
_ALLOWED = _ANNOTATIONS | {'type', 'properties', 'required', 'additionalProperties',
                          'enum', 'const', 'items', 'minItems', 'maxItems',
                          'minimum', 'maximum', 'minLength', 'maxLength', 'pattern', 'anyOf'}


def _canonical(value):
    return json.dumps(value, sort_keys=True, ensure_ascii=False,
                      separators=(',', ':'), allow_nan=False)


def _supported(schema):
    def visit(node, depth=0):
        if depth > 12 or not isinstance(node, dict) or set(node) - _ALLOWED:
            return False
        if 'properties' in node:
            if not isinstance(node['properties'], dict):
                return False
            if not all(visit(child, depth + 1) for child in node['properties'].values()):
                return False
        if 'items' in node and not visit(node['items'], depth + 1):
            return False
        if 'anyOf' in node and not all(visit(child, depth + 1) for child in node['anyOf']):
            return False
        return True

    try:
        if len(_canonical(schema).encode('utf-8')) > 16000 or not visit(schema):
            return False
        Draft202012Validator.check_schema(schema)
        return True
    except Exception:
        # Never resolve references or leak schema/credential data into diagnostics.
        return False


def _unique(schema):
    validator = Draft202012Validator(schema)
    if 'const' in schema:
        values = [schema['const']]
    elif 'enum' in schema:
        values = schema['enum']
    elif schema.get('type') == 'null':
        values = [None]
    else:
        values = None
    if values is not None:
        # JSON keys distinguish false from 0; Python set/equality would not.
        candidates = {_canonical(v): v for v in values if validator.is_valid(v)}
        return deepcopy(next(iter(candidates.values()))) if len(candidates) == 1 else _MISSING
    if schema.get('type') == 'object' and schema.get('additionalProperties') is False:
        props = schema.get('properties', {})
        if set(schema.get('required', [])) != set(props):
            return _MISSING  # An optional value may still have been requested.
        result = {}
        for name, child in props.items():
            value = _unique(child)
            if value is _MISSING:
                return _MISSING
            result[name] = value
        if validator.is_valid(result):
            return result
    return _MISSING


def unique_arguments(schema):
    """Return the fixed argument object, otherwise None (call the model).

    This does not decide whether the tool should run: existing Jev routing and
    execution safeguards retain that responsibility. No defaults are inferred.
    """
    if not _supported(schema):
        return None
    result = _unique(schema)
    return result if isinstance(result, dict) else None
