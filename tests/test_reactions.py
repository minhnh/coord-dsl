# SPDX-License-Identifier: MPL-2.0
"""Tests for the checks on the order of an FSM's reactions."""

import unittest

from textx.exceptions import TextXSemanticError

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
        T_STAY { from: <S_A>, to: <S_A> },
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
    def test_rejects_reactions_hidden_by_their_order(self):
        cases = [
            (
                "same event from one start state",
                "R_1 { when: <events.E1>, do: <T_LEAVE> },"
                "R_2 { when: <events.E1>, do: <T_OTHER> }",
                "Multiple reactions to event 'E1' from state 'S_A': 'R_1' and 'R_2'; only the "
                "first can fire",
            ),
            (
                "self-transition before a reaction leaving its state",
                "R_1 { when: <events.E1>, do: <T_STAY> },"
                "R_2 { when: <events.E2>, do: <T_LEAVE> }",
                "Self-transition reaction 'R_1' is listed before 'R_2', which leaves 'S_A'",
            ),
        ]
        for name, reactions, message in cases:
            with self.subTest(name):
                with self.assertRaisesRegex(TextXSemanticError, message):
                    fsm_metamodel().model_from_str(MODEL_START + reactions + MODEL_END)

    def test_accepts_reactions_that_can_all_fire(self):
        cases = [
            (
                "self-transition after a reaction leaving its state",
                "R_1 { when: <events.E2>, do: <T_LEAVE> },"
                "R_2 { when: <events.E1>, do: <T_STAY> }",
            ),
            (
                "same event from different start states",
                "R_1 { when: <events.E1>, do: <T_LEAVE> },"
                "R_2 { when: <events.E1>, do: <T_END> }",
            ),
        ]
        for name, reactions in cases:
            with self.subTest(name):
                model = fsm_metamodel().model_from_str(MODEL_START + reactions + MODEL_END)
                self.assertEqual([r.name for r in model.fsm.reactions], ["R_1", "R_2"])


if __name__ == "__main__":
    unittest.main()
