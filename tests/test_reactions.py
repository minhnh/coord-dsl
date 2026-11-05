# SPDX-License-Identifier: MPL-2.0
"""Tests for the checks on the order of an FSM's reactions."""

import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

from textx import metamodel_for_language
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
                "state 'S_A' reacts to event 'E1' with 'R_1' and 'R_2' -- only the first can fire",
            ),
            (
                "self-transition before a reaction leaving its state",
                "R_1 { when: <events.E1>, do: <T_STAY> },"
                "R_2 { when: <events.E2>, do: <T_LEAVE> }",
                "self-transition reaction 'R_1' is listed before 'R_2', which leaves 'S_A'",
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

    def test_checks_an_imported_model(self):
        cases = [
            ("R_1 { when: <events.E1>, do: <T_LEAVE> }", None),
            (
                "R_1 { when: <events.E1>, do: <T_LEAVE> },"
                "R_2 { when: <events.E1>, do: <T_OTHER> }",
                "only the first can fire",
            ),
        ]
        for reactions, message in cases:
            with self.subTest(reactions), TemporaryDirectory() as directory:
                Path(directory, "imported.fsm").write_text(MODEL_START + reactions + MODEL_END)
                main = Path(directory, "main.fsm")
                main.write_text(
                    'import "imported.fsm"\n'
                    'ns ex = "https://example.test/"\n'
                    "fsm (ns=ex) importer {\n"
                    "    states { S_D, S_E }\n"
                    "    evt loop: <events>\n"
                    "    start: <S_D>\n"
                    "    end: <S_E>\n"
                    "    transitions { T_D { from: <S_D>, to: <S_E> } }\n"
                    "    reactions { R_D { when: <events.E1>, do: <T_D> } }\n"
                    "}\n"
                )
                metamodel = metamodel_for_language("coord_dsl_fsm")
                if message is None:
                    self.assertEqual(metamodel.model_from_file(main).fsm.name, "importer")
                else:
                    with self.assertRaisesRegex(TextXSemanticError, message):
                        metamodel.model_from_file(main)


if __name__ == "__main__":
    unittest.main()
