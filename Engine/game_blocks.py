import sys
import os
import builtins
import sys

original_print = print
def silent_print(*args, **kwargs):
    if args and "RAYLIB STATIC" in str(args[0]):
        return
    original_print(*args, **kwargs)

builtins.print = silent_print
import pyray as pr
builtins.print = original_print

# Now pyray is imported without the message
from simpleeval import simple_eval

def show_window(value, all_functions, local_vars):
    """Initialize a raylib window."""
    from Engine.engine import resolve_value
    Title  = resolve_value(value[0], local_vars, all_functions)
    Width  = value[1]
    Height = value[2]
    pr.init_window(Width, Height, Title)

def is_raylib_okay(val, all_functions, local_vars):
    """Quick sanity-check: prints a message if raylib loaded correctly."""
    print("yes if you see this message, raylib is okay.")

def window_should_close(val, all_functions, local_vars):
    """Returns True if the window close button was pressed."""
    from Engine.engine import ReturnValue
    return ReturnValue(pr.window_should_close())

def clear_background(val, all_functions, local_vars):
    from Engine.engine import resolve_value
    pr.clear_background(pr.BLACK)

def begin_drawing(val, all_functions, local_vars):
    from Engine.engine import resolve_value
    pr.begin_drawing()

def end_drawing(val, all_functions, local_vars):
    from Engine.engine import resolve_value
    pr.end_drawing()

def draw_rectangle(value, all_functions, local_vars):
    """[X, Y, Width, Height, Color]"""
    from Engine.engine import resolve_value
    X = simple_eval(resolve_value(value[0], local_vars, all_functions))
    Y = simple_eval(resolve_value(value[1], local_vars, all_functions))
    pr.draw_rectangle(int(X), int(Y), int(value[2]), int(value[3]), value[4])

def delta_time(val, all_functions, local_vars):
    """Returns True if the window close button was pressed."""
    from Engine.engine import ReturnValue
    return ReturnValue(pr.get_frame_time())

Game = {
    "show window":          show_window,
    "is raylib okay":       is_raylib_okay,
    "window should close":  window_should_close,
    "clear background":     clear_background,
    "begin drawing":        begin_drawing,
    "end drawing":          end_drawing,
    "draw rectangle":       draw_rectangle,
    "get delta time":       delta_time
}