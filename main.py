import pyray as pr
import json
import EasyJson as nrjson

data = nrjson.Load("main.json")


settings = data["main"]
print(settings)
pr.init_window(settings["width"], settings["height"], settings["title"])
# Load JSON

# Variables dict
variables = {}

# Includes (kept if you need it)
includes = data.get("include", {})

# Function to run any list of actions
def run_actions(actions):
    for action in actions:
        if "var" in action:  # create/update variable
            exec(action["var"], {}, variables)
        if "print" in action:  # print (supports {var} placeholders)
            print(action["print"].format(**variables))

# Run begin (variables like Health are created here)
run_actions(data.get("begin", []))

# Main loop for update
while not pr.window_should_close():
    pr.begin_drawing()
    pr.clear_background(pr.BLACK)
    run_actions(data.get("update", []))
    pr.end_drawing()