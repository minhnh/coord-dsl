# SPDX-License-Identifier: MPL-2.0
# SPDX-FileCopyrightText: 2026 SECORO AG (secoro.uni-bremen.de)
# Author: Vamsi Kalagaturu
"""Tests for the PROV-O document generators write beside their artifacts."""

import unittest
from datetime import UTC, datetime
from pathlib import Path
from tempfile import TemporaryDirectory
from types import SimpleNamespace

from rdf_utils.constraints import check_shacl_constraints
from rdf_utils.models.prov import get_ni_iri, resolve_location
from rdf_utils.models.vocab import URI_PROV_EXT_TYPE_TRANSFORMATION
from rdf_utils.namespace import URL_MM_PROV_EXT_SHACL, URL_MM_PROV_SHACL
from rdflib import Dataset, URIRef
from rdflib.namespace import PROV, RDF, SDO

from coord_dsl.rdf.provenance import (
    AGENT,
    DOCUMENT_SUFFIX,
    record,
    source_paths,
)
from coord_dsl.registration import fsm_metamodel, gen_cpp, gen_python

MODEL = (
    Path(__file__).resolve().parents[1] / "examples" / "models" / "fsm" / "example.fsm"
)
SHAPES = {URL_MM_PROV_SHACL: "turtle", URL_MM_PROV_EXT_SHACL: "turtle"}


class ProvenanceTest(unittest.TestCase):
    def setUp(self):
        self.model = fsm_metamodel().model_from_file(str(MODEL))
        temporary = TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.directory = Path(temporary.name)

    def document(self, output: Path) -> Dataset:
        return Dataset(default_union=True).parse(
            output.with_name(f"{output.name}{DOCUMENT_SUFFIX}"), format="json-ld"
        )

    def test_generation_is_a_transformation_of_the_model_by_the_package(self):
        output = self.directory / "ex_fsm.py"
        gen_python(None, self.model, output, False, False)
        graph = self.document(output)

        (entity,) = [
            entity
            for entity in graph.subjects(PROV.wasGeneratedBy)
            if resolve_location(graph, entity) == URIRef(output.as_uri())
        ]
        activity = graph.value(entity, PROV.wasGeneratedBy)
        (source,) = graph.objects(activity, PROV.used)
        self.assertIn((activity, RDF.type, URI_PROV_EXT_TYPE_TRANSFORMATION), graph)
        self.assertEqual(entity, get_ni_iri(output))
        self.assertEqual(source, get_ni_iri(MODEL))
        self.assertIn((activity, PROV.wasAssociatedWith, AGENT), graph)
        self.assertIn((None, PROV.wasAttributedTo, AGENT), graph)
        self.assertEqual(str(graph.value(AGENT, SDO.name)), "coord_dsl")
        self.assertLess(
            graph.value(activity, PROV.startedAtTime),
            graph.value(activity, PROV.endedAtTime),
        )
        check_shacl_constraints(graph, SHAPES)

    def test_each_file_has_one_document_replaced_on_each_run(self):
        output = self.directory / "ex_fsm.py"
        gen_python(None, self.model, output, False, False)
        gen_python(None, self.model, output, False, False)
        gen_cpp(None, self.model, self.directory / "ex_fsm.hpp", False, False)

        documents = sorted(self.directory.glob("*.ld.json"))
        self.assertEqual(
            [document.name for document in documents],
            ["ex_fsm.hpp.prov.ld.json", "ex_fsm.py.prov.ld.json"],
        )
        for document in documents:
            dataset = Dataset().parse(document, format="json-ld")
            bundles = [
                g for g in dataset.graphs() if (None, RDF.type, PROV.Bundle) in g
            ]
            self.assertEqual(len(bundles), 1)
            check_shacl_constraints(Dataset(default_union=True).parse(document), SHAPES)
        self.assertEqual(
            set(self.document(output).subjects(PROV.wasGeneratedBy)), {get_ni_iri(output)}
        )

    def test_a_tool_records_a_file_it_wrote(self):
        started = datetime.now(UTC)
        header = self.directory / "ex_fsm.hpp"
        header.write_text("// header\n")
        self.assertEqual(
            record(self.model, header, started),
            self.directory / "ex_fsm.hpp.prov.ld.json",
        )
        graph = self.document(header)
        (activity,) = graph.subjects(RDF.type, URI_PROV_EXT_TYPE_TRANSFORMATION)
        (entity,) = graph.subjects(PROV.wasGeneratedBy, activity)
        self.assertEqual(resolve_location(graph, entity), URIRef(header.as_uri()))

    def test_source_paths_resolve_to_the_fsm_model(self):
        self.assertEqual(source_paths(self.model), [MODEL.resolve()])

    def test_sources_with_the_same_name_remain_distinct(self):
        first = self.directory / "a" / "shared.fsm"
        second = self.directory / "b" / "shared.fsm"
        first.parent.mkdir()
        second.parent.mkdir()
        first.write_text("// a\n")
        second.write_text("// b\n")
        imported = [
            SimpleNamespace(_tx_filename=str(first), imports=[]),
            SimpleNamespace(_tx_filename=str(second), imports=[]),
        ]
        model = SimpleNamespace(
            _tx_filename=None,
            imports=[SimpleNamespace(_tx_loaded_models=imported)],
        )
        artifact = self.directory / "generated.py"
        artifact.write_text("# generated\n")

        record(model, artifact, datetime.now(UTC))
        graph = self.document()
        (activity,) = graph.subjects(RDF.type, URI_PROV_EXT_TYPE_TRANSFORMATION)
        sources = set(graph.objects(activity, PROV.used))

        self.assertEqual(len(sources), 2)
        self.assertEqual(
            {resolve_location(graph, source) for source in sources},
            {URIRef(first.as_uri()), URIRef(second.as_uri())},
        )


if __name__ == "__main__":
    unittest.main()
