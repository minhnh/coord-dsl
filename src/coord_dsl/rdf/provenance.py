# SPDX-License-Identifier: MPL-2.0
# SPDX-FileCopyrightText: 2026 SECORO AG (secoro.uni-bremen.de)
# Author: Vamsi Kalagaturu
"""The generation steps of coord-dsl, each recording itself in a bundle in the dataset it is given.

``build`` turns a model into an FSM graph, and ``render`` turns that graph and a template into
code. Both work in one ``Dataset``: the FSM graph and the ``prov:Bundle`` are named graphs in it,
and each step adds itself to the bundle as a ``prov-ext:Transformation``, attributed to the
package. Without a bundle, a step creates one for the package. Files are named by their location,
with the hash of their bytes as ``dcterms:identifier``. Neither step writes the dataset.

The package, named by its purl, is the agent, though PROV-DM 2.2.1.1 defines a software agent as
running software.
"""

from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

from jinja2 import TemplateNotFound
from rdf_utils.models.prov import (
    add_directory_location,
    add_entity,
    add_file_entity,
    add_file_hash,
    create_bundle,
    get_git_info,
    get_pkg_info,
    load_pkg_prov,
    load_transformation_prov,
)
from rdf_utils.models.time import add_wall_instant
from rdflib import RDF, Dataset, Graph, Literal, URIRef
from rdflib.namespace import PROV, SDO

from coord_dsl.generators.fsm import gen_cpp_header, gen_json, gen_python_code
from coord_dsl.rdf.fsm import get_fsm_graph
from coord_dsl.rdf.vocab import URI_FSM_TYPE_FSM

RENDERERS = {
    "cpp": (gen_cpp_header, "templates/fsm.hpp.jinja2"),
    "python": (gen_python_code, "templates/fsm.py.jinja2"),
}


def _bundle(dataset: Dataset, bundle_id: URIRef | None) -> Graph:
    """The bundle to record in: BUNDLE_ID's, or a new one for the package when it is None."""
    if bundle_id is None:
        agent, version, revision, repository, dirty = get_pkg_info("coord_dsl")
        bundle_id = create_bundle(dataset, agent)
        load_pkg_prov(
            dataset.graph(bundle_id),
            agent,
            "coord_dsl",
            version,
            revision,
            repository,
            dirty=dirty,
        )
    return dataset.graph(bundle_id)


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
    dataset: Dataset,
    graph_id: URIRef | None = None,
    bundle_id: URIRef | None = None,
) -> tuple[URIRef, URIRef]:
    """Build the FSM graph of a model in a dataset and add how it was made to a bundle.

    Parameters:
        model: the textX model, loaded from a file; that file is the source
        dataset: the dataset holding the FSM graph and the bundle
        graph_id: the FSM graph to build into; a new `urn:uuid:` when None
        bundle_id: the `prov:Bundle` to record in; a new one for the package when None

    Returns:
        The IRIs of the FSM graph and the bundle
    """
    graph_id = URIRef(uuid4().urn) if graph_id is None else graph_id
    bundle = _bundle(dataset, bundle_id)
    started_at = datetime.now(UTC)
    source = Path(model._tx_filename).resolve()
    get_fsm_graph(model, dataset.graph(graph_id))
    ended_at = datetime.now(UTC)

    source_id = add_file_entity(bundle, add_directory_location(bundle, source.parent), source.name)
    add_file_hash(bundle, source_id)
    commit, repository, _, dirty = get_git_info(source)
    if commit is not None:
        bundle.add((source_id, SDO.identifier, Literal(f"{commit}-dirty" if dirty else commit)))
    if repository is not None:
        bundle.add((source_id, SDO.codeRepository, URIRef(repository)))
    activity = URIRef(uuid4().urn)
    _add_transformation(bundle, activity, [source_id], [graph_id], started_at, ended_at)
    assert isinstance(bundle.identifier, URIRef)
    return graph_id, bundle.identifier


def render(
    dataset: Dataset,
    graph_id: URIRef,
    target: str,
    output_file: Path,
    bundle_id: URIRef | None = None,
) -> URIRef:
    """Render an FSM graph in a dataset to code and add how it was made to a bundle.

    Parameters:
        dataset: the dataset holding the FSM graph and the bundle
        graph_id: the FSM graph to render, e.g. from `build`
        target: what to render, a key of `RENDERERS`
        output_file: the file to write the code to
        bundle_id: the `prov:Bundle` to record in; a new one for the package when None

    Returns:
        The IRI of the bundle

    Raises:
        FileNotFoundError: when the template is missing; nothing is written
    """
    fsm_graph = dataset.graph(graph_id)
    bundle = _bundle(dataset, bundle_id)
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

    add_entity(bundle, graph_id)
    activity = URIRef(uuid4().urn)
    output_id = add_file_entity(
        bundle,
        add_directory_location(bundle, output_file.parent),
        output_file.name,
        generated_by=activity,
    )
    add_file_hash(bundle, output_id)
    _add_transformation(
        bundle, activity, [graph_id, template_id], [output_id], started_at, ended_at
    )
    assert isinstance(bundle.identifier, URIRef)
    return bundle.identifier
