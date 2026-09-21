# SPDX-License-Identifier: MPL-2.0
# SPDX-FileCopyrightText: 2026 SECORO AG (secoro.uni-bremen.de)
# Author: Vamsi Kalagaturu
"""PROV-O provenance for generated artifacts.

Each generated file is a ``prov-ext:Transformation`` of the model and its imports by the
coord-dsl package. The document beside the artifacts accumulates, one activity per file, so
generating ``cpp`` then ``python`` describes both and a re-run restates only its own file.
"""

from datetime import datetime, timezone
from pathlib import Path
from urllib.parse import quote

from rdf_utils.models.prov import (
    add_file_entity,
    get_pkg_info,
    load_pkg_prov,
    load_transformation_prov,
)
from rdf_utils.namespace import URL_MM_PROV_EXT_JSON, URL_MM_PROV_JSON
from rdf_utils.resolver import install_resolver
from rdflib import Graph, Namespace, URIRef

CDPROV = Namespace("https://secorolab.github.io/coord-dsl/provenance/")
DOCUMENT_NAME = "provenance.ld.json"
AGENT = CDPROV["agent/coord_dsl"]
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


def record(model, target: str, artifact: Path, started: datetime) -> Path:
    """Add one generated file to the provenance document beside it."""
    artifact = Path(artifact).resolve()
    document = artifact.parent / DOCUMENT_NAME
    activity = CDPROV[f"activity/{target}_generation/{quote(artifact.name)}"]
    entity = CDPROV[f"entity/generated/{quote(artifact.name)}"]
    sources = {URIRef(path.as_uri()): path for path in source_paths(model)}

    # The contexts are metamodel URLs; the resolver serves them from the local cache.
    install_resolver()
    graph = Graph()
    if document.exists():
        graph.parse(document, format="json-ld")
    for subject in (AGENT, activity, entity, *sources):
        graph.remove((subject, None, None))

    load_pkg_prov(graph, AGENT, *get_pkg_info("coord_dsl"))
    for source, path in sources.items():
        add_file_entity(graph, source, location=str(path))
    generated_at = datetime.fromtimestamp(artifact.stat().st_mtime, timezone.utc)
    add_file_entity(graph, entity, location=str(artifact), generated_at=generated_at)
    load_transformation_prov(
        graph, activity, sources, [entity], AGENT, started, datetime.now(timezone.utc)
    )
    graph.serialize(
        document, format="json-ld", context=CONTEXT, auto_compact=True, indent=2
    )
    return document
