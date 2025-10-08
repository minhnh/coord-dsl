"""
This is an auto-generated file. Do not edit it directly.

FSM: example
FSM Description: Example of a simple FSM

Examples:

>>> from coord_dsl.fsm import fsm_step
>>> from coord_dsl.event_loop import reconfig_event_buffers
>>> from fsm_example import create_fsm
>>> fsm = create_fsm()
>>> while True:
...     if fsm.current_state_index == StateID.S_EXIT:
...         print("State machine completed successfully")
...         break
...     fsm_behavior(fsm, ud) # user-defined behaviour with user data
...     fsm_step(fsm)
...     reconfig_event_buffers(fsm.event_data)
"""

from enum import IntEnum, auto
from coord_dsl.event_loop import EventData
from coord_dsl.fsm import FSMData, Transition, EventReaction


# Event IDs
class EventID(IntEnum):
    E_CONFIGURE_ENTERED = 0
    E_CONFIGURE_EXIT = auto()
    E_IDLE_ENTERED = auto()
    E_IDLE_EXIT_EXECUTE = auto()
    E_IDLE_EXIT_COMPILE = auto()
    E_COMPILE_ENTERED = auto()
    E_COMPILE_EXIT = auto()
    E_EXECUTE_ENTERED = auto()
    E_EXECUTE_EXIT = auto()
    E_STEP = auto()


# State IDs
class StateID(IntEnum):
    S_START = 0
    S_CONFIGURE = auto()
    S_IDLE = auto()
    S_COMPILE = auto()
    S_EXECUTE = auto()
    S_EXIT = auto()


# Transition IDs
class TransitionID(IntEnum):
    T_START_CONFIGURE = 0
    T_CONFIGURE_IDLE = auto()
    T_IDLE_IDLE = auto()
    T_IDLE_EXECUTE = auto()
    T_IDLE_COMPILE = auto()
    T_COMPILE_EXECUTE = auto()
    T_EXECUTE_EXECUTE = auto()
    T_EXECUTE_IDLE = auto()


# Event reaction IDs
class ReactionID(IntEnum):
    R_E_CONFIGURE_EXIT = 0
    R_E_IDLE_EXIT_EXECUTE = auto()
    R_E_IDLE_EXIT_COMPILE = auto()
    R_E_COMPILE_EXIT = auto()
    R_E_EXECUTE_EXIT = auto()
    R_E_STEP1 = auto()
    R_E_STEP2 = auto()
    R_E_STEP3 = auto()


def create_fsm() -> FSMData:
    """Creates the FSM data structure."""
    # Transitions
    trans_dict = {
        TransitionID.T_START_CONFIGURE: Transition(
            StateID.S_START, StateID.S_CONFIGURE
        ),
        TransitionID.T_CONFIGURE_IDLE: Transition(StateID.S_CONFIGURE, StateID.S_IDLE),
        TransitionID.T_IDLE_IDLE: Transition(StateID.S_IDLE, StateID.S_IDLE),
        TransitionID.T_IDLE_EXECUTE: Transition(StateID.S_IDLE, StateID.S_EXECUTE),
        TransitionID.T_IDLE_COMPILE: Transition(StateID.S_IDLE, StateID.S_COMPILE),
        TransitionID.T_COMPILE_EXECUTE: Transition(
            StateID.S_COMPILE, StateID.S_EXECUTE
        ),
        TransitionID.T_EXECUTE_EXECUTE: Transition(
            StateID.S_EXECUTE, StateID.S_EXECUTE
        ),
        TransitionID.T_EXECUTE_IDLE: Transition(StateID.S_EXECUTE, StateID.S_IDLE),
    }
    trans_list = [trans_dict[i] for i in TransitionID]

    # Event Reactions
    evt_reaction_dict = {
        ReactionID.R_E_CONFIGURE_EXIT: EventReaction(
            condition_event_index=EventID.E_CONFIGURE_EXIT,
            transition_index=TransitionID.T_CONFIGURE_IDLE,
            fired_event_indices=[
                EventID.E_IDLE_ENTERED,
            ],
        ),
        ReactionID.R_E_IDLE_EXIT_EXECUTE: EventReaction(
            condition_event_index=EventID.E_IDLE_EXIT_EXECUTE,
            transition_index=TransitionID.T_IDLE_EXECUTE,
            fired_event_indices=[
                EventID.E_EXECUTE_ENTERED,
            ],
        ),
        ReactionID.R_E_IDLE_EXIT_COMPILE: EventReaction(
            condition_event_index=EventID.E_IDLE_EXIT_COMPILE,
            transition_index=TransitionID.T_IDLE_COMPILE,
            fired_event_indices=[
                EventID.E_COMPILE_ENTERED,
            ],
        ),
        ReactionID.R_E_COMPILE_EXIT: EventReaction(
            condition_event_index=EventID.E_COMPILE_EXIT,
            transition_index=TransitionID.T_COMPILE_EXECUTE,
            fired_event_indices=[
                EventID.E_EXECUTE_ENTERED,
            ],
        ),
        ReactionID.R_E_EXECUTE_EXIT: EventReaction(
            condition_event_index=EventID.E_EXECUTE_EXIT,
            transition_index=TransitionID.T_EXECUTE_IDLE,
            fired_event_indices=[
                EventID.E_IDLE_ENTERED,
            ],
        ),
        ReactionID.R_E_STEP1: EventReaction(
            condition_event_index=EventID.E_STEP,
            transition_index=TransitionID.T_START_CONFIGURE,
            fired_event_indices=[
                EventID.E_CONFIGURE_ENTERED,
            ],
        ),
        ReactionID.R_E_STEP2: EventReaction(
            condition_event_index=EventID.E_STEP,
            transition_index=TransitionID.T_IDLE_IDLE,
            fired_event_indices=[],
        ),
        ReactionID.R_E_STEP3: EventReaction(
            condition_event_index=EventID.E_STEP,
            transition_index=TransitionID.T_EXECUTE_EXECUTE,
            fired_event_indices=[],
        ),
    }
    evt_reaction_list = [evt_reaction_dict[i] for i in ReactionID]

    # Events
    events = EventData(len(EventID))

    # Return FSM Data
    return FSMData(
        event_data=events,
        num_states=len(StateID),
        start_state_index=StateID.S_START,
        end_state_index=StateID.S_EXIT,
        transitions=trans_list,
        event_reactions=evt_reaction_list,
        current_state_index=StateID.S_START,
    )
