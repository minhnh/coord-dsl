# SPDX-License-Identifier: MPL-2.0
# SPDX-FileCopyrightText: 2026 SECORO AG (secoro.uni-bremen.de)
# Author: Vamsi Kalagaturu
"""The generation steps of coord-dsl, each recording itself in a bundle in the dataset it is given.

``build`` turns a model into an FSM graph, and ``render`` turns that graph and a template into
code. Both work in one ``Dataset``: the FSM graph and the ``prov:Bundle`` are named graphs in it,
and each step adds itself to the bundle as a ``prov-ext:Transformation`` associated with the
package, which the caller states in the bundle first. Files are named by their location, with the
hash of their bytes as ``dcterms:identifier``. Neither step writes the dataset.

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
from rdflib.namespace import SDO

from coord_dsl.generators.fsm import RENDERERS, gen_json
from coord_dsl.rdf.fsm import get_fsm_graph
from coord_dsl.rdf.vocab import URI_FSM_TYPE_FSM


def create_coord_dsl_bundle(dataset: Dataset) -> tuple[URIRef, URIRef]:
    """Create a bundle for coord_dsl in a dataset, stating the package as its agent.

    Returns:
        The IDs of the bundle and of the package, to pass to `build` and `render`
    """
    purl, version, revision, repository, dirty = get_pkg_info("coord_dsl")
    bundle_id = create_bundle(dataset, purl)
    load_pkg_prov(
        dataset.graph(bundle_id), purl, "coord_dsl", version, revision, repository, dirty=dirty
    )
    return bundle_id, purl


def _add_transformation(
    bundle: Graph,
    agent: URIRef,
    activity: URIRef,
    sources: list[URIRef],
    targets: list[URIRef],
    started_at: datetime,
    ended_at: datetime,
) -> None:
    """Add a transformation by an agent to a bundle, with its wall-clock instants."""
    beginning, end = URIRef(uuid4().urn), URIRef(uuid4().urn)
    add_wall_instant(bundle, beginning, started_at)
    add_wall_instant(bundle, end, ended_at)
    load_transformation_prov(bundle, activity, sources, targets, agent, beginning, end)


def build(
    model,
    dataset: Dataset,
    bundle_id: URIRef,
    agent_id: URIRef,
    graph_id: URIRef | None = None,
) -> URIRef:
    """Build the FSM graph of a model in a dataset and add how it was made to a bundle.

    Parameters:
        model: the textX model, loaded from a file; that file is the source
        dataset: the dataset holding the FSM graph and the bundle
        bundle_id: the `prov:Bundle` in the dataset to record in
        agent_id: the coord_dsl package, stated in the bundle with `load_pkg_prov`
        graph_id: the FSM graph to build into; a new `urn:uuid:` when None

    Returns:
        The IRI of the FSM graph
    """
    graph_id = URIRef(uuid4().urn) if graph_id is None else graph_id
    bundle = dataset.graph(bundle_id)
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
    _add_transformation(
        bundle, agent_id, activity, [source_id], [graph_id], started_at, ended_at
    )
    return graph_id


def render(
    dataset: Dataset,
    graph_id: URIRef,
    bundle_id: URIRef,
    agent_id: URIRef,
    target: str,
    output_file: Path,
) -> None:
    """Render an FSM graph in a dataset to code and add how it was made to a bundle.

    Parameters:
        dataset: the dataset holding the FSM graph and the bundle
        graph_id: the FSM graph to render, e.g. from `build`
        bundle_id: the `prov:Bundle` in the dataset to record in
        agent_id: the coord_dsl package, stated in the bundle with `load_pkg_prov`; its
            template is found under it
        target: what to render, a key of `RENDERERS`
        output_file: the file to write the code to

    Raises:
        FileNotFoundError: when the template is missing; nothing is written
    """
    fsm_graph = dataset.graph(graph_id)
    bundle = dataset.graph(bundle_id)
    started_at = datetime.now(UTC)
    renderer, template_path = RENDERERS[target]
    output_file = Path(output_file).resolve()
    fsm_ref = fsm_graph.value(predicate=RDF.type, object=URI_FSM_TYPE_FSM)
    assert isinstance(fsm_ref, URIRef)
    template_id = add_file_entity(bundle, agent_id, template_path)
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
        bundle, agent_id, activity, [graph_id, template_id], [output_id], started_at, ended_at
    )
