import re
import json
import rich as r
import Engine.state as state
from Engine.blocks import BUILTIN_HANDLERS

# ─── Return Signal ────────────────────────────────────────────────────────────

class ReturnValue:
    """Wraps a function's return value so it doesn't accidentally stop callers."""
    def __init__(self, value):
        self.value = value

# ─── Value Helpers ────────────────────────────────────────────────────────────

def _parse_placeholder(raw):
    """
    Parse a placeholder expression into (name, args).

    Formats:
      "func name"                  -> ("func name", None)
      "func name [arg1, arg2]"     -> ("func name", ["arg1", "arg2"])
      "func name [\"KEY_RIGHT\"]"  -> ("func name", ["KEY_RIGHT"])
    """
    raw = raw.strip()
    m = re.match(r'^(.*?)\s*\[(.+)\]\s*$', raw, re.DOTALL)
    if m:
        name = m.group(1).strip()
        try:
            args = json.loads('[' + m.group(2) + ']')
        except Exception:
            args = [a.strip().strip('"').strip("'") for a in m.group(2).split(',')]
        return name, args
    return raw, None


def _resolve_placeholder(raw, local_vars, all_functions):
    """
    Resolve a placeholder expression to a value, with optional args.

    Lookup order:
      1. local_vars / state.variables  (no args — just a variable read)
      2. all_functions  (user-defined function call)
      3. BUILTIN_HANDLERS (built-in block call)
    """
    name, args = _parse_placeholder(raw)

    # Variable lookup (only when no args supplied)
    if args is None:
        merged = {**state.variables, **local_vars}
        if name in merged:
            return merged[name]

    # User-defined function
    if all_functions and name in all_functions:
        result = call_function(name, args, all_functions, local_vars)
        return result if result is not None else ""

    # Built-in handler
    if name in BUILTIN_HANDLERS:
        result = BUILTIN_HANDLERS[name](args, all_functions or {}, local_vars)
        if isinstance(result, ReturnValue):
            result = result.value
        return result if result is not None else ""

    return None   # unresolved


def resolve_value(val, local_vars, all_functions=None):
    """
    Substitute placeholders in strings.

    Two syntaxes are supported:
      {single_word}                    — single-word variable / function  (original)
      $(name)                          — multi-word name, no args          (new)
      $(name [arg1, arg2])             — multi-word name with args         (new)

    Lookup order: local_vars -> state.variables -> all_functions -> BUILTIN_HANDLERS.
    """
    if not isinstance(val, str):
        return val

    # ── 1. Resolve $(...)  placeholders first ────────────────────────────────
    def replace_multiword(m):
        result = _resolve_placeholder(m.group(1), local_vars, all_functions)
        return str(result) if result is not None else m.group(0)

    val = re.sub(r'\$\(([^)]+)\)', replace_multiword, val)

    # ── 2. Resolve {single_word} placeholders ────────────────────────────────
    merged = {**state.variables, **local_vars}

    for name in re.findall(r'\{(\w+)\}', val):
        if name not in merged:
            result = _resolve_placeholder(name, local_vars, all_functions)
            if result is not None:
                merged[name] = result

    try:
        return val.format(**merged)
    except (KeyError, ValueError):
        return val


def _coerce(v):
    """If a resolved value is a string that looks like a number, convert it."""
    if not isinstance(v, str):
        return v
    try:
        return int(v)
    except ValueError:
        pass
    try:
        return float(v)
    except ValueError:
        pass
    return v


def resolve_args(val, local_vars, all_functions=None):
    """Resolve placeholders in a value that may be a list or a scalar.
    Strings that resolve to numbers are coerced to int/float automatically.
    """
    if isinstance(val, list):
        return [_coerce(resolve_value(v, local_vars, all_functions)) for v in val]
    return _coerce(resolve_value(val, local_vars, all_functions))


def eval_condition(condition, local_vars, all_functions=None):
    """
    Evaluate a condition string. Both {single_word} and $(name [args])
    placeholders are expanded before eval().
    """
    def replace_multiword(m):
        result = _resolve_placeholder(m.group(1), local_vars, all_functions)
        return str(result) if result is not None else m.group(0)

    condition = re.sub(r'\$\(([^)]+)\)', replace_multiword, condition)

    merged = {**state.variables, **local_vars}

    for name in re.findall(r'\{(\w+)\}', condition):
        if name not in merged:
            result = _resolve_placeholder(name, local_vars, all_functions)
            if result is not None:
                merged[name] = result

    try:
        return bool(eval(condition.format(**merged), {}, merged))
    except Exception as e:
        r.print(f"[red]ERROR evaluating condition '{condition}': {e}[/red]")
        return False

# ─── Function Registry ────────────────────────────────────────────────────────

def get_functions(data_block, include_begin=False):
    """Return all callable function definitions from a data block."""
    skip = set(state.RESERVED_TOP)
    if include_begin:
        skip.discard("begin")
    return {
        key: val
        for key, val in data_block.items()
        if isinstance(val, list) and key not in skip
    }

# ─── Execution Engine ─────────────────────────────────────────────────────────

def call_function(func_name, args, all_functions, local_vars):
    """Look up and execute a named function, binding any declared parameters."""
    if func_name not in all_functions:
        r.print(f"[red]ERROR: Function '{func_name}' not found.[/red]")
        return None

    body = all_functions[func_name]

    # Collect parameter declarations at the top of the function body
    param_names  = []
    action_start = 0
    for i, item in enumerate(body):
        if isinstance(item, dict) and "param" in item:
            raw = item["param"]
            param_names  = [p.split(":")[0] for p in raw] if isinstance(raw, list) else []
            action_start = i + 1
        elif isinstance(item, list):
            action_start = i + 1
        else:
            action_start = i
            break

    func_locals = dict(local_vars)
    if isinstance(args, list):
        for i, name in enumerate(param_names):
            if i < len(args):
                func_locals[name] = args[i]
    elif args is not None and param_names:
        func_locals[param_names[0]] = args

    result = run_actions(body[action_start:], all_functions, func_locals)

    if isinstance(result, ReturnValue):
        return result.value
    return None


def dispatch_action(action, all_functions, local_vars):
    """Run an action that may be a list of steps, a single dict, or a bare string."""
    if isinstance(action, list):
        return run_actions(action, all_functions, local_vars)
    if isinstance(action, dict):
        return run_actions([action], all_functions, local_vars)
    if isinstance(action, str):
        if "." in action:
            obj_name, func_name = action.split(".", 1)
            if obj_name in state.loaded_objects:
                obj        = state.loaded_objects[obj_name]
                merged_fns = {**all_functions, **obj["functions"]}
                return call_function(func_name, None, merged_fns, local_vars)
        if action in all_functions:
            return call_function(action, None, all_functions, local_vars)
        return resolve_value(action, local_vars, all_functions)
    return None


def run_actions(actions, all_functions, local_vars=None):
    """Execute a list of action dicts, stopping early only on ReturnValue or __exit__."""
    if local_vars is None:
        local_vars = {}

    for action in actions:

        # Bare string -> check for object method call first, then regular function
        if isinstance(action, str):
            if "." in action:
                obj_name, func_name = action.split(".", 1)
                if obj_name in state.loaded_objects:
                    obj        = state.loaded_objects[obj_name]
                    merged_fns = {**all_functions, **obj["functions"]}
                    result     = call_function(func_name, None, merged_fns, local_vars)
                    if result == "__exit__":
                        return "__exit__"
                    continue
                else:
                    r.print(f"[red]ERROR: Object '{obj_name}' not loaded.[/red]")
                    continue
            result = call_function(action, None, all_functions, local_vars)
            if result == "__exit__":
                return "__exit__"
            continue

        if not isinstance(action, dict):
            continue

        for key, val in action.items():

            if key in BUILTIN_HANDLERS:
                result = BUILTIN_HANDLERS[key](val, all_functions, local_vars)
                if isinstance(result, ReturnValue) or result == "__exit__":
                    return result
                break   # one key per action dict is enough

            if "." in key:
                obj_name, func_name = key.split(".", 1)
                if obj_name not in state.loaded_objects:
                    r.print(f"[red]ERROR: Object '{obj_name}' not loaded.[/red]")
                    continue
                obj        = state.loaded_objects[obj_name]
                merged_fns = {**all_functions, **obj["functions"]}
                args       = resolve_args(val, local_vars, all_functions) if val is not None else None
                result     = call_function(func_name, args, merged_fns, local_vars)
                if result == "__exit__":
                    return "__exit__"

            else:
                args   = resolve_args(val, local_vars, all_functions) if val is not None else None
                result = call_function(key, args, all_functions, local_vars)
                if result == "__exit__":
                    return "__exit__"

    return None