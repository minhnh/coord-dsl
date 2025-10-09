#!/usr/bin/env python3
# SPDX-License-Identifier: MPL-2.0
import time
from enum import IntEnum, auto
from dataclasses import dataclass
from coord_dsl.event_loop import (
    EventData,
    produce_event,
    consume_event,
    reconfig_event_buffers,
)
from coord_dsl.fsm import FSMData, Transition, EventReaction, fsm_step


class EventID(IntEnum):
    STEP = 0
    LIGHT_CHANGED = auto()
    SINGLE_LIGHT_TIMEOUT = auto()
    GLOBAL_TIMEOUT = auto()


class StateID(IntEnum):
    START = 0
    RED = auto()
    RED_YELLOW = auto()
    GREEN = auto()
    GREEN_YELLOW = auto()
    EXIT = auto()


class TransitionID(IntEnum):
    START_RED = 0
    RED_EXIT = auto()
    RED_RED = auto()
    RED_YELLOW = auto()
    RED_YELLOW_EXIT = auto()
    RED_YELLOW_YELLOW = auto()
    RED_YELLOW_GREEN = auto()
    GREEN_EXIT = auto()
    GREEN_GREEN = auto()
    GREEN_YELLOW = auto()
    GREEN_YELLOW_EXIT = auto()
    GREEN_YELLOW_YELLOW = auto()
    GREEN_YELLOW_RED = auto()


class ReactionID(IntEnum):
    GLOBAL_TIMER_RED = 0
    GLOBAL_TIMER_RED_YELLOW = auto()
    GLOBAL_TIMER_GREEN = auto()
    GLOBAL_TIMER_GREEN_YELLOW = auto()
    SINGLE_LIGHT_TIMEOUT_RED = auto()
    SINGLE_LIGHT_TIMEOUT_RED_YELLOW = auto()
    SINGLE_LIGHT_TIMEOUT_GREEN = auto()
    SINGLE_LIGHT_TIMEOUT_GREEN_YELLOW = auto()
    ALWAYS_TRUE_START = auto()
    ALWAYS_TRUE_RED = auto()
    ALWAYS_TRUE_RED_YELLOW = auto()
    ALWAYS_TRUE_GREEN = auto()
    ALWAYS_TRUE_GREEN_YELLOW = auto()


@dataclass
class UserData:
    redOn: bool = False
    yellowOn: bool = False
    greenOn: bool = False


def generic_behavior(user_data: UserData):
    r = "x" if user_data.redOn else " "
    y = "x" if user_data.yellowOn else " "
    g = "x" if user_data.greenOn else " "
    print(f"lights: r=[{r}] y=[{y}] g=[{g}]")


def red_behavior(u: UserData):
    u.redOn, u.yellowOn, u.greenOn = True, False, False


def red_yel_behavior(u: UserData):
    u.redOn, u.yellowOn, u.greenOn = True, True, False


def green_behavior(u: UserData):
    u.redOn, u.yellowOn, u.greenOn = False, False, True


def green_yel_behavior(u: UserData):
    u.redOn, u.yellowOn, u.greenOn = False, True, True


def fsm_behavior(fsm: FSMData, user_data: UserData):
    cs = fsm.current_state_index
    if cs == StateID.RED:
        red_behavior(user_data)
    elif cs == StateID.RED_YELLOW:
        red_yel_behavior(user_data)
    elif cs == StateID.GREEN:
        green_behavior(user_data)
    elif cs == StateID.GREEN_YELLOW:
        green_yel_behavior(user_data)

    if consume_event(fsm.event_data, EventID.LIGHT_CHANGED):
        generic_behavior(user_data)


def main(global_timeout_secs: float, single_light_timeout_secs: float):
    transitions_dict = {
        TransitionID.START_RED: Transition(StateID.START, StateID.RED),
        TransitionID.RED_EXIT: Transition(StateID.RED, StateID.EXIT),
        TransitionID.RED_RED: Transition(StateID.RED, StateID.RED),
        TransitionID.RED_YELLOW: Transition(StateID.RED, StateID.RED_YELLOW),
        TransitionID.RED_YELLOW_EXIT: Transition(StateID.RED_YELLOW, StateID.EXIT),
        TransitionID.RED_YELLOW_YELLOW: Transition(
            StateID.RED_YELLOW, StateID.RED_YELLOW
        ),
        TransitionID.RED_YELLOW_GREEN: Transition(StateID.RED_YELLOW, StateID.GREEN),
        TransitionID.GREEN_EXIT: Transition(StateID.GREEN, StateID.EXIT),
        TransitionID.GREEN_GREEN: Transition(StateID.GREEN, StateID.GREEN),
        TransitionID.GREEN_YELLOW: Transition(StateID.GREEN, StateID.GREEN_YELLOW),
        TransitionID.GREEN_YELLOW_EXIT: Transition(StateID.GREEN_YELLOW, StateID.EXIT),
        TransitionID.GREEN_YELLOW_YELLOW: Transition(
            StateID.GREEN_YELLOW, StateID.GREEN_YELLOW
        ),
        TransitionID.GREEN_YELLOW_RED: Transition(StateID.GREEN_YELLOW, StateID.RED),
    }
    transitions = [transitions_dict[tid] for tid in TransitionID]

    reactions_dict = {
        ReactionID.GLOBAL_TIMER_RED: EventReaction(
            EventID.GLOBAL_TIMEOUT, TransitionID.RED_EXIT, []
        ),
        ReactionID.GLOBAL_TIMER_RED_YELLOW: EventReaction(
            EventID.GLOBAL_TIMEOUT, TransitionID.RED_YELLOW_EXIT, []
        ),
        ReactionID.GLOBAL_TIMER_GREEN: EventReaction(
            EventID.GLOBAL_TIMEOUT, TransitionID.GREEN_EXIT, []
        ),
        ReactionID.GLOBAL_TIMER_GREEN_YELLOW: EventReaction(
            EventID.GLOBAL_TIMEOUT, TransitionID.GREEN_YELLOW_EXIT, []
        ),
        ReactionID.SINGLE_LIGHT_TIMEOUT_RED: EventReaction(
            EventID.SINGLE_LIGHT_TIMEOUT,
            TransitionID.RED_YELLOW,
            [EventID.LIGHT_CHANGED],
        ),
        ReactionID.SINGLE_LIGHT_TIMEOUT_RED_YELLOW: EventReaction(
            EventID.SINGLE_LIGHT_TIMEOUT,
            TransitionID.RED_YELLOW_GREEN,
            [EventID.LIGHT_CHANGED],
        ),
        ReactionID.SINGLE_LIGHT_TIMEOUT_GREEN: EventReaction(
            EventID.SINGLE_LIGHT_TIMEOUT,
            TransitionID.GREEN_YELLOW,
            [EventID.LIGHT_CHANGED],
        ),
        ReactionID.SINGLE_LIGHT_TIMEOUT_GREEN_YELLOW: EventReaction(
            EventID.SINGLE_LIGHT_TIMEOUT,
            TransitionID.GREEN_YELLOW_RED,
            [EventID.LIGHT_CHANGED],
        ),
        ReactionID.ALWAYS_TRUE_START: EventReaction(
            EventID.STEP, TransitionID.START_RED, []
        ),
        ReactionID.ALWAYS_TRUE_RED: EventReaction(
            EventID.STEP, TransitionID.RED_RED, []
        ),
        ReactionID.ALWAYS_TRUE_RED_YELLOW: EventReaction(
            EventID.STEP, TransitionID.RED_YELLOW_YELLOW, []
        ),
        ReactionID.ALWAYS_TRUE_GREEN: EventReaction(
            EventID.STEP, TransitionID.GREEN_GREEN, []
        ),
        ReactionID.ALWAYS_TRUE_GREEN_YELLOW: EventReaction(
            EventID.STEP, TransitionID.GREEN_YELLOW_YELLOW, []
        ),
    }
    event_reactions = [reactions_dict[rid] for rid in ReactionID]

    events = EventData(len(EventID))
    user_data = UserData()
    fsm = FSMData(
        event_data=events,
        num_states=len(StateID),
        start_state_index=StateID.START,
        end_state_index=StateID.EXIT,
        transitions=transitions,
        event_reactions=event_reactions,
    )

    start_time = time.time()
    last_light_time = start_time

    print("Starting traffic light example")
    while True:
        if fsm.current_state_index == StateID.EXIT:
            print("State machine completed successfully")
            break

        produce_event(fsm.event_data, EventID.STEP)

        now = time.time()

        if now - last_light_time > single_light_timeout_secs:
            produce_event(events, EventID.SINGLE_LIGHT_TIMEOUT)
            last_light_time = now

        if now - start_time > global_timeout_secs:
            produce_event(events, EventID.GLOBAL_TIMEOUT)

        fsm_behavior(fsm, user_data)
        fsm_step(fsm)
        reconfig_event_buffers(events)

        time.sleep(0.01)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="Traffic Light FSM Example",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "--global-timeout",
        "-g",
        type=float,
        default=10.0,
        help="Global timeout in seconds",
    )
    parser.add_argument(
        "--single-light-timeout",
        "-s",
        type=float,
        default=0.5,
        help="Timeout in seconds for each light",
    )
    args = parser.parse_args()
    main(args.global_timeout, args.single_light_timeout)
