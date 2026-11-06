# SPDX-License-Identifier: MPL-2.0
# SPDX-FileCopyrightText: 2026 SECORO AG (secoro.uni-bremen.de)
# Author: Vamsi Kalagaturu
"""The generation steps of coord-dsl, each recording itself in the bundle it is given.

``build`` turns a model into an FSM graph, saved when a file is given, and ``render`` turns that
graph and a template into code. Each adds itself as a ``prov-ext:Transformation`` to the
``prov:Bundle`` the caller gives it, attributed to the package and stating it. The graph is named by its ``urn:uuid:`` identifier and files by their
location, with the hash of their bytes as ``dcterms:identifier``.

The package, named by its purl, is the agent, though PROV-DM 2.2.1.1 defines a software agent as
running software.
"""

from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

from jinja2 import TemplateNotFound
from rdf_utils import DatasetFormat
from rdf_utils.models.prov import (
    add_directory_location,
    add_entity,
    add_file_entity,
    add_file_hash,
    get_git_info,
    load_transformation_prov,
)
from rdf_utils.models.time import add_wall_instant
from rdflib import RDF, Dataset, Graph, Literal, URIRef
from rdflib.namespace import PROV, SDO

from coord_dsl.generators.fsm import gen_cpp_header, gen_json, gen_python_code
from coord_dsl.rdf.fsm import get_fsm_graph
from coord_dsl.rdf.vocab import URI_FSM_TYPE_FSM

DOCUMENT_SUFFIX = f".prov.{DatasetFormat.JSON_LD.extension}"
RENDERERS = {
    "cpp": (gen_cpp_header, "templates/fsm.hpp.jinja2"),
    "python": (gen_python_code, "templates/fsm.py.jinja2"),
}


def _add_transformation(
    bundle: Graph,
    activity: URIRef,
    sources: list[URIRef],
    targets: list[URIRef],
    started_at: datetime,
    ended_at: datetime,
) -> None:
    """Add a transformation by the package to a bundle, with its wall-clock instants."""
    agent = bundle.value(bundle.identifier, PROV.wasAttributedTo)
    assert isinstance(agent, URIRef)
    beginning, end = URIRef(uuid4().urn), URIRef(uuid4().urn)
    add_wall_instant(bundle, beginning, started_at)
    add_wall_instant(bundle, end, ended_at)
    load_transformation_prov(bundle, activity, sources, targets, agent, beginning, end)


def build(
    model,
    bundle: Graph,
    graph_file: Path | None = None,
    dataset_format: DatasetFormat = DatasetFormat.JSON_LD,
    auto_compact: bool = False,
) -> Graph:
    """Build the FSM graph of a model and add how it was made to a bundle.

    Parameters:
        model: the textX model, loaded from a file; that file is the source
        bundle: the `prov:Bundle` graph to add the transformation to, attributed to the package
        graph_file: the file to save the graph to; the graph is not saved when None
        dataset_format: the format to save it in
        auto_compact: compact JSON-LD with the graph's namespaces

    Returns:
        The graph
    """
    started_at = datetime.now(UTC)
    source = Path(model._tx_filename).resolve()
    fsm_graph, _ = get_fsm_graph(model)
    if graph_file is not None:
        graph_file = Path(graph_file).resolve()
        dataset = Dataset()
        dataset.add_graph(fsm_graph)
        graph_file.write_text(
            dataset.serialize(format=dataset_format, indent=2, auto_compact=auto_compact)
        )
    ended_at = datetime.now(UTC)

    source_id = add_file_entity(bundle, add_directory_location(bundle, source.parent), source.name)
    add_file_hash(bundle, source_id)
    commit, repository, _, dirty = get_git_info(source)
    if commit is not None:
        bundle.add((source_id, SDO.identifier, Literal(f"{commit}-dirty" if dirty else commit)))
    if repository is not None:
        bundle.add((source_id, SDO.codeRepository, URIRef(repository)))
    activity = URIRef(uuid4().urn)
    assert isinstance(fsm_graph.identifier, URIRef)
    targets = [fsm_graph.identifier]
    if graph_file is not None:
        file_id = add_file_entity(
            bundle,
            add_directory_location(bundle, graph_file.parent),
            graph_file.name,
            generated_by=activity,
        )
        add_file_hash(bundle, file_id)
        bundle.add((file_id, PROV.wasDerivedFrom, fsm_graph.identifier))
        targets.append(file_id)
    _add_transformation(bundle, activity, [source_id], targets, started_at, ended_at)
    return fsm_graph


def render(fsm_graph: Graph, bundle: Graph, target: str, output_file: Path) -> Path:
    """Render an FSM graph to code and add how it was made to a bundle.

    Parameters:
        fsm_graph: the graph `build` returned
        bundle: the `prov:Bundle` graph to add the transformation to, attributed to the package,
            with `load_pkg_prov` stating it so that the template can be found
        target: what to render, a key of `RENDERERS`
        output_file: the file to write the code to

    Returns:
        The written file

    Raises:
        FileNotFoundError: when the template is missing; nothing is written
    """
    started_at = datetime.now(UTC)
    renderer, template_path = RENDERERS[target]
    output_file = Path(output_file).resolve()
    fsm_ref = fsm_graph.value(predicate=RDF.type, object=URI_FSM_TYPE_FSM)
    assert isinstance(fsm_ref, URIRef)
    agent = bundle.value(bundle.identifier, PROV.wasAttributedTo)
    assert isinstance(agent, URIRef)
    template_id = add_file_entity(bundle, agent, template_path)
    try:
        add_file_hash(bundle, template_id)
        code = renderer(gen_json(fsm_graph, fsm_ref))
    except (FileNotFoundError, TemplateNotFound) as error:
        raise FileNotFoundError(
            f"template for target '{target}' not found -- coord_dsl install is incomplete: {error}"
        ) from error
    output_file.write_text(code)
    ended_at = datetime.now(UTC)

    assert isinstance(fsm_graph.identifier, URIRef)
    add_entity(bundle, fsm_graph.identifier)
    activity = URIRef(uuid4().urn)
    output_id = add_file_entity(
        bundle,
        add_directory_location(bundle, output_file.parent),
        output_file.name,
        generated_by=activity,
    )
    add_file_hash(bundle, output_id)
    _add_transformation(
        bundle, activity, [fsm_graph.identifier, template_id], [output_id], started_at, ended_at
    )
    return output_file


def write_bundle(bundle: Graph, document: Path | str) -> None:
    """Write a bundle as its own JSON-LD document, replacing any earlier one."""
    dataset = Dataset()
    dataset.add_graph(bundle)
    Path(document).write_text(dataset.serialize(format=DatasetFormat.JSON_LD, indent=2))
