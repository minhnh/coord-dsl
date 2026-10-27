# SPDX-License-Identifier: MPL-2.0
# SPDX-FileCopyrightText: 2026 SECORO AG (secoro.uni-bremen.de)
# Author: Vamsi Kalagaturu

from uuid import uuid4

from rdf_utils.namespace import URL_SECORO_MM
from rdflib import Graph, Literal, RDF, URIRef
from rdf_utils.models.vocab import (
    URI_EL_PRED_EVT_LOOP,
    URI_EL_PRED_HAS_EVT_REACT,
    URI_EL_PRED_REF_EVT,
    URI_EL_TYPE_EVT_REACT,
)

from coord_dsl.classes.fsm import FSM
from coord_dsl.rdf.event_loop import add_event_loop
from coord_dsl.rdf.vocab import (
    NS_MM_FSM,
    URI_FSM_PRED_CURRENT_STATE,
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
    URI_FSM_TYPE_FSM,
    URI_FSM_TYPE_REACTION,
    URI_FSM_TYPE_STATE,
    URI_FSM_TYPE_TRANSITION,
)


URL_FSM_SHACL = f"{URL_SECORO_MM}/behaviour/fsm.shacl.ttl"


def get_fsm_graph(model) -> tuple[Graph, URIRef]:
    fsm = getattr(model, "fsm", None)
    assert isinstance(fsm, FSM), "Model does not contain an FSM definition"

    graph = Graph(identifier=URIRef(uuid4().urn))
    add_event_loop(graph=graph, event_loop=fsm.event_loop)
    graph.bind("fsm", NS_MM_FSM)
    graph.bind(fsm.ns_prefix, fsm.namespace)

    assert fsm.uri is not None, "FSM must have a URI"

    graph.add((fsm.uri, RDF.type, URI_FSM_TYPE_FSM))
    graph.add((fsm.uri, URI_FSM_PRED_NAME, Literal(fsm.name)))
    if fsm.description:
        graph.add((fsm.uri, URI_FSM_PRED_DESCRIPTION, Literal(fsm.description)))

    graph.add((fsm.uri, URI_FSM_PRED_START_STATE, fsm.start_state.uri))
    graph.add((fsm.uri, URI_FSM_PRED_END_STATE, fsm.end_state.uri))
    graph.add((fsm.uri, URI_FSM_PRED_CURRENT_STATE, fsm.start_state.uri))
    graph.add((fsm.uri, URI_EL_PRED_EVT_LOOP, fsm.event_loop.uri))

    for state in fsm.states:
        graph.add((state.uri, RDF.type, URI_FSM_TYPE_STATE))
        graph.add((fsm.uri, URI_FSM_PRED_STATES, state.uri))

    for transition in fsm.transitions:
        graph.add((transition.uri, RDF.type, URI_FSM_TYPE_TRANSITION))
        graph.add((fsm.uri, URI_FSM_PRED_TRANSITIONS, transition.uri))
        graph.add(
            (
                transition.uri,
                URI_FSM_PRED_TRANSITION_FROM,
                transition.from_state.uri,
            )
        )
        graph.add(
            (
                transition.uri,
                URI_FSM_PRED_TRANSITION_TO,
                transition.to_state.uri,
            )
        )

    for reaction in fsm.reactions:
        graph.add((reaction.uri, RDF.type, URI_FSM_TYPE_REACTION))
        graph.add((reaction.uri, RDF.type, URI_EL_TYPE_EVT_REACT))
        graph.add((fsm.event_loop.uri, URI_EL_PRED_HAS_EVT_REACT, reaction.uri))
        graph.add((fsm.uri, URI_FSM_PRED_REACTIONS, reaction.uri))
        graph.add((reaction.uri, URI_EL_PRED_REF_EVT, reaction.when.uri))
        graph.add((reaction.uri, URI_FSM_PRED_DO_TRANSITION, reaction.do.uri))
        for fired_event in reaction.fired_events:
            graph.add(
                (
                    reaction.uri,
                    URI_FSM_PRED_FIRES_EVENTS,
                    fired_event.uri,
                )
            )

    return graph, fsm.uri
