# SPDX-License-Identifier: MPL-2.0
# SPDX-FileCopyrightText: 2026 SECORO AG (secoro.uni-bremen.de)
# Author: Vamsi Kalagaturu

from jinja2 import Environment, FileSystemLoader
from os.path import basename
from pathlib import Path
from rdflib import Graph, URIRef
from rdflib.collection import Collection
from rdf_utils.models.vocab import (
    URI_EL_PRED_EVT_LOOP,
    URI_EL_PRED_HAS_EVT,
    URI_EL_PRED_REF_EVT,
)
from rdf_utils.naming import get_valid_var_name

from coord_dsl.rdf.vocab import (
    URI_FSM_PRED_DESCRIPTION,
    URI_FSM_PRED_DO_TRANSITION,
    URI_FSM_PRED_END_STATE,
    URI_FSM_PRED_FIRES_EVENTS,
    URI_FSM_PRED_NAME,
    URI_FSM_PRED_REACTIONS,
    URI_FSM_PRED_START_STATE,
    URI_FSM_PRED_STATES,
    URI_FSM_PRED_TRANSITION_FROM,
    URI_FSM_PRED_TRANSITION_TO,
    URI_FSM_PRED_TRANSITIONS,
)


def local_name(uri: str) -> str:
    return basename(uri.replace("#", "/").rstrip("/"))


def gen_json(g: Graph, fsm_ref: URIRef) -> dict:
    assert isinstance(fsm_ref, URIRef)

    name_node = g.value(fsm_ref, URI_FSM_PRED_NAME)
    assert name_node is not None
    name = str(name_node)
    description_node = g.value(fsm_ref, URI_FSM_PRED_DESCRIPTION)
    description = str(description_node) if description_node is not None else None

    start_state_node = g.value(fsm_ref, URI_FSM_PRED_START_STATE)
    assert isinstance(start_state_node, URIRef)
    start_state = get_valid_var_name(local_name(start_state_node.toPython())).upper()

    end_state_node = g.value(fsm_ref, URI_FSM_PRED_END_STATE)
    assert isinstance(end_state_node, URIRef)
    end_state = get_valid_var_name(local_name(end_state_node.toPython())).upper()

    states = []
    state_uris = {}
    for _, _, state_uri in g.triples((fsm_ref, URI_FSM_PRED_STATES, None)):
        assert isinstance(state_uri, URIRef)
        uri_s = state_uri.toPython()
        ident = get_valid_var_name(local_name(uri_s)).upper()
        states.append(ident)
        state_uris[ident] = uri_s

    events = []
    event_uris = {}
    event_loop = g.value(fsm_ref, URI_EL_PRED_EVT_LOOP)
    assert isinstance(event_loop, URIRef)
    for event_uri in g.objects(event_loop, URI_EL_PRED_HAS_EVT):
        assert isinstance(event_uri, URIRef)
        uri_s = event_uri.toPython()
        ident = get_valid_var_name(local_name(uri_s)).upper()
        events.append(ident)
        event_uris[ident] = uri_s

    transitions_table = []
    for _, _, tr_uri in g.triples((fsm_ref, URI_FSM_PRED_TRANSITIONS, None)):
        assert isinstance(tr_uri, URIRef)
        uri_s = tr_uri.toPython()
        from_state_node = g.value(tr_uri, URI_FSM_PRED_TRANSITION_FROM)
        assert isinstance(from_state_node, URIRef)
        from_state = get_valid_var_name(local_name(from_state_node.toPython())).upper()
        to_state_node = g.value(tr_uri, URI_FSM_PRED_TRANSITION_TO)
        assert isinstance(to_state_node, URIRef)
        to_state = get_valid_var_name(local_name(to_state_node.toPython())).upper()
        transitions_table.append(
            {
                "id": get_valid_var_name(local_name(uri_s)).upper(),
                "uri": uri_s,
                "from_state": from_state,
                "to_state": to_state,
            }
        )

    reactions_table = []
    for rx_uri in Collection(g, g.value(fsm_ref, URI_FSM_PRED_REACTIONS)):
        assert isinstance(rx_uri, URIRef)
        uri_s = rx_uri.toPython()
        when_event_node = g.value(rx_uri, URI_EL_PRED_REF_EVT)
        assert isinstance(when_event_node, URIRef)
        when_event = get_valid_var_name(local_name(when_event_node.toPython())).upper()
        do_transition_node = g.value(rx_uri, URI_FSM_PRED_DO_TRANSITION)
        assert isinstance(do_transition_node, URIRef)
        do_transition = get_valid_var_name(
            local_name(do_transition_node.toPython())
        ).upper()
        fires = []
        for _, _, ev_uri in g.triples((rx_uri, URI_FSM_PRED_FIRES_EVENTS, None)):
            assert isinstance(ev_uri, URIRef)
            fires.append(get_valid_var_name(local_name(ev_uri.toPython())).upper())
        reactions_table.append(
            {
                "id": get_valid_var_name(local_name(uri_s)).upper(),
                "uri": uri_s,
                "when_event": when_event,
                "do_transition": do_transition,
                "fires_events": fires,
                "num_fires": len(fires),
            }
        )

    result = {
        "name": name,
        "uri": str(fsm_ref),
        "description": description,
        "start_state": start_state,
        "end_state": end_state,
        "states": states,
        "state_uris": state_uris,
        "events": events,
        "event_uris": event_uris,
        "transitions_table": transitions_table,
        "reactions_table": reactions_table,
    }

    return result


def gen_cpp_header(ir: dict):
    """Generates a .hpp file with the FSM datastructures"""

    print(f"Generating C code for FSM: {ir['name']}")

    # get module path
    module_path = Path(__file__).parent.parent
    env = Environment(loader=FileSystemLoader(module_path / "templates"))
    template = env.get_template("fsm.hpp.jinja2")

    output = template.render(
        {
            "data": ir,
        }
    )

    return output


def gen_python_code(ir: dict):
    """Generates a .py file with the FSM datastructures"""

    print(f"Generating Python code for FSM: {ir['name']}")

    # get module path
    module_path = Path(__file__).parent.parent
    env = Environment(loader=FileSystemLoader(module_path / "templates"))
    template = env.get_template("fsm.py.jinja2")

    output = template.render(
        {
            "data": ir,
        }
    )

    return output
