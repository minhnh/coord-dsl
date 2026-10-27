# coord-dsl

A [textX](https://textx.github.io/textX/) DSL for event-driven finite state
machines, with Python, C++, RDF, and graphviz generators.

## Installation

```bash
pip install "rdf_utils @ git+https://github.com/minhnh/rdf-utils.git"
pip install -e .
```

If both repositories are sibling checkouts, the first command can instead be
`pip install -e ../rdf-utils`.

## Model

The FSM design follows Prof. Herman Bruyninckx's
[Composable and Explainable Systems of Systems](https://robmosys.pages.gitlab.kuleuven.be/composable-and-explainable-systems-of-systems.pdf):
an FSM is represented as a pure data structure. A `.fsm` file contains:

- **states**: the stateful behaviours, including a `start` and an `end` state;
- **an event loop**: named events representing occurrences or monitored state
  changes to which the machine reacts;
- **transitions**: directed `from`/`to` relationships between states; and
- **reactions**: the policy relating an event to a transition and, optionally,
  further events to fire.

Each reaction matches one event from the referenced event loop. Event
compositions from the broader FSM design are not implemented.

The control loop and behaviour implementations are separate from the model.
The Python `coord_dsl` runtime and C++
[coord2b](https://github.com/rosym-project/coord2b) runtime apply reactions and
provide their event loops. References to model declarations are enclosed in
angle brackets.

An event loop is declared before the FSM as
`evt loop (ns=<namespace>) <name> { ... }`. Each comma-separated event uses
`evt <name>`. The FSM selects a loop with `evt loop: <loop>`, and reactions
refer to its events by fully qualified name, such as `<loop.EVENT>`, in both
`when` and `fires`.

```text
ns ex = "https://example.com/fsm/"

evt loop (ns=ex) example_events {
    evt E_START,
    evt E_STOP
}

fsm (ns=ex) example_fsm {
    description: "Example FSM"
    states { S_START, S_RUNNING, S_EXIT }
    evt loop: <example_events>
    start: <S_START>
    end: <S_EXIT>
    transitions {
        T_START { from: <S_START>, to: <S_RUNNING> },
        T_STOP  { from: <S_RUNNING>, to: <S_EXIT> }
    }
    reactions {
        R_START { when: <example_events.E_START>, do: <T_START> },
        R_STOP  { when: <example_events.E_STOP>, do: <T_STOP> }
    }
}
```

Reactions are ordered: each step applies the first reaction whose event is
present and whose transition starts at the current state. A namespace gives
the FSM and each of its parts a stable URI.

## Generation

```bash
textx generate example.fsm --target cpp -o model.hpp
textx generate example.fsm --target python -o model.py
textx generate example.fsm --target graph --format json-ld --autocompact  # writes example_fsm.ld.json beside example.fsm
textx generate example.fsm --target console --format trig
textx generate example.fsm --target dot --format png
```

Available targets:

- `cpp`: C++ header for the [coord2b](https://github.com/rosym-project/coord2b) runtime.
- `python`: Python module for the bundled `coord_dsl` runtime.
- `graph` / `console`: RDF in JSON-LD, N-Quads, or TriG.
- `dot` / `dot-console`: graphviz source or a PNG, SVG, or PDF rendering.

The RDF generators write the FSM graph as one named graph, named by a fresh
`urn:uuid:`, in the `--format` given: `json-ld` (default, `.ld.json`), `nquads`
(`.nq`) or `trig` (`.trig`). JSON-LD gets `indent=2`, and `auto_compact=True`
when `--autocompact` is present (`False` otherwise); RDFLib derives the
compacted context from the graph's namespace manager.

Generated code includes `FSM_URI` and URI tables for states, events,
transitions, and reactions. File generators also write their provenance to a
`<output>.prov.ld.json` beside their output, e.g. `model.hpp.prov.ld.json`,
replaced on each run.

See [examples/models/fsm](examples/models/fsm/) for a complete model and Python
and C++ controllers.
