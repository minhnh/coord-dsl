# coord-dsl

Domain-Specific Languages (DSLs) for modelling coordination of (robot) behaviours.

## Installation

The library can be installed as a Python package, e.g., with `pip`:

```bash
pip install "./coord_dsl"
```

## Coordination Models

### Finite State Machines (FSMs)

We include a [textX](https://textx.github.io/textX/) DSL for representing _event-driven_ finite state machines (FSMs).
This design is described in Prof. Herman Bruyninckx's [online book](https://robmosys.pages.gitlab.kuleuven.be/composable-and-explainable-systems-of-systems.pdf).
Specifically, the design allows specifying FSMs as a data type consisting of:

* _Events_, occurence or monitored state change of the system
* _States_, which represent stateful behaviours of a system
* _Transitions_ from one _State_ to another
* _Event Reactions_, which induce _Transitions_ when trigged by an _Event_
  (or event compositions, but not realized here).

Our implementations of this FSM design are meant to work with control loops, where in each loop the FSM step function
is called to induce state transitions.
Production and consumption of events are handled with a simple event loop implementation.

#### Example model

textX FSM models should be defined as a `.fsm` file. A simple example is listed below. More complete examples can be
found in the [`models/fsm`](examples/models/fsm/) directory.

```yaml
NAME: example_fsm

DESCRIPTION: Example FSM

STATES: S_START,S_STATE1,S_STATE2,S_EXIT

START_STATE: S_START
CURRENT_STATE: S_START
END_STATE: S_EXIT

EVENTS: E_EVENT1,E_EVENT2,E_STEP,E_EVENT3,E_EVENT4

TRANSITIONS:
    T_START_STATE1:
        FROM: @S_START
        TO: @S_STATE1
    T_STATE1_STATE2:
        FROM: @S_STATE1
        TO: @S_STATE2
    T_STATE2_STATE2:
        FROM: @S_STATE2
        TO: @S_STATE2
    T_STATE2_EXIT:
        FROM: @S_STATE2
        TO: @S_EXIT

REACTIONS:
    R_EVENT1:
        WHEN: @E_EVENT1
        DO: @T_START_STATE1
        FIRES: @E_EVENT2
    R_EVENT2:
        WHEN: @E_EVENT2
        DO: @T_STATE1_STATE2
    R_STEP:
        WHEN: @E_STEP
        DO: @T_STATE2_STATE2
        FIRES: @E_EVENT3,@E_EVENT4
    R_EVENT3:
        WHEN: @E_EVENT3
        DO: @T_STATE2_EXIT
```

##### States

* States represent the different behaviors of an activity.
* Each state is represented by a unique identifier.
* The `START_STATE` and `END_STATE` variables define the initial and final states of the FSM.
* The `CURRENT_STATE` variable defines where the FSM starts from.

    > [!IMPORTANT]
    > The included event loop implementation can only work with states that spans at least 2 "steps."
    > Function calls that does not span 2 steps should not be in a separate state.
    > For more details see commit [coord-dsl@5d983e2](https://github.com/secorolab/coord-dsl/commit/5d983e2011957c373ca829f538c3baaa79266308).

##### Events

[Events](https://en.wikipedia.org/wiki/Event_(computing)) represents "a detectable occurence" or a
"monitored change in state." Here, events trigger "reactions" in the form of state transitions.

##### Transitions

* Transitions section defines the `transition` `from` one state `to` another.
* Each `transition` is represented by a unique identifier.
* The `FROM` and `TO` keywords define the source and destination states (`@` is used to reference the state by its identifier).
* A state can have multiple transitions leading to different states or the same state.

##### Reactions

* Reactions represents the decision making policy of the FSM for changing its behavior.
* It defines a list of events that the FSM can _react_ to with `WHEN` keyword, each `event` associated with a unique reaction.
* The `DO` keyword defines the action to be taken when the `event` occurs.
* The `FIRES` keyword defines the `set` of events (or none) that are fired as a result of the transition.

    > [!IMPORTANT]
    > The order of the `REACTIONS` section is important. The first reaction that matches the `event` and that satisfies
    > the `transition` will be executed. If multiple reactions match, only the first one will be executed.

#### Code Generation

```bash
textx generate model.fsm --target cpp -o model.hpp
textx generate model.fsm --target py -o model.py
```

* Generates a C++ header file with the data structures required for the FSM, along with a sample implementation code.
* The header file can be included in a C++ program.
* If the `-o` is not specified, the generated file will be saved in the same directory as the input file with
  the same name and `.hpp` extension.
* Available targets:
  - `cpp`: A C++ header file.
  - `py`: A Python module.
  - `json`: JSON file.
  - `console`: Console output.

#### Execution

* The generated header file is dependent on the [coord2b](https://github.com/rosym-project/coord2b) library.
* The [traffic_lights.c](https://github.com/rosym-project/coord2b/blob/master/src/example/traffic_lights.c) example
  is a good starting point to understand how to use the generated data structures.
