# SPDX-License-Identifier: MPL-2.0
"""RDF generation for event loops."""

from rdf_utils.models.vocab import (
    URI_EL_PRED_HAS_EVT,
    URI_EL_TYPE_EVT_LOOP,
    URI_TIME_TYPE_INSTANT,
)
from rdf_utils.namespace import NS_MM_EL, NS_OWL_TIME, URL_SECORO_MM
from rdflib import RDF, Graph

from coord_dsl.classes.event_loop import EventLoop

URL_EVT_LOOP_SHACL = f"{URL_SECORO_MM}/behaviour/event_loop.shacl.ttl"


def add_event_loop(graph: Graph, event_loop: EventLoop) -> None:
    graph.bind("el", NS_MM_EL)
    graph.bind("time", NS_OWL_TIME)
    graph.bind(event_loop.ns_prefix, event_loop.namespace)

    graph.add((event_loop.uri, RDF.type, URI_EL_TYPE_EVT_LOOP))
    for event in event_loop.events:
        graph.add((event.uri, RDF.type, URI_TIME_TYPE_INSTANT))
        graph.add((event_loop.uri, URI_EL_PRED_HAS_EVT, event.uri))
