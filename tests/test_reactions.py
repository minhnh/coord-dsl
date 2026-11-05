# SPDX-License-Identifier: MPL-2.0
"""Tests for the checks on the order of an FSM's reactions."""

import unittest

from rdf_utils.collection import add_node_list_pred
from rdf_utils.constraints import ConstraintViolation
from textx.exceptions import TextXSemanticError

from coord_dsl.generators.fsm import gen_json
from coord_dsl.rdf.fsm import get_fsm_graph
from coord_dsl.rdf.vocab import URI_FSM_PRED_REACTIONS
from coord_dsl.registration import fsm_metamodel


MODEL_START = """
ns ex = "https://example.test/"
evt loop (ns=ex) events { evt E1, evt E2 }
fsm (ns=ex) machine {
    states { S_A, S_B, S_C }
    evt loop: <events>
    start: <S_A>
    end: <S_C>
    transitions {
        T_LEAVE { from: <S_A>, to: <S_B> },
        T_OTHER { from: <S_A>, to: <S_C> },
        T_END { from: <S_B>, to: <S_C> }
    }
    reactions {
"""
MODEL_END = """
    }
}
"""


class CheckReactionsTest(unittest.TestCase):
    def test_rejects_multiple_reactions_to_one_event_from_one_state(self):
        reactions = (
            "R_1 { when: <events.E1>, do: <T_LEAVE> },"
            "R_2 { when: <events.E1>, do: <T_OTHER> }"
        )
        with self.assertRaisesRegex(
            TextXSemanticError,
            "Multiple reactions to event 'E1' from state 'S_A': 'R_1' and 'R_2'; only the "
            "first can fire",
        ):
            fsm_metamodel().model_from_str(MODEL_START + reactions + MODEL_END)

    def test_accepts_one_event_from_different_states(self):
        reactions = (
            "R_1 { when: <events.E1>, do: <T_LEAVE> },"
            "R_2 { when: <events.E1>, do: <T_END> }"
        )
        model = fsm_metamodel().model_from_str(MODEL_START + reactions + MODEL_END)
        self.assertEqual([r.name for r in model.fsm.reactions], ["R_1", "R_2"])

    def test_rejects_a_transition_from_a_state_to_itself(self):
        model = MODEL_START.replace(
            "T_LEAVE { from: <S_A>, to: <S_B> }", "T_STAY { from: <S_A>, to: <S_A> }"
        )
        with self.assertRaisesRegex(
            TextXSemanticError, "Transition 'T_STAY' goes from state 'S_A' to itself"
        ):
            fsm_metamodel().model_from_str(
                model + "R_1 { when: <events.E1>, do: <T_END> }" + MODEL_END
            )

    def test_rejects_two_reactions_with_one_name(self):
        reactions = (
            "R_1 { when: <events.E1>, do: <T_LEAVE> },"
            "R_1 { when: <events.E2>, do: <T_END> }"
        )
        with self.assertRaisesRegex(TextXSemanticError, "Multiple reactions named 'R_1'"):
            fsm_metamodel().model_from_str(MODEL_START + reactions + MODEL_END)

    def test_rejects_a_graph_listing_a_reaction_twice(self):
        model = fsm_metamodel().model_from_str(
            MODEL_START + "R_1 { when: <events.E1>, do: <T_LEAVE> }" + MODEL_END
        )
        graph, fsm_ref = get_fsm_graph(model)
        reaction = model.fsm.reactions[0].uri
        graph.remove((fsm_ref, URI_FSM_PRED_REACTIONS, None))
        add_node_list_pred(graph, fsm_ref, URI_FSM_PRED_REACTIONS, [reaction, reaction])
        with self.assertRaisesRegex(ConstraintViolation, "listed more than once"):
            gen_json(graph, fsm_ref)


if __name__ == "__main__":
    unittest.main()
