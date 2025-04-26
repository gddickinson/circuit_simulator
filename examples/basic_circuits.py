"""
Circuit Simulator - Basic Example Circuits
----------------------------------------
This module provides functions to create basic example circuits.
"""

import logging
from components.passive_components import Resistor, Capacitor, Inductor, Ground
from components.active_components import (
    DCVoltageSource, ACVoltageSource, DCCurrentSource, Diode, LED, BJT, Switch
)

logger = logging.getLogger(__name__)


def create_voltage_divider(simulator):
    """Create a simple voltage divider circuit.
    
    Args:
        simulator: CircuitSimulator instance
        
    Returns:
        True if successful, False otherwise
    """
    logger.info("Creating voltage divider circuit")
    
    # Clear the simulator
    simulator.clear()
    
    # Create components
    dc_source = DCVoltageSource(properties={'voltage': 10.0})
    dc_source.position = (5, 5)
    
    r1 = Resistor(properties={'resistance': 1000.0})  # 1k ohm
    r1.position = (8, 5)
    r1.rotation = 0
    
    r2 = Resistor(properties={'resistance': 1000.0})  # 1k ohm
    r2.position = (11, 5)
    r2.rotation = 0
    
    ground = Ground()
    ground.position = (14, 7)
    
    # Add components to simulator
    simulator.add_component(dc_source)
    simulator.add_component(r1)
    simulator.add_component(r2)
    simulator.add_component(ground)
    
    # Build the circuit
    simulator.build_circuit_from_components()
    
    # Connect components
    simulator.connect_components_at(dc_source.id, 'pos', r1.id, 'p1')
    simulator.connect_components_at(r1.id, 'p2', r2.id, 'p1')
    simulator.connect_components_at(r2.id, 'p2', ground.id, 'gnd')
    simulator.connect_components_at(dc_source.id, 'neg', ground.id, 'gnd')
    
    return True


def create_rc_circuit(simulator):
    """Create an RC circuit (resistor-capacitor).
    
    Args:
        simulator: CircuitSimulator instance
        
    Returns:
        True if successful, False otherwise
    """
    logger.info("Creating RC circuit")
    
    # Clear the simulator
    simulator.clear()
    
    # Create components
    dc_source = DCVoltageSource(properties={'voltage': 5.0})
    dc_source.position = (5, 5)
    
    resistor = Resistor(properties={'resistance': 1000.0})  # 1k ohm
    resistor.position = (8, 5)
    resistor.rotation = 0
    
    capacitor = Capacitor(properties={'capacitance': 1e-6})  # 1 µF
    capacitor.position = (11, 5)
    capacitor.rotation = 0
    
    ground = Ground()
    ground.position = (14, 7)
    
    # Add components to simulator
    simulator.add_component(dc_source)
    simulator.add_component(resistor)
    simulator.add_component(capacitor)
    simulator.add_component(ground)
    
    # Build the circuit
    simulator.build_circuit_from_components()
    
    # Connect components
    simulator.connect_components_at(dc_source.id, 'pos', resistor.id, 'p1')
    simulator.connect_components_at(resistor.id, 'p2', capacitor.id, 'p1')
    simulator.connect_components_at(capacitor.id, 'p2', ground.id, 'gnd')
    simulator.connect_components_at(dc_source.id, 'neg', ground.id, 'gnd')
    
    return True


def create_diode_circuit(simulator):
    """Create a simple diode circuit.
    
    Args:
        simulator: CircuitSimulator instance
        
    Returns:
        True if successful, False otherwise
    """
    logger.info("Creating diode circuit")
    
    # Clear the simulator
    simulator.clear()
    
    # Create components
    dc_source = DCVoltageSource(properties={'voltage': 5.0})
    dc_source.position = (5, 5)
    
    resistor = Resistor(properties={'resistance': 1000.0})  # 1k ohm
    resistor.position = (8, 5)
    resistor.rotation = 0
    
    diode = Diode(properties={'forward_voltage': 0.7})
    diode.position = (11, 5)
    diode.rotation = 0
    
    ground = Ground()
    ground.position = (14, 7)
    
    # Add components to simulator
    simulator.add_component(dc_source)
    simulator.add_component(resistor)
    simulator.add_component(diode)
    simulator.add_component(ground)
    
    # Build the circuit
    simulator.build_circuit_from_components()
    
    # Connect components
    simulator.connect_components_at(dc_source.id, 'pos', resistor.id, 'p1')
    simulator.connect_components_at(resistor.id, 'p2', diode.id, 'anode')
    simulator.connect_components_at(diode.id, 'cathode', ground.id, 'gnd')
    simulator.connect_components_at(dc_source.id, 'neg', ground.id, 'gnd')
    
    return True


def create_led_circuit(simulator):
    """Create a simple LED circuit.
    
    Args:
        simulator: CircuitSimulator instance
        
    Returns:
        True if successful, False otherwise
    """
    logger.info("Creating LED circuit")
    
    # Clear the simulator
    simulator.clear()
    
    # Create components
    dc_source = DCVoltageSource(properties={'voltage': 5.0})
    dc_source.position = (5, 5)
    
    resistor = Resistor(properties={'resistance': 220.0})  # 220 ohm
    resistor.position = (8, 5)
    resistor.rotation = 0
    
    led = LED(properties={'forward_voltage': 2.0, 'color': 'red'})
    led.position = (11, 5)
    led.rotation = 0
    
    ground = Ground()
    ground.position = (14, 7)
    
    # Add components to simulator
    simulator.add_component(dc_source)
    simulator.add_component(resistor)
    simulator.add_component(led)
    simulator.add_component(ground)
    
    # Build the circuit
    simulator.build_circuit_from_components()
    
    # Connect components
    simulator.connect_components_at(dc_source.id, 'pos', resistor.id, 'p1')
    simulator.connect_components_at(resistor.id, 'p2', led.id, 'anode')
    simulator.connect_components_at(led.id, 'cathode', ground.id, 'gnd')
    simulator.connect_components_at(dc_source.id, 'neg', ground.id, 'gnd')
    
    return True


def create_bjt_circuit(simulator):
    """Create a simple BJT transistor circuit.
    
    Args:
        simulator: CircuitSimulator instance
        
    Returns:
        True if successful, False otherwise
    """
    logger.info("Creating BJT circuit")
    
    # Clear the simulator
    simulator.clear()
    
    # Create components
    dc_source = DCVoltageSource(properties={'voltage': 9.0})
    dc_source.position = (5, 5)
    
    rc = Resistor(properties={'resistance': 1000.0})  # 1k ohm - collector resistor
    rc.position = (8, 5)
    rc.rotation = 0
    
    rb = Resistor(properties={'resistance': 10000.0})  # 10k ohm - base resistor
    rb.position = (8, 8)
    rb.rotation = 0
    
    bjt = BJT(properties={'type': 'npn', 'gain': 100})
    bjt.position = (11, 8)
    
    ground = Ground()
    ground.position = (11, 11)
    
    # Add components to simulator
    simulator.add_component(dc_source)
    simulator.add_component(rc)
    simulator.add_component(rb)
    simulator.add_component(bjt)
    simulator.add_component(ground)
    
    # Build the circuit
    simulator.build_circuit_from_components()
    
    # Connect components
    simulator.connect_components_at(dc_source.id, 'pos', rc.id, 'p1')
    simulator.connect_components_at(rc.id, 'p2', bjt.id, 'collector')
    simulator.connect_components_at(dc_source.id, 'pos', rb.id, 'p1')
    simulator.connect_components_at(rb.id, 'p2', bjt.id, 'base')
    simulator.connect_components_at(bjt.id, 'emitter', ground.id, 'gnd')
    simulator.connect_components_at(dc_source.id, 'neg', ground.id, 'gnd')
    
    return True


def create_oscillator_circuit(simulator):
    """Create a simple oscillator circuit.
    
    Args:
        simulator: CircuitSimulator instance
        
    Returns:
        True if successful, False otherwise
    """
    logger.info("Creating oscillator circuit")
    
    # Clear the simulator
    simulator.clear()
    
    # Create components
    ac_source = ACVoltageSource(properties={
        'amplitude': 5.0, 
        'frequency': 1000.0,
        'phase': 0.0
    })
    ac_source.position = (5, 5)
    
    resistor = Resistor(properties={'resistance': 1000.0})  # 1k ohm
    resistor.position = (8, 5)
    resistor.rotation = 0
    
    capacitor = Capacitor(properties={'capacitance': 1e-6})  # 1 µF
    capacitor.position = (11, 5)
    capacitor.rotation = 0
    
    ground = Ground()
    ground.position = (14, 7)
    
    # Add components to simulator
    simulator.add_component(ac_source)
    simulator.add_component(resistor)
    simulator.add_component(capacitor)
    simulator.add_component(ground)
    
    # Build the circuit
    simulator.build_circuit_from_components()
    
    # Connect components
    simulator.connect_components_at(ac_source.id, 'pos', resistor.id, 'p1')
    simulator.connect_components_at(resistor.id, 'p2', capacitor.id, 'p1')
    simulator.connect_components_at(capacitor.id, 'p2', ground.id, 'gnd')
    simulator.connect_components_at(ac_source.id, 'neg', ground.id, 'gnd')
    
    return True


def create_switch_circuit(simulator):
    """Create a simple switch circuit.
    
    Args:
        simulator: CircuitSimulator instance
        
    Returns:
        True if successful, False otherwise
    """
    logger.info("Creating switch circuit")
    
    # Clear the simulator
    simulator.clear()
    
    # Create components
    dc_source = DCVoltageSource(properties={'voltage': 5.0})
    dc_source.position = (5, 5)
    
    switch = Switch(properties={'state': False})  # Initially open
    switch.position = (8, 5)
    switch.rotation = 0
    
    resistor = Resistor(properties={'resistance': 1000.0})  # 1k ohm
    resistor.position = (11, 5)
    resistor.rotation = 0
    
    led = LED(properties={'forward_voltage': 2.0, 'color': 'green'})
    led.position = (14, 5)
    led.rotation = 0
    
    ground = Ground()
    ground.position = (17, 7)
    
    # Add components to simulator
    simulator.add_component(dc_source)
    simulator.add_component(switch)
    simulator.add_component(resistor)
    simulator.add_component(led)
    simulator.add_component(ground)
    
    # Build the circuit
    simulator.build_circuit_from_components()
    
    # Connect components
    simulator.connect_components_at(dc_source.id, 'pos', switch.id, 'p1')
    simulator.connect_components_at(switch.id, 'p2', resistor.id, 'p1')
    simulator.connect_components_at(resistor.id, 'p2', led.id, 'anode')
    simulator.connect_components_at(led.id, 'cathode', ground.id, 'gnd')
    simulator.connect_components_at(dc_source.id, 'neg', ground.id, 'gnd')
    
    return True


def create_example_circuit(simulator, circuit_name):
    """Create an example circuit by name.
    
    Args:
        simulator: CircuitSimulator instance
        circuit_name: Name of the example circuit
        
    Returns:
        True if successful, False otherwise
    """
    # Map of circuit names to creation functions
    circuits = {
        'voltage_divider': create_voltage_divider,
        'rc_circuit': create_rc_circuit,
        'diode_circuit': create_diode_circuit,
        'led_circuit': create_led_circuit,
        'bjt_circuit': create_bjt_circuit,
        'oscillator_circuit': create_oscillator_circuit,
        'switch_circuit': create_switch_circuit
    }
    
    # Normalize the circuit name
    circuit_name = circuit_name.lower().replace(' ', '_')
    
    # Check if the circuit exists
    if circuit_name in circuits:
        # Create the circuit
        return circuits[circuit_name](simulator)
    else:
        logger.error(f"Unknown example circuit: {circuit_name}")
        return False
