# SPDX-License-Identifier: MPL-2.0
"""RDF vocabulary used by coord-dsl."""

from rdflib import Namespace
from rdf_utils.namespace import URL_SECORO_MM


NS_MM_FSM = Namespace(f"{URL_SECORO_MM}/behaviour/fsm#")

URI_FSM_TYPE_FSM = NS_MM_FSM["FiniteStateMachine"]
URI_FSM_TYPE_ORDERED_REACTIONS = NS_MM_FSM["OrderedReactions"]
URI_FSM_TYPE_STATE = NS_MM_FSM["State"]
URI_FSM_TYPE_TRANSITION = NS_MM_FSM["Transition"]
URI_FSM_TYPE_REACTION = NS_MM_FSM["Reaction"]

URI_FSM_PRED_NAME = NS_MM_FSM["name"]
URI_FSM_PRED_DESCRIPTION = NS_MM_FSM["description"]
URI_FSM_PRED_START_STATE = NS_MM_FSM["start-state"]
URI_FSM_PRED_END_STATE = NS_MM_FSM["end-state"]
URI_FSM_PRED_CURRENT_STATE = NS_MM_FSM["current-state"]
URI_FSM_PRED_STATES = NS_MM_FSM["states"]
URI_FSM_PRED_TRANSITIONS = NS_MM_FSM["transitions"]
URI_FSM_PRED_REACTIONS = NS_MM_FSM["reactions"]
URI_FSM_PRED_TRANSITION_FROM = NS_MM_FSM["transition-from"]
URI_FSM_PRED_TRANSITION_TO = NS_MM_FSM["transition-to"]
URI_FSM_PRED_DO_TRANSITION = NS_MM_FSM["do-transition"]
URI_FSM_PRED_FIRES_EVENTS = NS_MM_FSM["fires-events"]
