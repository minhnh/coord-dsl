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

        # A reaction listed earlier can stop a later one from the same state from firing.
        first_by_trigger = {}
        self_transition_by_state = {}
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
            if from_state is reaction.do.to_state:
                self_transition_by_state.setdefault(id(from_state), reaction)
                continue
            self_transition = self_transition_by_state.get(id(from_state))
            if self_transition is not None:
                raise TextXSemanticError(
                    f"Self-transition reaction '{self_transition.name}' is listed before "
                    f"'{reaction.name}', which leaves '{from_state.name}'; the self-transition "
                    "wins whenever both events are set.",
                    **get_location(self_transition),
                )
