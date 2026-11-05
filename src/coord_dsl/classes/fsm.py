# SPDX-License-Identifier: MPL-2.0
# SPDX-FileCopyrightText: 2026 SECORO AG (secoro.uni-bremen.de)
# Author: Vamsi Kalagaturu

from typing import Optional

from textx import get_location
from textx.exceptions import TextXSemanticError

from coord_dsl.classes.common import IHasNamespaceDeclare, IInheritNamespace
from coord_dsl.classes.event_loop import Event, EventLoop, EventRef


class State(IInheritNamespace):
    pass


class Transition(IInheritNamespace):
    def __init__(self, parent, name, from_state, to_state):
        super().__init__(parent=parent, name=name)
        self.from_state: State = from_state
        self.to_state: State = to_state


class Reaction(IInheritNamespace):
    def __init__(self, parent, name, when, do, fires):
        super().__init__(parent=parent, name=name)
        self.when: Event = when
        self.do: Transition = do
        self.fires: list[EventRef] = fires

    @property
    def fired_events(self) -> list[Event]:
        return [f.event for f in self.fires if f.event is not None]


class FSM(IHasNamespaceDeclare):
    def __init__(
        self,
        parent,
        ns,
        name,
        description,
        states,
        start_state,
        end_state,
        event_loop,
        transitions,
        reactions,
    ):
        super().__init__(parent=parent, ns=ns, name=name)
        self.description: Optional[str] = description
        self.states: list[State] = states
        self.start_state: State = start_state
        self.end_state: State = end_state
        self.event_loop: EventLoop = event_loop
        self.transitions: list[Transition] = transitions
        self.reactions: list[Reaction] = reactions

        for transition in transitions:
            if transition.from_state is transition.to_state:
                raise TextXSemanticError(
                    f"Transition '{transition.name}' goes from state "
                    f"'{transition.from_state.name}' to itself. Self-transitions are not needed, "
                    "as the state does not change when no reaction fires.",
                    **get_location(transition),
                )

        # Ensure the reaction specifications are valid.
        first_by_trigger = {}
        for reaction in reactions:
            from_state = reaction.do.from_state
            first = first_by_trigger.setdefault((id(from_state), id(reaction.when)), reaction)
            if first is not reaction:
                raise TextXSemanticError(
                    f"Multiple reactions to event '{reaction.when.name}' from state "
                    f"'{from_state.name}': '{first.name}' and '{reaction.name}'; only the "
                    "first can fire.",
                    **get_location(reaction),
                )
