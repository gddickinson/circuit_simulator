# Circuit Simulator

An interactive electronic circuit simulator built with Python and PyQt5. This application allows you to create, simulate, and analyze electronic circuits in real-time.

## Features

- Interactive circuit board for placing and connecting components
- Real-time simulation with visual feedback
- Automatic schematic diagram generation
- Measurement and analysis tools
- Built-in component library
- Save and load circuit designs
- SQL database for component storage

## Components

The simulator includes the following components:

- **Passive Components**: Resistors, Capacitors, Inductors, Ground
- **Active Components**: Diodes, LEDs, BJTs, Switches
- **Sources**: DC Voltage, AC Voltage, DC Current
- **Meters**: Voltmeter, Ammeter (coming soon)

## Requirements

- Python 3.7+
- PyQt5
- NumPy
- SciPy
- Matplotlib

## Installation

1. Clone this repository
2. Install the required dependencies:

```bash
pip install -r requirements.txt
```

## Usage

To start the application, run:

```bash
python main.py
```

Command-line options:
- `--debug`: Enable debug mode
- `--load <file>`: Load a saved circuit file
- `--example <name>`: Load an example circuit
- `--config <file>`: Path to configuration file

## Getting Started

1. Start the application
2. Select components from the component panel
3. Place components on the circuit board
4. Connect components by clicking and dragging between connection points
5. Start the simulation using the Simulation menu
6. View measurements and analysis in the Analysis panel

## Development

The project is structured in a modular way for easy extension:

- `main.py`: Main entry point
- `gui/`: User interface components
- `components/`: Circuit component definitions
- `simulation/`: Simulation engine
- `database/`: Database management
- `utils/`: Utility functions

## License

This project is open-source and available under the MIT License.

## Contributing

Contributions are welcome! Please feel free to submit a Pull Request.
