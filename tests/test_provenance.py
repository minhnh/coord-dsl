# SPDX-License-Identifier: MPL-2.0
# SPDX-FileCopyrightText: 2026 SECORO AG (secoro.uni-bremen.de)
# Author: Vamsi Kalagaturu
"""Tests for the generation steps and the provenance they return."""

import unittest
from importlib.resources import files
from pathlib import Path
from tempfile import TemporaryDirectory

from rdf_utils.constraints import check_shacl_constraints
from rdf_utils.models.prov import (
    create_bundle,
    get_git_info,
    get_pkg_info,
    load_pkg_prov,
    resolve_location,
)
from rdf_utils.models.vocab import URI_PROV_EXT_TYPE_TRANSFORMATION
from rdf_utils.namespace import URL_MM_PROV_EXT_SHACL, URL_MM_PROV_SHACL
from rdflib import Dataset, Literal, URIRef
from rdflib.namespace import DCTERMS, PROV, RDF, SDO, TIME

from coord_dsl.generators.fsm import gen_json
from coord_dsl.rdf.provenance import build, render
from coord_dsl.rdf.vocab import URI_FSM_TYPE_FSM
from coord_dsl.registration import fsm_metamodel, gen_python

MODEL = (
    Path(__file__).resolve().parents[1] / "examples" / "models" / "fsm" / "example.fsm"
)
SHAPES = {URL_MM_PROV_SHACL: "turtle", URL_MM_PROV_EXT_SHACL: "turtle"}


class ProvenanceTest(unittest.TestCase):
    def setUp(self):
        self.model = fsm_metamodel().model_from_file(str(MODEL))
        temporary = TemporaryDirectory()
        self.addCleanup(temporary.cleanup)
        self.directory = Path(temporary.name).resolve()
        self.agent, version, revision, repository, dirty = get_pkg_info("coord_dsl")
        self.bundle = create_bundle(self.agent)
        load_pkg_prov(
            self.bundle, self.agent, "coord_dsl", version, revision, repository, dirty=dirty
        )

    def test_build_records_the_graph_generated_from_the_model(self):
        bundle = self.bundle
        graph = build(self.model, bundle)

        (activity,) = bundle.subjects(RDF.type, URI_PROV_EXT_TYPE_TRANSFORMATION)
        (entity,) = bundle.subjects(PROV.wasGeneratedBy, activity)
        (source,) = bundle.objects(activity, PROV.used)
        self.assertEqual(entity, graph.identifier)
        self.assertIsNotNone(bundle.value(source, DCTERMS.identifier))
        self.assertEqual(resolve_location(bundle, source), URIRef(MODEL.as_uri()))
        self.assertIn((activity, PROV.wasAssociatedWith, self.agent), bundle)
        self.assertIn((None, PROV.wasAttributedTo, self.agent), bundle)
        self.assertEqual(str(bundle.value(self.agent, SDO.name)), "coord_dsl")
        self.assertIsNotNone(bundle.value(activity, TIME.hasBeginning))
        self.assertIsNotNone(bundle.value(activity, TIME.hasEnd))
        commit, _, _, dirty = get_git_info(MODEL)
        revision = f"{commit}-dirty" if dirty else commit
        self.assertEqual(
            bundle.value(source, SDO.identifier), Literal(revision) if commit else None
        )
        check_shacl_constraints(bundle, SHAPES)

    def test_build_records_a_saved_file_as_derived_from_the_graph(self):
        graph_file = self.directory / "ex_fsm.ld.json"
        bundle = self.bundle
        graph = build(self.model, bundle, graph_file)

        (activity,) = bundle.subjects(RDF.type, URI_PROV_EXT_TYPE_TRANSFORMATION)
        (file_id,) = set(bundle.subjects(PROV.wasGeneratedBy, activity)) - {graph.identifier}
        self.assertIsNotNone(bundle.value(file_id, DCTERMS.identifier))
        self.assertIn((file_id, PROV.wasDerivedFrom, graph.identifier), bundle)
        self.assertEqual(resolve_location(bundle, file_id), URIRef(graph_file.as_uri()))
        saved = Dataset().parse(graph_file, format="json-ld")
        self.assertIn(graph.identifier, {g.identifier for g in saved.graphs()})
        check_shacl_constraints(bundle, SHAPES)

    def test_render_uses_the_graph_and_the_template(self):
        graph = build(self.model, create_bundle(self.agent))
        bundle = self.bundle
        output_file = render(graph, bundle, "cpp", self.directory / "ex_fsm.hpp")

        template = Path(str(files("coord_dsl").joinpath("templates/fsm.hpp.jinja2")))
        (activity,) = bundle.subjects(RDF.type, URI_PROV_EXT_TYPE_TRANSFORMATION)
        (entity,) = bundle.subjects(PROV.wasGeneratedBy, activity)
        (template_id,) = set(bundle.objects(activity, PROV.used)) - {graph.identifier}
        self.assertIsNotNone(bundle.value(entity, DCTERMS.identifier))
        self.assertIsNotNone(bundle.value(template_id, DCTERMS.identifier))
        self.assertEqual(resolve_location(bundle, entity), URIRef(output_file.as_uri()))
        self.assertEqual(resolve_location(bundle, template_id), URIRef(template.as_uri()))
        self.assertIn("ex_fsm", output_file.read_text())
        check_shacl_constraints(bundle, SHAPES)

    def test_saved_graph_keeps_the_declared_reaction_order(self):
        graph_file = self.directory / "ex_fsm.ld.json"
        build(self.model, self.bundle, graph_file)

        dataset =Dataset().parse(graph_file, format="json-ld")
        graph = next(g for g in dataset.graphs() if (None, RDF.type, URI_FSM_TYPE_FSM) in g)
        fsm_ref = graph.value(predicate=RDF.type, object=URI_FSM_TYPE_FSM)
        assert isinstance(fsm_ref, URIRef)
        self.assertEqual(
            [reaction["id"] for reaction in gen_json(graph, fsm_ref)["reactions_table"]],
            [reaction.name.replace("-", "_").upper() for reaction in self.model.fsm.reactions],
        )

    def test_generator_writes_only_the_code_by_default(self):
        output = self.directory / "ex_fsm.py"
        gen_python(None, self.model, output, False, False)
        self.assertEqual({path.name for path in self.directory.iterdir()}, {"ex_fsm.py"})

    def test_generator_records_both_steps_in_one_bundle_when_asked(self):
        output = self.directory / "ex_fsm.py"
        gen_python(None, self.model, output, False, False, provenance=True)
        self.assertEqual(
            {path.name for path in self.directory.iterdir()},
            {"ex_fsm.py", "ex_fsm.py.prov.ld.json"},
        )
        record = Dataset().parse(self.directory / "ex_fsm.py.prov.ld.json", format="json-ld")
        (bundle,) = [g for g in record.graphs() if (None, RDF.type, PROV.Bundle) in g]
        generated = set(bundle.subjects(PROV.wasGeneratedBy))
        used = set(bundle.objects(predicate=PROV.used))
        self.assertEqual(len(generated & used), 1)


if __name__ == "__main__":
    unittest.main()
