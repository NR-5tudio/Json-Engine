import json
import sys
from rich import print

# ─── Replace with your real EasyJson module ───────────────────────────────────
class nrjson:
    @staticmethod
    def Load(path):
        with open(path, "r") as f:
            return json.load(f)

# ─── Globals ──────────────────────────────────────────────────────────────────
Error          = False
variables      = {}        # global variable scope
loaded_objects = {}        # { "Player": { "functions": {...} } }

RESERVED_TOP = {"begin", "update", "include", "window"}
BUILTINS     = {"var", "print", "input", "return", "if", "load"}


def get_functions(data_block, include_begin=False):
    skip = set(RESERVED_TOP)
    if include_begin:
        skip.discard("begin")
    return {k: v for k, v in data_block.items()
            if isinstance(v, list) and k not in skip}


def resolve_value(val, local_vars):
    if isinstance(val, str):
        merged = {**variables, **local_vars}
        try:
            return val.format(**merged)
        except (KeyError, ValueError):
            return val
    return val


def resolve_args(val, local_vars):
    if isinstance(val, list):
        return [resolve_value(v, local_vars) for v in val]
    if isinstance(val, str):
        return resolve_value(val, local_vars)
    return val


def eval_condition(condition, local_vars):
    merged = {**variables, **local_vars}
    try:
        return bool(eval(condition.format(**merged), {}, merged))
    except Exception as e:
        print(f"[red]ERROR evaluating condition '{condition}': {e}[/red]")
        return False


def call_function(func_name, args, all_functions, local_vars):
    if func_name not in all_functions:
        print(f"[red]ERROR: Function '{func_name}' not found.[/red]")
        return None

    body = all_functions[func_name]
    param_names  = []
    action_start = 0

    for i, item in enumerate(body):
        if isinstance(item, dict) and "param" in item:
            raw = item["param"]
            param_names = [p.split(":")[0] for p in raw] if isinstance(raw, list) else []
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

    return run_actions(body[action_start:], all_functions, func_locals)


def dispatch_action(action, all_functions, local_vars):
    if isinstance(action, list):
        return run_actions(action, all_functions, local_vars)
    if isinstance(action, dict):
        return run_actions([action], all_functions, local_vars)
    if isinstance(action, str):
        if action in all_functions:
            return call_function(action, None, all_functions, local_vars)
        return resolve_value(action, local_vars)
    return None


def run_actions(actions, all_functions, local_vars=None):
    if local_vars is None:
        local_vars = {}

    for action in actions:
        if isinstance(action, str):
            result = call_function(action, None, all_functions, local_vars)
            if result is not None:
                return result
            continue

        if not isinstance(action, dict):
            continue

        if "var" in action:
            stmt   = resolve_value(action["var"], local_vars)
            merged = {**variables, **local_vars}
            exec(stmt, {}, merged)
            for k, v in merged.items():
                if k in local_vars:
                    local_vars[k] = v
                else:
                    variables[k] = v
            continue

        if "print" in action:
            print(resolve_value(action["print"], local_vars))
            continue

        if "input" in action:
            params = action["input"]
            if isinstance(params, list) and len(params) == 2:
                var_name = params[0]
                prompt   = resolve_value(params[1], local_vars)
            else:
                var_name = params
                prompt   = ""
            value = input(prompt)
            local_vars[var_name] = value
            variables[var_name]  = value
            continue

        if "return" in action:
            return resolve_value(action["return"], local_vars)

        if "if" in action:
            if_block     = action["if"]
            condition    = if_block[0]
            true_action  = None
            false_action = None
            for part in if_block[1:]:
                if isinstance(part, dict):
                    if "true"  in part: true_action  = part["true"]
                    if "false" in part: false_action = part["false"]
            branch = true_action if eval_condition(condition, local_vars) else false_action
            if branch is not None:
                ret = dispatch_action(branch, all_functions, local_vars)
                if ret is not None:
                    return ret
            continue

        if "load" in action:
            info     = action["load"]
            name     = info["name"]
            obj_data = nrjson.Load(info["source"])
            loaded_objects[name] = {
                "functions": get_functions(obj_data, include_begin=True),
            }
            continue

        for key, val in action.items():
            if key in BUILTINS:
                continue

            if "." in key:
                obj_name, func_name = key.split(".", 1)
                if obj_name not in loaded_objects:
                    print(f"[red]ERROR: Object '{obj_name}' not loaded.[/red]")
                    continue
                obj        = loaded_objects[obj_name]
                merged_fns = {**all_functions, **obj["functions"]}
                args       = resolve_args(val, local_vars) if val is not None else None
                result     = call_function(func_name, args, merged_fns, local_vars)
                if result is not None:
                    return result
            else:
                args   = resolve_args(val, local_vars) if val is not None else None
                result = call_function(key, args, all_functions, local_vars)
                if result is not None:
                    return result

    return None


# ─── Entry point ──────────────────────────────────────────────────────────────

path = None
if len(sys.argv) > 1:
    path = sys.argv[1]
else:
    print("[red]Usage: python main.py <file.json>[/red]")
    exit(1)

data          = nrjson.Load(path)
all_functions = get_functions(data)   # main begin is NOT callable, prevents recursion

run_actions(data.get("begin", []), all_functions)

update_actions = data.get("update", [])
running = True
while update_actions and running:
    result = run_actions(update_actions, all_functions)
    if result == "__exit__":
        running = False

print("\n")
if not Error:
    print("[green]PROGRAM EXECUTION COMPLETED[/green]")
    print("- Script:", sys.argv[0])