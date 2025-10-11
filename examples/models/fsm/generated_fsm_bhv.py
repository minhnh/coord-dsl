#!/usr/bin/env python3
"""Example of using a generated FSM with custom behavior in Python.

SPDX-License-Identifier: MPL-2.0
"""

import signal
import sys
from dataclasses import dataclass
import time
from coord_dsl.event_loop import (
    produce_event,
    consume_event,
    reconfig_event_buffers,
)
from coord_dsl.fsm import FSMData, fsm_step
from fsm_example import EventID, StateID, create_fsm


LOOP_DURATION = 0.01


def signal_handler(sig, frame):
    print("You pressed Ctrl+C, exiting!")
    sys.exit(0)


@dataclass
class UserData:
    current_time: float
    state_duration: float
    compile: bool = True
    transition_time: float | None = None

    def __post_init__(self):
        if self.transition_time is None:
            self.transition_time = self.current_time + self.state_duration


def generic_on_end(fsm: FSMData, ud: UserData, end_events: list[EventID]):
    print(f"State '{StateID(fsm.current_state_index).name}' finished")
    for evt in end_events:
        produce_event(fsm.event_data, evt)


def idle_on_end(fsm: FSMData, ud: UserData):
    if ud.compile:
        generic_on_end(fsm, ud, [EventID.E_IDLE_EXIT_COMPILE])
    else:
        generic_on_end(fsm, ud, [EventID.E_IDLE_EXIT_EXECUTE])

    # Toggle compile flag for next time
    ud.compile = not ud.compile


def generic_step(fsm: FSMData, ud: UserData, start_event: EventID) -> bool:
    """Return True if timeout has occurred, i.e., state finished."""
    if consume_event(fsm.event_data, start_event):
        print(f"Entered state '{StateID(fsm.current_state_index).name}'")

    ud.current_time = time.time()
    assert ud.transition_time is not None
    if ud.current_time < ud.transition_time:
        return False

    # ensure loop period
    while ud.transition_time < ud.current_time:
        ud.transition_time += ud.state_duration
    return True


def fsm_behavior(fsm: FSMData, ud: UserData, bhv_data: dict):
    cs = fsm.current_state_index
    # print(f"Current state: '{StateID(fsm.current_state_index).name}'")
    if cs not in bhv_data:
        return

    bhv_data_cs = bhv_data[cs]
    assert "step" in bhv_data_cs, f"no step defined for state: {cs}"
    if not bhv_data_cs["step"](fsm, ud):
        # not done
        return

    if "on_end" in bhv_data_cs:
        bhv_data_cs["on_end"](fsm, ud)


def main(state_duration_sec: float):
    signal.signal(signal.SIGINT, signal_handler)

    print("Starting generated FSM example. Press Ctrl+C to exit.")
    fsm = create_fsm()
    fsm_bhv = {
        StateID.S_CONFIGURE: {
            "step": lambda fsm, ud: generic_step(
                fsm, ud, EventID.E_CONFIGURE_ENTERED
            ),
            "on_end": lambda fsm, ud: generic_on_end(
                fsm, ud, [EventID.E_CONFIGURE_EXIT]
            ),
        },
        StateID.S_IDLE: {
            "step": lambda fsm, ud: generic_step(
                fsm, ud, EventID.E_IDLE_ENTERED
            ),
            "on_end": idle_on_end,
        },
        StateID.S_COMPILE: {
            "step": lambda fsm, ud: generic_step(
                fsm, ud, EventID.E_COMPILE_ENTERED
            ),
            "on_end": lambda fsm, ud: generic_on_end(fsm, ud, [EventID.E_COMPILE_EXIT]),
        },
        StateID.S_EXECUTE: {
            "step": lambda fsm, ud: generic_step(
                fsm, ud, EventID.E_EXECUTE_ENTERED
            ),
            "on_end": lambda fsm, ud: generic_on_end(fsm, ud, [EventID.E_EXECUTE_EXIT]),
        },
    }

    now = time.time()
    ud = UserData(current_time=now, state_duration=state_duration_sec)
    loop_timeout = now + LOOP_DURATION
    while True:
        if fsm.current_state_index == StateID.S_EXIT:
            print("State machine completed successfully")
            break

        # Ensure loop rate & produce step event
        reconfig_event_buffers(fsm.event_data)
        while now < loop_timeout:
            now = time.time()
        while loop_timeout < now:
            loop_timeout += LOOP_DURATION
        produce_event(fsm.event_data, EventID.E_STEP)

        # FSM behaviour
        fsm_behavior(fsm, ud, fsm_bhv)

        # State transitions
        reconfig_event_buffers(fsm.event_data)
        fsm_step(fsm)


if __name__ == "__main__":
    import argparse

    parser = argparse.ArgumentParser(
        description="Test generated FSM Example",
        formatter_class=argparse.ArgumentDefaultsHelpFormatter,
    )
    parser.add_argument(
        "--state-duration",
        "-s",
        type=float,
        default=0.5,
        help="Duration in seconds to sleep in each state",
    )
    args = parser.parse_args()
    main(args.state_duration)
