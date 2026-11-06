# SPDX-License-Identifier: MPL-2.0
# SPDX-FileCopyrightText: 2026 SECORO AG (secoro.uni-bremen.de)
# Author: Vamsi Kalagaturu
"""textX registration and generators for finite-state-machine models."""

from importlib.resources import files
from pathlib import Path

from rdf_utils import DatasetFormat
from rdf_utils.models.prov import create_bundle, get_pkg_info, load_pkg_prov
from rdflib import Dataset
from textx import GeneratorDesc, LanguageDesc, metamodel_from_file
from textx.scoping import providers as scoping_providers

from coord_dsl.classes.event_loop import Event, EventLoop, EventRef
from coord_dsl.classes.fsm import FSM, Reaction, State, Transition
from coord_dsl.generators.dot import FORMATS, fsm_dot, write_dot
from coord_dsl.generators.fsm import gen_json
from coord_dsl.rdf.fsm import get_fsm_graph
from coord_dsl.rdf.provenance import (
    DOCUMENT_SUFFIX,
    RENDERERS,
    build,
    render,
    write_bundle,
)

GRAMMAR_PATH = str(files("coord_dsl.metamodels").joinpath("fsm.tx"))


def fsm_metamodel():
    mm = metamodel_from_file(
        GRAMMAR_PATH,
        classes=[EventLoop, Event, EventRef, State, Transition, Reaction, FSM],
    )
    mm.register_scope_providers({"*.*": scoping_providers.FQNImportURI()})
    return mm


fsm_lang = LanguageDesc(
    name="coord_dsl_fsm",
    pattern="*.fsm",
    description="Finite State Machine DSL",
    metamodel=fsm_metamodel,
)


def graph_gen_console(metamodel, model, output_path, overwrite, debug, **kwargs):
    del metamodel, output_path, overwrite, debug
    dataset_format = DatasetFormat(kwargs.get("format", DatasetFormat.JSON_LD))
    dataset = Dataset()
    dataset.add_graph(get_fsm_graph(model)[0])
    print(50 * "-")
    print(
        dataset.serialize(
            format=dataset_format, indent=2, auto_compact="autocompact" in kwargs
        )
    )


def graph_gen_file(metamodel, model, output_path, overwrite, debug, **kwargs):
    del metamodel, overwrite, debug
    dataset_format = DatasetFormat(kwargs.get("format", DatasetFormat.JSON_LD))
    if not output_path:
        output_path = (
            Path(model._tx_filename).parent / f"{model.fsm.name}.{dataset_format.extension}"
        )
    auto_compact = "autocompact" in kwargs
    if "provenance" in kwargs:
        agent, version, revision, repository, dirty = get_pkg_info("coord_dsl")
        bundle = create_bundle(agent)
        load_pkg_prov(bundle, agent, "coord_dsl", version, revision, repository, dirty=dirty)
        build(model, bundle, output_path, dataset_format, auto_compact)
        write_bundle(bundle, Path(output_path).parent / f"{model.fsm.name}{DOCUMENT_SUFFIX}")
    else:
        dataset = Dataset()
        dataset.add_graph(get_fsm_graph(model)[0])
        Path(output_path).write_text(
            dataset.serialize(format=dataset_format, indent=2, auto_compact=auto_compact)
        )
    print(f"FSM graph generated at {output_path}")


def gen_fsm_dot_console(metamodel, model, output_path, overwrite, debug, **kwargs):
    del metamodel, output_path, overwrite, debug, kwargs
    g, fsm_ref = get_fsm_graph(model)
    print(fsm_dot(g, fsm_ref), end="")


def gen_fsm_dot_file(metamodel, model, output_path, overwrite, debug, **kwargs):
    del metamodel, debug
    img_format = kwargs.get("format", "dot")
    if img_format not in ("dot",) + FORMATS:
        raise ValueError(
            f"unhandled format {img_format!r} for the state-machine graph, try {['dot', *FORMATS]}"
        )
    g, fsm_ref = get_fsm_graph(model)
    output_path = (
        output_path
        or Path(model._tx_filename).parent / f"{model.fsm.name}.{img_format}"
    )
    if Path(output_path).exists() and not overwrite:
        print(f"not overwriting existing file '{output_path}'")
        return
    write_dot(fsm_dot(g, fsm_ref), output_path, img_format)
    print(f"FSM graph drawn at {output_path}")


def gen_code(model, output_path, target, suffix, record_provenance):
    name = model.fsm.name
    output_path = Path(output_path or Path(model._tx_filename).parent / f"{name}{suffix}")
    if not record_provenance:
        graph, fsm_ref = get_fsm_graph(model)
        output_path.write_text(RENDERERS[target][0](gen_json(graph, fsm_ref)))
        return output_path
    agent, version, revision, repository, dirty = get_pkg_info("coord_dsl")
    bundle = create_bundle(agent)
    load_pkg_prov(bundle, agent, "coord_dsl", version, revision, repository, dirty=dirty)
    output_file = render(build(model, bundle), bundle, target, output_path)
    write_bundle(bundle, f"{output_file}{DOCUMENT_SUFFIX}")
    return output_file


def gen_cpp(metamodel, model, output_path, overwrite, debug, **kwargs):
    del metamodel, overwrite, debug
    output_file = gen_code(model, output_path, "cpp", ".hpp", "provenance" in kwargs)
    print(f"FSM C code generated at {output_file}")


def gen_python(metamodel, model, output_path, overwrite, debug, **kwargs):
    del metamodel, overwrite, debug
    output_file = gen_code(model, output_path, "python", ".py", "provenance" in kwargs)
    print(f"FSM Python code generated at {output_file}")


fsm_console_gen = GeneratorDesc(
    language="coord_dsl_fsm",
    target="console",
    description="Prints the loaded model to console",
    generator=graph_gen_console,
)
fsm_file_gen = GeneratorDesc(
    language="coord_dsl_fsm",
    target="graph",
    description="Generates a file with the FSM graph in RDF format",
    generator=graph_gen_file,
)
fsm_dot_console_gen = GeneratorDesc(
    language="coord_dsl_fsm",
    target="dot-console",
    description="Print the state machine as a graphviz graph",
    generator=gen_fsm_dot_console,
)
fsm_dot_gen = GeneratorDesc(
    language="coord_dsl_fsm",
    target="dot",
    description="Draw the state machine: states joined by the reactions that fire them."
    " Formats: dot (default), png, svg, pdf",
    generator=gen_fsm_dot_file,
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
