# SPDX-License-Identifier: MPL-2.0
# SPDX-FileCopyrightText: 2026 SECORO AG (secoro.uni-bremen.de)
# Author: Vamsi Kalagaturu
"""Render an FSM's RDF graph as graphviz."""

import shutil
import subprocess
from pathlib import Path

from rdflib.namespace import split_uri
from rdf_utils.collection import load_list_re
from rdf_utils.models.vocab import URI_EL_PRED_REF_EVT

from coord_dsl.rdf.vocab import (
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

FORMATS = ("png", "svg", "pdf")

_HEADER = [
    "  compound=true;",
    '  graph [fontname="Helvetica", fontsize=11];',
    '  node [fontname="Helvetica", fontsize=10, shape=box, style="rounded,filled", fillcolor="#ffffff"];',
    '  edge [fontname="Helvetica", fontsize=9, color="#5f6368"];',
]


def write_dot(dot_source, output_path, img_format):
    """Write DOT source, rendering it unless the requested format is ``dot``."""
    if img_format == "dot":
        Path(output_path).write_text(dot_source)
        return
    if shutil.which("dot") is None:
        raise ValueError(
            f"graphviz is needed to write {img_format!r}: no 'dot' on PATH"
        )
    subprocess.run(
        ["dot", f"-T{img_format}", "-o", str(output_path)],
        input=dot_source,
        text=True,
        check=True,
    )


def _esc(text) -> str:
    return str(text).replace("\\", "\\\\").replace('"', '\\"')


def _local(uri) -> str:
    return split_uri(uri)[1]


def _fsm_body(g, fsm_ref, indent, entry=True, awaited=(), colour=None):
    """The states and the reactions that join them, as dot lines."""
    start = g.value(fsm_ref, URI_FSM_PRED_START_STATE)
    end = g.value(fsm_ref, URI_FSM_PRED_END_STATE)
    lines = []

    if entry:
        lines.append(
            f'{indent}"__entry__" [shape=point, width=0.12, '
            'fillcolor="#202124", color="#202124"];'
        )
        lines.append(f'{indent}"__entry__" -> "{_esc(start)}";')
    for state in sorted(g.objects(fsm_ref, URI_FSM_PRED_STATES), key=str):
        attrs = [f'label="{_esc(_local(state))}"']
        if state == end:
            attrs.append('peripheries=2, fillcolor="#e6f4ea"')
        elif state == start:
            attrs.append('fillcolor="#e8f0fe"')
        if state in awaited:
            attrs.append(f'color="{colour}", penwidth=2')
        lines.append(f'{indent}"{_esc(state)}" [{", ".join(attrs)}];')

    reacted = set()
    for reaction in sorted(load_list_re(g, g.value(fsm_ref, URI_FSM_PRED_REACTIONS)), key=str):
        transition = g.value(reaction, URI_FSM_PRED_DO_TRANSITION)
        reacted.add(transition)
        label = [_local(g.value(reaction, URI_EL_PRED_REF_EVT))]
        fires = sorted(
            _local(e) for e in g.objects(reaction, URI_FSM_PRED_FIRES_EVENTS)
        )
        if fires:
            label.append("fires " + ", ".join(fires))
        text = "\\n".join(_esc(line) for line in label)
        lines.append(
            f'{indent}"{_esc(g.value(transition, URI_FSM_PRED_TRANSITION_FROM))}"'
            f' -> "{_esc(g.value(transition, URI_FSM_PRED_TRANSITION_TO))}"'
            f' [label="{text}"];'
        )
    for transition in sorted(g.objects(fsm_ref, URI_FSM_PRED_TRANSITIONS), key=str):
        if transition not in reacted:
            lines.append(
                f'{indent}"{_esc(g.value(transition, URI_FSM_PRED_TRANSITION_FROM))}"'
                f' -> "{_esc(g.value(transition, URI_FSM_PRED_TRANSITION_TO))}"'
                f' [label="{_esc(_local(transition))}", style=dashed, color="#9aa0a6",'
                ' fontcolor="#9aa0a6"];'
            )
    return lines


def fsm_dot(g, fsm_ref) -> str:
    """States as nodes, one edge per reaction: what fires it, and what it fires."""
    lines = [
        f'digraph "{_esc(g.value(fsm_ref, URI_FSM_PRED_NAME))}" {{',
        "  rankdir=LR;",
    ] + _HEADER
    lines += _fsm_body(g, fsm_ref, "  ")
    lines.append("}")
    return "\n".join(lines) + "\n"
