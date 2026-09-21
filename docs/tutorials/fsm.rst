Tutorial: FSM
=============

An FSM (finite state machine) is coord-dsl's smallest coordination unit. This
tutorial models one, generates it, and runs it — with a full **Python** section
and a full **C++** section. They share the same model and the same event-loop
semantics; only the runtime language differs.

Modelling
---------

Following the FSM design in Prof. Herman Bruyninckx's `Composable and
Explainable Systems of Systems`_, an FSM is represented as a pure data
structure. A ``.fsm`` file contains:

* **states** — the stateful behaviours, including a ``start`` and an ``end`` state;
* **an event loop** — named events representing occurrences or monitored state
  changes to which the machine reacts;
* **transitions** — directed ``from``/``to`` relationships between states; and
* **reactions** — the policy relating an event to a transition and, optionally,
  further events to fire.

Each reaction matches one event from the referenced event loop. Event
compositions from the broader FSM design are not implemented.

The control loop and behaviour implementations are separate from the model.

**Event-loop syntax.**

Declare an event loop before the FSM. It has its own namespace and name; each
comma-separated event is introduced by ``evt``:

.. code-block:: text

   evt loop (ns=ex) el {
       evt START,
       evt STOP
   }

The FSM selects one declared loop with ``evt loop: <el>``. Event references use
the loop-qualified name in both ``when`` and ``fires``:

.. code-block:: text

   R_START {
       when: <el.START>,
       do: <T_START>,
       fires { <el.STOP> }
   }

Within the same scope, e.g. in the same FSM declaration, references can be
direct, e.g., ``start: <IDLE>`` or ``from: <IDLE>, to: <GRASPING>``.

.. literalinclude:: ../../examples/models/fsm/example.fsm
   :language: text
   :caption: examples/models/fsm/example.fsm

Two rules matter:

* **Reactions are ordered.** On each step the *first* reaction whose event is
  present **and** whose transition starts from the current state is taken; the
  rest are ignored that step.
* During graph generation, the ``namespace`` (``ns``) is combined with the FSM
  and declaration names to create their full URIs.

The event-loop model (shared by Python and C++)
-----------------------------------------------

Events live in a **double buffer** — a *current* and a *future* set. One tick is
four operations:

.. list-table::
   :header-rows: 1
   :widths: 32 68

   * - Operation
     - Effect
   * - ``produce_event(ev, E)``
     - set ``E`` in the **future** buffer (schedule it)
   * - ``reconfig_event_buffers(ev)``
     - swap future→current and clear future (advance one tick)
   * - ``consume_event(ev, E)``
     - read ``E`` from the **current** buffer
   * - ``fsm_step``
     - apply the first matching reaction: transition + fire events (to future)

So an event you produce this tick becomes *current* — and drives a transition —
only after the next ``reconfig``. This one-tick pipeline is identical in both
languages. Generated code constructs the model data; the runtime supplies
the step operation — ``coord_dsl.fsm.fsm_step`` in Python and ``fsm_step_nbx``
from coord2b_ in C++ — while user code supplies the behaviour and control loop.

.. note::

   States should span at least two control-loop steps. A function call that
   completes within one step should not normally be modelled as a separate
   state: an event produced during that step is unavailable until the event
   buffers are reconfigured. Calling ``reconfig_event_buffers`` again before
   stepping the FSM can work around this for an immediate-completion state, as
   demonstrated in `coord-dsl@5d983e2`_, but does not remove the underlying
   double-buffer limitation.

Generate
--------

.. code-block:: bash

   textx generate example.fsm --target python -o ex_fsm.py
   textx generate example.fsm --target cpp    -o ex_fsm.hpp
   textx generate example.fsm --target graph --format json-ld --autocompact  # writes ex_fsm.ld.json beside example.fsm
   textx generate example.fsm --target dot --format png     # a picture of the machine

The ``graph`` and ``console`` targets call ``rdflib.Graph.serialize`` with
``format`` from ``--format`` (default: ``json-ld``), ``indent=2``, and
``auto_compact=True`` when ``--autocompact`` is present (``False`` otherwise).
RDFLib derives the compacted JSON-LD context from the graph's namespace
manager.

The code targets emit ``create_fsm()``, ``destroy_fsm()`` (C++), the
state/event/transition/reaction enums, and the IRI tables below. No control loop —
you own that. Each also writes a ``provenance.ld.json`` beside the artifact,
recording what produced it.

A tool that calls the generator functions itself records a file the same way,
with ``record(model, target, path, started)``.

.. _fsm-iri-tables:

Model IRIs in the generated code
''''''''''''''''''''''''''''''''

Every entity the model names keeps its IRI in the generated runtime, so a running
machine can identify itself and its parts against the RDF graph — the same IRIs
the ``graph`` target serialises:

.. list-table::
   :header-rows: 1
   :widths: 30 70

   * - Symbol
     - Names
   * - ``FSM_URI``
     - the machine itself
   * - ``STATE_URIS`` / ``EVENT_URIS``
     - indexed by ``StateID`` / ``EventID``
   * - ``TRANSITION_URIS`` / ``REACTION_URIS``
     - indexed by ``TransitionID`` / ``ReactionID``

.. code-block:: python

   from ex_fsm import FSM_URI, STATE_URIS, StateID, create_fsm

   fsm = create_fsm()
   print(FSM_URI)                                   # which machine
   print(STATE_URIS[StateID(fsm.current_state_index)])   # which state it is in

The C++ header carries the same names, as ``static constexpr const char *``
arrays indexed by the enums.

Running in Python
-----------------

The Python runtime is ``coord_dsl.event_loop`` (the buffer ops) and
``coord_dsl.fsm`` (``fsm_step``). The generated module gives you ``EventID`` and
``StateID`` enums, ``create_fsm()`` and ``STATE_URIS``.

The loop is: run **your** behaviour (produce/consume events), ``fsm_step``, then
``reconfig_event_buffers``:

.. code-block:: python

   from coord_dsl.event_loop import produce_event, consume_event, reconfig_event_buffers
   from coord_dsl.fsm import fsm_step
   from ex_fsm import EventID, StateID, create_fsm, STATE_URIS

   fsm = create_fsm()
   while fsm.current_state_index != StateID.S_EXIT:
       behavior(fsm)                          # YOUR code: produce/consume events
       fsm_step(fsm)                          # apply the first matching reaction
       reconfig_event_buffers(fsm.event_data)

``fsm.current_state_index`` is the live state; ``fsm.event_data`` holds the
buffers. You "define behaviour" by writing ``behavior`` — typically it inspects
``current_state_index`` and, when a state's work is done, produces the event
that advances the machine. A complete, time-driven controller ships with the
repo:

.. literalinclude:: ../../examples/models/fsm/generated_fsm_bhv.py
   :language: python
   :caption: examples/models/fsm/generated_fsm_bhv.py
   :lines: 1, 28-80

Run it:

.. code-block:: bash

   textx generate example.fsm --target python -o ex_fsm.py
   python generated_fsm_bhv.py             # cycles until Ctrl+C
   python generated_fsm_bhv.py --cycles 3  # fires e-exit, ends in S_EXIT

The second form is what makes the loop above terminate: the controller produces
``e-exit`` after three idle visits, and ``R_E_EXIT`` — which is ordered **above**
the ``e-step`` reactions, so it wins while both events are present — takes the
machine to its end state.

Running in C++
--------------

The C++ header is self-contained and depends on coord2b_. The API mirrors
Python one-to-one (``produce_event`` / ``consume_event`` /
``reconfig_event_buffers`` / ``fsm_step_nbx``), and the loop has the same shape:

.. literalinclude:: ../../examples/models/fsm/test_fsm.cpp
   :language: cpp
   :caption: examples/models/fsm/test_fsm.cpp — the control loop
   :lines: 27-63

``fsm->currentStateIndex`` and ``fsm->states[i].name`` read the live machine;
``fsm->eventData`` holds the buffers. Build against coord2b_ with CMake:

.. literalinclude:: ../../examples/models/fsm/CMakeLists.txt
   :language: cmake
   :caption: examples/models/fsm/CMakeLists.txt

.. code-block:: bash

   cmake -S . -B build && cmake --build build
   ./build/fsm_test

.. _coord2b: https://github.com/rosym-project/coord2b
.. _Composable and Explainable Systems of Systems: https://robmosys.pages.gitlab.kuleuven.be/composable-and-explainable-systems-of-systems.pdf
.. _coord-dsl@5d983e2: https://github.com/secorolab/coord-dsl/commit/5d983e2011957c373ca829f538c3baaa79266308
