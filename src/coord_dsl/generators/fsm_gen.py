import json
from dataclasses import dataclass, field
from textx import generator
from jinja2 import Environment, FileSystemLoader
from pathlib import Path


@dataclass
class FSMData:
    name: str = ""
    description: str = ""
    states: list = field(default_factory=list)
    start_state: str = ""
    current_state: str = ""
    end_state: str = ""
    events: list = field(default_factory=list)
    transitions: list = field(default_factory=list)
    reactions: list = field(default_factory=list)
    transitions_table: dict = field(default_factory=dict)
    reactions_table: dict = field(default_factory=dict)

    def to_json(self):
        return json.dumps(
            {
                "name": self.name,
                "description": self.description,
                "states": self.states,
                "start_state": self.start_state,
                "current_state": self.current_state,
                "end_state": self.end_state,
                "events": self.events,
                "transitions": self.transitions,
                "reactions": self.reactions,
                "transitions_table": self.transitions_table,
                "reactions_table": self.reactions_table,
            },
            indent=4,
        )


def parse_fsm(model):
    fsm = FSMData()

    fsm.name = model.name
    fsm.description = model.description

    fsm.states = [state.name for state in model.states]

    fsm.start_state = model.start_state.name
    fsm.current_state = model.current_state.name
    fsm.end_state = model.end_state.name

    fsm.events = [event.name for event in model.events]

    for transition in model.transitions:
        fsm.transitions.append(transition.name)
        fsm.transitions_table[transition.name] = {
            "from": transition.from_state.name,
            "to": transition.to_state.name,
        }

    for reaction in model.reactions:
        fsm.reactions.append(reaction.name)
        fsm.reactions_table[reaction.name] = {
            "when": reaction.when.name,
            "do": reaction.do.name,
            "num_fires": len(reaction.fires),
            "fires": [event.name for event in reaction.fires]
            if len(reaction.fires) > 0
            else None,
        }

    return fsm


@generator("fsm", "console")
def fsm_console_gen(metamodel, model, output_path, overwrite, debug, **custom_args):
    """Prints the FSM datastructures to the console"""
    print(f"Generating FSM: {model.name}")

    fsm = parse_fsm(model)

    print(fsm.to_json())


@generator("fsm", "cpp")
def fsm_cpp_gen(metamodel, model, output_path, overwrite, debug, **custom_args):
    """Generates a .hpp file with the FSM datastructures"""

    print(f"Generating C code for FSM: {model.name}")

    # get module path
    module_path = Path(__file__).parent.parent
    env = Environment(loader=FileSystemLoader(module_path / "templates"))
    template = env.get_template("fsm.hpp.jinja2")

    fsm = parse_fsm(model)

    fsm_name = model.name

    output = template.render(
        {
            "data": fsm,
        }
    )

    if not output_path:
        model_path = Path(model._tx_filename).parent
        output_path = f"{model_path}/{fsm_name}.fsm.hpp"

    with open(output_path, "w") as f:
        f.write(output)
    print(f"FSM C code generated at {output_path}")


@generator("fsm", "py")
def fsm_py_gen(metamodel, model, output_path, overwrite, debug, **custom_args):
    """Generates a .py file with the FSM datastructures"""

    print(f"Generating Python code for FSM: {model.name}")

    # get module path
    module_path = Path(__file__).parent.parent
    env = Environment(loader=FileSystemLoader(module_path / "templates"))
    template = env.get_template("fsm.py.jinja2")

    fsm = parse_fsm(model)

    fsm_name = model.name

    output = template.render(
        {
            "data": fsm,
        }
    )

    if not output_path:
        model_path = Path(model._tx_filename).parent
        output_path = f"{model_path}/fsm_{fsm_name}.py"

    with open(output_path, "w") as f:
        f.write(output)
    print(f"FSM C code generated at {output_path}")


@generator("fsm", "json")
def fsm_json_gen(metamodel, model, output_path, overwrite, debug, **custom_args):
    """Generates a .json file with the FSM datastructures"""

    print(f"Generating JSON for FSM: {model.name}")

    fsm = parse_fsm(model)

    if not output_path:
        model_path = Path(model._tx_filename).parent
        output_path = f"{model_path}/{model.name}.fsm.json"

    with open(output_path, "w") as f:
        f.write(fsm.to_json())
    print(f"FSM JSON generated at {output_path}")
