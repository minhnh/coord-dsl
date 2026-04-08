from pathlib import Path
from textx import GeneratorDesc, LanguageDesc, metamodel_from_file
from textx.scoping import providers as scoping_providers
from coord_dsl.generators.classes import (
    State,
    Event,
    Transition,
    FiredEvent,
    Reaction,
    FSM,
)
from coord_dsl.generators.fsm_graph import gen_cpp_header, get_fsm_graph, gen_json, gen_python_code
from importlib.resources import files

GRAMMAR_PATH = str(files("coord_dsl.metamodels").joinpath("fsm.tx"))

__SUPPORTED_GRAPH_FORMATS = {"ttl": "ttl", "xml": "xml", "json-ld": "json"}

def fsm_metamodel():
    mm = metamodel_from_file(
        GRAMMAR_PATH,
        classes=[
            State,
            Event,
            Transition,
            FiredEvent,
            Reaction,
            FSM,
        ],
    )
    mm.register_scope_providers(
        {
            "*.*": scoping_providers.FQNImportURI(),
        }
    )
    return mm

fsm_lang = LanguageDesc(
    name="coord_dsl_fsm",
    pattern="*.fsm",
    description="Finite State Machine DSL",
    metamodel=fsm_metamodel,
)


def graph_gen_console(metamodel, model, output_path, overwrite, debug, **kwargs):
    g, context = get_fsm_graph(model)

    ser_args = {"indent": 2, "context": context}

    if "autocompact" in kwargs:
        ser_args["auto_compact"] = True
    else:
        ser_args["auto_compact"] = False

    format = kwargs.get("format", "json-ld")
    if format not in __SUPPORTED_GRAPH_FORMATS:
        raise ValueError(f"Unsupported graph format '{format}', supported formats are: {__SUPPORTED_GRAPH_FORMATS}")

    ser_args["format"] = format

    print(50*"-")
    print(g.serialize(**ser_args))

def graph_gen_file(metamodel, model, output_path, overwrite, debug, **kwargs):
    g, context = get_fsm_graph(model)

    ser_args = {"indent": 2, "context": context}

    if "autocompact" in kwargs:
        ser_args["auto_compact"] = True
    else:
        ser_args["auto_compact"] = False

    format = kwargs.get("format", "json-ld")
    if format not in __SUPPORTED_GRAPH_FORMATS:
        raise ValueError(f"Unsupported graph format '{format}', supported formats are: {__SUPPORTED_GRAPH_FORMATS}")

    ser_args["format"] = format

    if not output_path:
        model_path = Path(model._tx_filename).parent
        file_format = __SUPPORTED_GRAPH_FORMATS[format]
        output_path = f"{model_path}/{model.fsm.name}.{file_format}"

    with open(output_path, "w") as f:
        f.write(g.serialize(**ser_args))
    print(f"FSM graph generated at {output_path}")

def gen_cpp(metamodel, model: FSM, output_path, overwrite, debug, **kwargs):
    g, _ = get_fsm_graph(model)

    ir = gen_json(g)

    rendered = gen_cpp_header(ir)

    if not output_path:
        model_path = Path(model._tx_filename).parent
        output_path = f"{model_path}/{ir["name"]}.hpp"

    with open(output_path, "w") as f:
        f.write(rendered)
    print(f"FSM C code generated at {output_path}")

def gen_python(metamodel, model: FSM, output_path, overwrite, debug, **kwargs):
    g, _ = get_fsm_graph(model)

    ir = gen_json(g)

    rendered = gen_python_code(ir)

    if not output_path:
        model_path = Path(model._tx_filename).parent
        output_path = f"{model_path}/{ir["name"]}.py"

    with open(output_path, "w") as f:
        f.write(rendered)
    print(f"FSM Python code generated at {output_path}")


fsm_console_gen = GeneratorDesc(
    language="coord_dsl_fsm",
    target="console",
    description="Prints the loaded model to console",
    generator=graph_gen_console,
)

fsm_file_gen = GeneratorDesc(
    language="coord_dsl_fsm",
    target="file",
    description="Generates a file with the FSM graph in RDF format",
    generator=graph_gen_file,
)

fsm_cpp_gen = GeneratorDesc(
    language="coord_dsl_fsm",
    target="cpp",
    description="Generates C++ code for the FSM",
    generator=gen_cpp,
)

fsm_python_gen = GeneratorDesc(
    language="coord_dsl_fsm",
    target="python",
    description="Generates Python code for the FSM",
    generator=gen_python,
)
