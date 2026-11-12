"""Component catalog and example circuits for the web interface, taken from the desktop app's own code.

* catalog(): every component class the desktop app can place (gui/circuit_board.py _create_component), with its
  connection offsets and size (components/*.py), default properties (simulation/mna.py DEFAULTS, the same defaults
  the component classes use) and the editable properties with units as in gui/component_panel.py.
* examples(): the seven circuits of examples/basic_circuits.py, built by that module and saved with
  CircuitSimulator.to_dict() (the .circuit file format). Only the board positions/rotations are re-laid out
  (LAYOUT below) so the schematic reads clearly; components, values and connections are untouched.
"""
import logging

from components.active_components import (ACVoltageSource, BJT, DCCurrentSource, DCVoltageSource, Diode, LED,
                                          Switch)
from components.passive_components import Capacitor, Ground, Inductor, Resistor
from examples import basic_circuits
from simulation.mna import DEFAULTS
from simulation.simulator import CircuitSimulator

logging.getLogger("simulation").setLevel(logging.WARNING)
logging.getLogger("components").setLevel(logging.WARNING)

CLASSES = [Resistor, Capacitor, Inductor, Ground, DCVoltageSource, ACVoltageSource, DCCurrentSource, Diode, LED, BJT,
           Switch]
GROUPS = {"Passive": ["Resistor", "Capacitor", "Inductor", "Ground"],
          "Sources": ["DCVoltageSource", "ACVoltageSource", "DCCurrentSource"],
          "Active": ["Diode", "LED", "BJT", "Switch"]}
LABELS = {"Resistor": "Resistor", "Capacitor": "Capacitor", "Inductor": "Inductor", "Ground": "Ground",
          "DCVoltageSource": "DC voltage source", "ACVoltageSource": "AC voltage source",
          "DCCurrentSource": "DC current source", "Diode": "Diode", "LED": "LED", "BJT": "BJT transistor",
          "Switch": "Switch"}
# Editable properties and units, as in the property dialog of gui/component_panel.py (name, label, unit or choices).
PROPS = {
    "Resistor": [("resistance", "Resistance", "Ω"), ("max_power", "Max power", "W")],
    "Capacitor": [("capacitance", "Capacitance", "F"), ("max_voltage", "Max voltage", "V")],
    "Inductor": [("inductance", "Inductance", "H"), ("max_current", "Max current", "A")],
    "Ground": [],
    "DCVoltageSource": [("voltage", "Voltage", "V"), ("max_current", "Max current", "A")],
    "ACVoltageSource": [("amplitude", "Amplitude", "V"), ("frequency", "Frequency", "Hz"), ("phase", "Phase", "°")],
    "DCCurrentSource": [("current", "Current", "A"), ("max_voltage", "Max voltage", "V")],
    "Diode": [("forward_voltage", "Forward voltage", "V"), ("max_current", "Max current", "A")],
    "LED": [("forward_voltage", "Forward voltage", "V"), ("max_current", "Max current", "A"),
            ("color", "Colour", ["red", "green", "blue", "yellow", "white"])],
    "BJT": [("type", "Type", ["npn", "pnp"]), ("gain", "Gain (β)", ""),
            ("max_collector_current", "Max collector current", "A")],
    "Switch": [("state", "Closed", "bool"), ("max_current", "Max current", "A")],
}
# Desktop defaults of the rating-only properties (gui/component_panel.py); they do not enter the solver.
RATINGS = {"Resistor": {"max_power": 0.25}, "Capacitor": {"max_voltage": 50.0}, "Inductor": {"max_current": 1.0},
           "DCVoltageSource": {"max_current": 1.0}, "DCCurrentSource": {"max_voltage": 12.0},
           "Switch": {"max_current": 5.0}}


def catalog():
    out = []
    for cls in CLASSES:
        comp = cls()
        name = cls.__name__
        out.append({"type": name, "label": LABELS[name],
                    "group": next(g for g, names in GROUPS.items() if name in names),
                    "connections": {k: list(v) for k, v in comp.connections.items()}, "size": list(comp.size),
                    "defaults": {**DEFAULTS[name], **RATINGS.get(name, {})},
                    "props": [{"name": n, "label": lab, "unit": u if isinstance(u, str) else "",
                               "choices": u if isinstance(u, list) else None} for n, lab, u in PROPS[name]]})
    return out


TITLES = {"voltage_divider": "Voltage divider", "rc_circuit": "RC charging", "diode_circuit": "Diode",
          "led_circuit": "LED", "bjt_circuit": "BJT switch", "oscillator_circuit": "AC into RC low-pass",
          "switch_circuit": "Switch + LED"}
NOTES = {"voltage_divider": "10 V across 1 kΩ + 1 kΩ: the midpoint sits at 5 V and 5 mA flows.",
         "rc_circuit": "5 V charging 1 µF through 1 kΩ: τ = RC = 1 ms, 63 % after one time constant.",
         "diode_circuit": "5 V, 1 kΩ and a silicon diode (Vf 0.7 V): about 4.3 mA.",
         "led_circuit": "5 V, 220 Ω and a red LED (Vf 2 V): about 13.6 mA.",
         "bjt_circuit": "npn transistor (β 100) with 10 kΩ base and 1 kΩ collector resistors on 9 V: driven into "
                        "saturation.",
         "oscillator_circuit": "5 V, 1 kHz sine into 1 kΩ / 1 µF: the capacitor lags and is attenuated.",
         "switch_circuit": "5 V, switch, 1 kΩ and a green LED. Double-click the switch to close it."}
ID_PREFIX = {"Resistor": "resistor_", "Capacitor": "capacitor_", "Inductor": "inductor_", "Ground": "ground_",
             "DCVoltageSource": "dc_source_", "ACVoltageSource": "ac_source_", "DCCurrentSource": "dc_current_",
             "Diode": "diode_", "LED": "led_", "BJT": "bjt_", "Switch": "switch_"}
# Board layout (x, y, rotation) per component, in the order basic_circuits.py adds them.
LAYOUT = {
    "voltage_divider": [(6, 12, 180), (13, 8, 0), (19, 11, 90), (13, 17, 0)],
    "rc_circuit": [(6, 12, 180), (13, 8, 0), (19, 11, 90), (13, 17, 0)],
    "diode_circuit": [(6, 12, 180), (13, 8, 0), (19, 11, 90), (13, 17, 0)],
    "led_circuit": [(6, 12, 180), (13, 8, 0), (19, 11, 90), (13, 17, 0)],
    "bjt_circuit": [(6, 12, 180), (20, 6, 90), (28, 6, 90), (20, 12, 180), (13, 18, 0)],
    "oscillator_circuit": [(6, 12, 180), (13, 8, 0), (19, 11, 90), (13, 17, 0)],
    "switch_circuit": [(6, 12, 180), (11, 8, 0), (17, 8, 0), (23, 11, 90), (14, 17, 0)],
}


def example(name):
    sim = CircuitSimulator()
    if not basic_circuits.create_example_circuit(sim, name):
        raise KeyError(name)
    data = sim.to_dict()
    # readable, stable ids in the id-prefix style utils/file_manager.py recognises (uuid4 ids change every run)
    ids, count = {}, {}
    for old in data["components"]:
        prefix = ID_PREFIX[data["components"][old]["type"]]
        count[prefix] = count.get(prefix, 0) + 1
        ids[old] = f"{prefix}{count[prefix]}"
    comps = {}
    for (old, comp), (x, y, rot) in zip(data["components"].items(), LAYOUT[name]):
        comp.update(id=ids[old], position=[x, y], rotation=rot, size=list(comp["size"]))
        comp.pop("state", None)  # the desktop loader then starts from each component's _init_state()
        comp["connected_to"] = {k: [[ids[o], t] for o, t in v] for k, v in comp["connected_to"].items()}
        comps[ids[old]] = comp
    data["components"] = comps
    data["ground_node"] = None
    data["metadata"] = {"version": "1.0", "description": NOTES[name], "name": TITLES[name]}
    return data


def examples():
    return [{"name": n, "title": TITLES[n], "note": NOTES[n],
             "components": len(example(n)["components"])} for n in TITLES]
