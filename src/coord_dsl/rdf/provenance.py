# SPDX-License-Identifier: MPL-2.0
# SPDX-FileCopyrightText: 2026 SECORO AG (secoro.uni-bremen.de)
# Author: Vamsi Kalagaturu
"""PROV-O provenance for generated artifacts.

Each generated file is a ``prov-ext:Transformation`` of the model and its imports by the
coord-dsl package, recorded in a ``prov:Bundle`` of its own. Files are named by their content,
so every tool names a file alike and a caller adds the bundle to its record unchanged. Each
generator run writes its bundle beside the file, as ``<file>.prov.ld.json``, replacing the one
that described the bytes it overwrote.
"""

from datetime import UTC, datetime
from pathlib import Path
from uuid import uuid4

from rdf_utils.models.prov import (
    add_file_entity,
    create_bundle,
    get_git_info,
    get_pkg_info,
    load_pkg_prov,
    load_transformation_prov,
)
from rdf_utils.namespace import URL_MM_PROV_EXT_JSON, URL_MM_PROV_JSON, URL_SECORO_UNI
from rdf_utils.resolver import install_resolver
from rdflib import Dataset, Graph, Literal, Namespace, URIRef
from rdflib.namespace import SDO

CDPROV = Namespace(f"{URL_SECORO_UNI}/coord-dsl/provenance/")
DOCUMENT_SUFFIX = ".prov.ld.json"
AGENTS = Namespace(f"{CDPROV}agent/")
AGENT = AGENTS["coord-dsl"]
CONTEXT = [URL_MM_PROV_JSON, URL_MM_PROV_EXT_JSON, {"cdprov": str(CDPROV)}]


def source_paths(model) -> list[Path]:
    """The model file and everything it imported."""
    paths: dict[Path, None] = {}

    def visit(item):
        filename = getattr(item, "_tx_filename", None)
        if filename:
            paths[Path(filename).resolve()] = None
        for imp in getattr(item, "imports", []):
            for loaded in getattr(imp, "_tx_loaded_models", []):
                visit(loaded)

    visit(model)
    return list(paths)


def generation_provenance(
    model,
    outputs: list[Path],
    started: datetime,
    ended: datetime,
    root: Path | None = None,
    source_dir: Path | None = None,
    agents: Namespace | None = None,
) -> Graph:
    """The transformation of MODEL's sources into OUTPUTS by coord-dsl, as a `prov:Bundle`.

    Parameters:
        root: directory files are located from; the first output's when None
        source_dir: where the caller keeps a copy of each source, by its file name; the
            sources are then located by their copies
        agents: namespace coord-dsl is named in; `AGENTS` when None
    """
    root = root or Path(outputs[0]).resolve().parent
    agents = agents or AGENTS
    agent = agents["coord-dsl"]
    bundle = create_bundle(agent)
    load_pkg_prov(bundle, agent, *get_pkg_info("coord_dsl"))
    sources = []
    for path in source_paths(model):
        source = add_file_entity(
            bundle, root, Path(source_dir) / path.name if source_dir else path
        )
        commit, repository = get_git_info(path)
        if commit is not None:
            bundle.add((source, SDO.identifier, Literal(commit)))
        if repository is not None:
            bundle.add((source, SDO.codeRepository, URIRef(repository)))
        sources.append(source)
    activity = URIRef(uuid4().urn)
    targets = [
        add_file_entity(bundle, root, path, generated_by=activity) for path in outputs
    ]
    load_transformation_prov(bundle, activity, sources, targets, agent, started, ended)
    return bundle


def record(model, artifact: Path, started: datetime, **kwargs) -> Path:
    """Write one generated file's provenance beside it, as `<file>.prov.ld.json`, and return it.

    KWARGS are the generator's; `root`, `source_dir` and `agents` among them are passed to
    `generation_provenance`.
    """
    artifact = Path(artifact).resolve()
    document = artifact.with_name(f"{artifact.name}{DOCUMENT_SUFFIX}")
    # The contexts are metamodel URLs; the resolver serves them from the local cache.
    install_resolver()
    dataset = Dataset()
    dataset.add_graph(
        generation_provenance(
            model,
            [artifact],
            started,
            datetime.now(UTC),
            root=kwargs.get("root"),
            source_dir=kwargs.get("source_dir"),
            agents=kwargs.get("agents"),
        )
    )
    dataset.serialize(
        document, format="json-ld", context=CONTEXT, auto_compact=True, indent=2
    )
    return document
