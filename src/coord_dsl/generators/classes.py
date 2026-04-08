from typing import Optional
from coord_dsl.generators.common import IHasNamespaceDeclare, NamedNamespaceObject


class State(NamedNamespaceObject):
    pass

class Event(NamedNamespaceObject):
    pass


class Transition(NamedNamespaceObject):
    def __init__(self, parent, name, from_state, to_state):
        super().__init__(parent=parent, name=name)
        self.from_state: State = from_state
        self.to_state: State = to_state


class FiredEvent:
    def __init__(self, **kwargs):
        self.event: Optional[Event] = kwargs.get("event")


class Reaction(NamedNamespaceObject):
    def __init__(self, parent, name, when, do, fires):
        super().__init__(parent=parent, name=name)
        self.when: Event = when
        self.do: Transition = do
        self.fires: list[FiredEvent] = fires

    @property
    def fired_events(self) -> list[Event]:
        return [f.event for f in self.fires if f.event is not None]


class FSM(IHasNamespaceDeclare):
    def __init__(self, parent, ns, name, description, states, start_state, 
                 end_state, events, transitions, reactions):
        super().__init__(parent=parent, ns=ns, name=name)
        self.description: Optional[str] = description
        self.states: list[State] = states
        self.start_state: State = start_state
        self.end_state: State = end_state
        self.events: list[Event] = events
        self.transitions: list[Transition] = transitions
        self.reactions: list[Reaction] = reactions

    def _all_entities(self) -> list:
        return self.states + self.events + self.transitions + self.reactions
