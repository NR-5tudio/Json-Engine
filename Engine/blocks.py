import rich as r
import Engine.state as state
import Engine.game_blocks as game
import Engine.keyboard_blocks as keyboard
Raylib = game.Game
Keyboard = keyboard.Keyboard


def handle_var(value, all_functions, local_vars):
    """Execute a variable-assignment statement: {"var": "x = 5"}"""
    from Engine.engine import resolve_value
    stmt   = resolve_value(value, local_vars, all_functions)
    merged = {**state.variables, **local_vars}
    exec(stmt, {}, merged)
    # Write results back to whichever scope already owns the variable
    for key, val in merged.items():
        if key in local_vars:
            local_vars[key] = val
        else:
            state.variables[key] = val


def handle_colored_print(value, all_functions, local_vars):
    """Print a colored (possibly interpolated) string using rich."""
    from Engine.engine import resolve_value
    Color = value[0]
    Text  = resolve_value(value[1], local_vars, all_functions)
    r.print(f"[{Color}]{Text}[/{Color}]")


def handle_print(value, all_functions, local_vars):
    """Print a (possibly interpolated) string."""
    from Engine.engine import resolve_value
    print(resolve_value(value, local_vars, all_functions))


def handle_input(value, all_functions, local_vars):
    """Read user input: {"input": ["var_name", "prompt"]} or {"input": "var_name"}"""
    from Engine.engine import resolve_value
    if isinstance(value, list) and len(value) == 2:
        var_name, prompt = value[0], resolve_value(value[1], local_vars, all_functions)
    else:
        var_name, prompt = value, ""
    result = input(prompt)
    local_vars[var_name]      = result
    state.variables[var_name] = result


def handle_return(value, all_functions, local_vars):
    """Return a value from the current function only — does not stop the caller."""
    from Engine.engine import resolve_value, ReturnValue
    return ReturnValue(resolve_value(value, local_vars, all_functions))


def handle_if(value, all_functions, local_vars):
    """Conditional branch: {"if": [condition, {"true": ..., "false": ...}]}"""
    from Engine.engine import eval_condition, dispatch_action
    condition    = value[0]
    true_action  = None
    false_action = None
    for part in value[1:]:
        if isinstance(part, dict):
            if "true"  in part: true_action  = part["true"]
            if "false" in part: false_action = part["false"]
    branch = true_action if eval_condition(condition, local_vars, all_functions) else false_action
    if branch is not None:
        return dispatch_action(branch, all_functions, local_vars)


def handle_load(value, all_functions, local_vars):
    """Load an external object file: {"load": ["Player", "player.json"]}"""
    from Engine.engine import get_functions
    from Engine.nrjson import nrjson
    name     = value[0]
    obj_data = nrjson.load(value[1])
    state.loaded_objects[name] = {
        "functions": get_functions(obj_data, include_begin=True),
    }


def handle_exit(value, all_functions, local_vars):
    """Stop the program: {"exit": null}"""
    return "__exit__"


def handle_comment(value, all_functions, local_vars):
    """No-op comment block: {"#": "your comment here"}"""
    pass


def IncludePackage(value, all_functions, local_vars):
    inlist = []
    if isinstance(value, list):
        inlist.extend(value)
    else:
        inlist.append(value)

    for including in inlist:
        # Guard: skip empty/None values
        if not including:
            print("Are you trying to include nothing?")
            continue

        if including in globals():
            print(f"Including - {including}")
            try:
                BUILTIN_HANDLERS.update(globals()[including])
            except Exception as e:
                r.print(f"[red]Error during importing the package '{including}': {e}[/red]")
        else:
            r.print(f"[red]The package '{including}' does not exist.[/red]")

def write_file(value, all_functions, local_vars):
    print("Start")


BUILTIN_HANDLERS = {
    "var":           handle_var,
    "print":         handle_print,
    "output":        handle_print,
    "colored print": handle_colored_print,
    "input":         handle_input,
    "return":        handle_return,
    "if":            handle_if,
    "load":          handle_load,
    "exit":          handle_exit,
    "#":             handle_comment,
    "include":       IncludePackage,
    "write in file": write_file
}