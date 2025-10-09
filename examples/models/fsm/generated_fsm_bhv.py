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


def fsm_behavior(fsm: FSMData, ud: UserData):
    cs = fsm.current_state_index
    if (
        consume_event(fsm.event_data, EventID.E_CONFIGURE_ENTERED)
        or consume_event(fsm.event_data, EventID.E_IDLE_ENTERED)
        or consume_event(fsm.event_data, EventID.E_COMPILE_ENTERED)
        or consume_event(fsm.event_data, EventID.E_EXECUTE_ENTERED)
    ):
        print(f"Entered state '{StateID(cs).name}'")

    ud.current_time = time.time()
    assert ud.transition_time is not None
    if ud.current_time < ud.transition_time:
        return

    if cs == StateID.S_CONFIGURE:
        print(f"Producing E_CONFIGURE_EXIT from state '{StateID(cs).name}'")
        produce_event(fsm.event_data, EventID.E_CONFIGURE_EXIT)
    elif cs == StateID.S_IDLE:
        if ud.compile:
            print(f"Producing E_IDLE_EXIT_COMPILE from state '{StateID(cs).name}'")
            produce_event(fsm.event_data, EventID.E_IDLE_EXIT_COMPILE)
        else:
            print(f"Producing E_IDLE_EXIT_EXECUTE from state '{StateID(cs).name}'")
            produce_event(fsm.event_data, EventID.E_IDLE_EXIT_EXECUTE)
        # Toggle compile flag for next time
        ud.compile = not ud.compile
    elif cs == StateID.S_COMPILE:
        print(f"Producing E_COMPILE_EXIT from state '{StateID(cs).name}'")
        produce_event(fsm.event_data, EventID.E_COMPILE_EXIT)
    elif cs == StateID.S_EXECUTE:
        print(f"Producing E_EXECUTE_EXIT from state '{StateID(cs).name}'")
        produce_event(fsm.event_data, EventID.E_EXECUTE_EXIT)

    # ensure loop period
    while ud.transition_time < ud.current_time:
        ud.transition_time += ud.state_duration


def main(state_duration_sec: float):
    signal.signal(signal.SIGINT, signal_handler)

    print("Starting generated FSM example. Press Ctrl+C to exit.")
    fsm = create_fsm()
    now = time.time()
    ud = UserData(current_time=now, state_duration=state_duration_sec)
    while True:
        if fsm.current_state_index == StateID.S_EXIT:
            print("State machine completed successfully")
            break

        produce_event(fsm.event_data, EventID.E_STEP)

        fsm_behavior(fsm, ud)
        fsm_step(fsm)

        reconfig_event_buffers(fsm.event_data)

        time.sleep(0.01)


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
