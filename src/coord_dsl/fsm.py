# SPDX-License-Identifier: MPL-2.0
from dataclasses import dataclass
from coord_dsl.event_loop import EventData, produce_event, consume_event


@dataclass
class Transition:
    start_state_index: int
    end_state_index: int


@dataclass
class EventReaction:
    condition_event_index: int
    transition_index: int
    fired_event_indices: list[int]


@dataclass
class FSMData:
    event_data: EventData
    num_states: int
    start_state_index: int
    end_state_index: int
    transitions: list[Transition]
    event_reactions: list[EventReaction]
    current_state_index: int | None = None

    def __post_init__(self):
        if self.current_state_index is None:
            self.current_state_index = self.start_state_index


def fsm_step(fsm: FSMData):
    assert fsm.num_states > 0, "FSMData must have at least one state"
    assert fsm.current_state_index is not None
    assert 0 <= fsm.start_state_index < fsm.num_states
    assert 0 <= fsm.end_state_index < fsm.num_states
    assert 0 <= fsm.current_state_index < fsm.num_states

    # Exit if end state is reached
    if fsm.current_state_index == fsm.end_state_index:
        return

    # Process reactions in order (priority by list order)
    for reaction in fsm.event_reactions:
        # Skip if event condition not triggered
        if not consume_event(fsm.event_data, reaction.condition_event_index):
            continue

        trans_index = reaction.transition_index
        assert (
            0 <= trans_index < len(fsm.transitions)
        ), f"Transition index '{trans_index}' out of range [0, {len(fsm.transitions)})"

        transition = fsm.transitions[trans_index]

        # Skip if current state doesn't match transition's start state
        if fsm.current_state_index != transition.start_state_index:
            continue

        # Perform the transition
        assert (
            0 <= transition.end_state_index < fsm.num_states
        ), f"Transition end state index '{transition.end_state_index}' out of range [0, {fsm.num_states})"
        fsm.current_state_index = transition.end_state_index

        # Fire any resulting events
        for idx in reaction.fired_event_indices:
            produce_event(fsm.event_data, idx)

        # Stop after the first matching reaction
        # This implies that the order of reactions and reactions signifies the priority in which
        # they're handled, and that only the first transition will be taken into account.
        break
