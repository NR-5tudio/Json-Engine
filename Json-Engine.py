import sys
import rich as r
from Engine.engine import get_functions, run_actions
from Engine.nrjson import nrjson
from datetime import datetime
import os


if len(sys.argv) < 2:
    r.print("[red]Missing arg: <file.json>[/red]")
    sys.exit(1)

now = datetime.now()

year = now.year
month = now.month
day = now.day
hour = now.hour
minute = now.minute
second = now.second

r.print(f"[green]Program Execution Started. | {month}/{day}/{year} | {hour}:{minute}:{second}[/green]")

data = nrjson.load(sys.argv[1])
all_functions = get_functions(data)          # "begin" is NOT callable here (prevents recursion)

run_actions(data.get("begin", []), all_functions)

update_actions = data.get("update", [])
running = True
while update_actions and running:
    if run_actions(update_actions, all_functions) == "__exit__":
        running = False

now = datetime.now()

year = now.year
month = now.month
day = now.day
hour = now.hour
minute = now.minute
second = now.second
r.print(f"\n[green]Program Execution Completed. | {month}/{day}/{year} | {hour}:{minute}:{second}[/green]")
