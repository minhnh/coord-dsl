# SPDX-License-Identifier: MPL-2.0
class EventData:
    def __init__(self, num_events):
        self.num_events = num_events
        self.current_events = [False] * num_events
        self.future_events = [False] * num_events


def produce_event(event_data: EventData, event_index: int):
    assert event_data.future_events is not None, "Event buffers not initialized"
    assert (
        0 <= event_index < event_data.num_events
    ), f"Event index '{event_index}' out of range [0, {event_data.num_events})"
    event_data.future_events[event_index] = True


def consume_event(event_data: EventData, event_index: int) -> bool:
    assert event_data.current_events is not None, "Event buffers not initialized"
    assert (
        0 <= event_index < event_data.num_events
    ), f"Event index '{event_index}' out of range [0, {event_data.num_events})"
    return event_data.current_events[event_index]


def reconfig_event_buffers(event_data: EventData):
    assert (
        event_data.future_events is not None and event_data.current_events is not None
    ), "Event buffers not initialized"

    # swap current and future event buffers
    event_data.current_events, event_data.future_events = (
        event_data.future_events,
        event_data.current_events,
    )

    # reset all future events
    for i in range(event_data.num_events):
        event_data.future_events[i] = False
