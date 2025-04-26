"""
Circuit Simulator - Database Manager
----------------------------------
This module handles database connections and operations.
"""

import os
import sqlite3
import logging
from pathlib import Path
import json

import config
from database.models import Component, SavedCircuit

logger = logging.getLogger(__name__)


class DatabaseManager:
    """Manages database connections and operations for the circuit simulator."""
    
    def __init__(self, db_path=None):
        """Initialize the database manager.
        
        Args:
            db_path: Path to the SQLite database file. If None, uses the path from config.
        """
        self.db_path = db_path or config.DATABASE_PATH
        self.conn = None
        self._component_cache = {}
        self._circuit_cache = {}
    
    def get_connection(self):
        """Get a database connection."""
        if self.conn is None:
            try:
                self.conn = sqlite3.connect(
                    self.db_path, 
                    timeout=config.DB_TIMEOUT,
                    detect_types=sqlite3.PARSE_DECLTYPES
                )
                self.conn.row_factory = sqlite3.Row
                logger.debug(f"Connected to database at {self.db_path}")
            except sqlite3.Error as e:
                logger.error(f"Error connecting to database: {e}")
                raise
        return self.conn
    
    def close_connection(self):
        """Close the database connection."""
        if self.conn:
            self.conn.close()
            self.conn = None
            logger.debug("Database connection closed")
    
    def execute_query(self, query, params=None, commit=False):
        """Execute a SQL query.
        
        Args:
            query: SQL query string
            params: Query parameters
            commit: Whether to commit the transaction
            
        Returns:
            Cursor object
        """
        conn = self.get_connection()
        try:
            cursor = conn.cursor()
            if params:
                cursor.execute(query, params)
            else:
                cursor.execute(query)
            
            if commit:
                conn.commit()
            
            return cursor
        except sqlite3.Error as e:
            logger.error(f"Error executing query: {e}")
            logger.debug(f"Query: {query}, Params: {params}")
            conn.rollback()
            raise
    
    def initialize_database(self):
        """Initialize the database with required tables."""
        logger.info("Initializing database")
        
        # Read schema file
        schema_path = Path(__file__).parent / "schema.sql"
        try:
            with open(schema_path, 'r') as f:
                schema_sql = f.read()
        except FileNotFoundError:
            logger.error(f"Schema file not found: {schema_path}")
            self._create_default_schema()
            return
        
        # Execute schema
        conn = self.get_connection()
        try:
            conn.executescript(schema_sql)
            conn.commit()
            logger.info("Database schema initialized")
            
            # Check if we need to populate with default components
            cursor = self.execute_query("SELECT COUNT(*) FROM components")
            if cursor.fetchone()[0] == 0:
                self._populate_default_components()
                
        except sqlite3.Error as e:
            logger.error(f"Error initializing database: {e}")
            conn.rollback()
            raise
    
    def _create_default_schema(self):
        """Create a default schema if the schema file is missing."""
        logger.info("Creating default database schema")
        
        conn = self.get_connection()
        try:
            # Components table
            conn.execute('''
                CREATE TABLE IF NOT EXISTS components (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    type TEXT NOT NULL,
                    name TEXT NOT NULL,
                    description TEXT,
                    properties TEXT NOT NULL,
                    image_path TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Saved circuits table
            conn.execute('''
                CREATE TABLE IF NOT EXISTS saved_circuits (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    name TEXT NOT NULL,
                    description TEXT,
                    circuit_data TEXT NOT NULL,
                    thumbnail TEXT,
                    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    modified_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
                )
            ''')
            
            # Usage statistics table
            conn.execute('''
                CREATE TABLE IF NOT EXISTS usage_stats (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    component_id INTEGER,
                    circuit_id INTEGER,
                    action TEXT NOT NULL,
                    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                    FOREIGN KEY (component_id) REFERENCES components (id),
                    FOREIGN KEY (circuit_id) REFERENCES saved_circuits (id)
                )
            ''')
            
            conn.commit()
            logger.info("Default database schema created")
            
            # Populate with default components
            self._populate_default_components()
            
        except sqlite3.Error as e:
            logger.error(f"Error creating default schema: {e}")
            conn.rollback()
            raise
    
    def _populate_default_components(self):
        """Populate the database with default components."""
        logger.info("Adding default components to database")
        
        # Define basic components
        default_components = [
            # Passive components
            Component("resistor", "Resistor", "Standard resistor", 
                     {"resistance": config.DEFAULT_RESISTANCE, "max_power": 0.25}),
            Component("capacitor", "Capacitor", "Standard capacitor", 
                     {"capacitance": config.DEFAULT_CAPACITANCE, "max_voltage": 50}),
            Component("inductor", "Inductor", "Standard inductor", 
                     {"inductance": config.DEFAULT_INDUCTANCE, "max_current": 1.0}),
            
            # Active components
            Component("diode", "Diode", "Standard diode", 
                     {"forward_voltage": 0.7, "max_current": 1.0}),
            Component("led", "LED", "Light Emitting Diode", 
                     {"forward_voltage": 2.0, "color": "red", "max_current": 0.02}),
            Component("npn_transistor", "NPN Transistor", "NPN BJT", 
                     {"gain": 100, "max_collector_current": 0.5}),
            Component("pnp_transistor", "PNP Transistor", "PNP BJT", 
                     {"gain": 100, "max_collector_current": 0.5}),
            
            # Sources
            Component("dc_voltage_source", "DC Voltage Source", "DC power supply", 
                     {"voltage": config.DEFAULT_VOLTAGE, "max_current": 1.0}),
            Component("dc_current_source", "DC Current Source", "DC current source", 
                     {"current": config.DEFAULT_CURRENT, "max_voltage": 12.0}),
            Component("ac_voltage_source", "AC Voltage Source", "AC power supply", 
                     {"amplitude": config.DEFAULT_VOLTAGE, 
                      "frequency": config.DEFAULT_FREQUENCY, 
                      "phase": 0.0}),
            
            # Meters
            Component("voltmeter", "Voltmeter", "Voltage measurement device", 
                     {"max_voltage": 50.0, "internal_resistance": 1e7}),
            Component("ammeter", "Ammeter", "Current measurement device", 
                     {"max_current": 10.0, "internal_resistance": 0.1}),
            
            # Switches and controls
            Component("switch", "Switch", "Simple on/off switch", 
                     {"state": False, "max_current": 5.0}),
            Component("potentiometer", "Potentiometer", "Variable resistor", 
                     {"max_resistance": 10000, "current_value": 5000, "max_power": 0.5}),
        ]
        
        # Insert components into database
        for component in default_components:
            self.add_component(component)
            
        logger.info(f"Added {len(default_components)} default components")
    
    def add_component(self, component):
        """Add a component to the database.
        
        Args:
            component: Component object to add
            
        Returns:
            Component ID
        """
        properties_json = json.dumps(component.properties)
        
        cursor = self.execute_query(
            """
            INSERT INTO components (type, name, description, properties, image_path)
            VALUES (?, ?, ?, ?, ?)
            """,
            (component.type, component.name, component.description, 
             properties_json, component.image_path),
            commit=True
        )
        
        component_id = cursor.lastrowid
        logger.debug(f"Added component: {component.name} (ID: {component_id})")
        
        # Update cache
        component.id = component_id
        self._component_cache[component_id] = component
        
        return component_id
    
    def get_component(self, component_id):
        """Get a component by ID.
        
        Args:
            component_id: Component ID
            
        Returns:
            Component object or None if not found
        """
        # Check cache first
        if component_id in self._component_cache:
            return self._component_cache[component_id]
        
        cursor = self.execute_query(
            "SELECT * FROM components WHERE id = ?",
            (component_id,)
        )
        row = cursor.fetchone()
        
        if row:
            properties = json.loads(row['properties'])
            component = Component(
                row['type'],
                row['name'],
                row['description'],
                properties,
                row['image_path']
            )
            component.id = row['id']
            
            # Update cache
            self._component_cache[component_id] = component
            
            return component
        
        return None
    
    def get_all_components(self, component_type=None):
        """Get all components.
        
        Args:
            component_type: Optional filter by component type
            
        Returns:
            List of Component objects
        """
        if component_type:
            cursor = self.execute_query(
                "SELECT * FROM components WHERE type = ?",
                (component_type,)
            )
        else:
            cursor = self.execute_query("SELECT * FROM components")
        
        components = []
        for row in cursor.fetchall():
            properties = json.loads(row['properties'])
            component = Component(
                row['type'],
                row['name'],
                row['description'],
                properties,
                row['image_path']
            )
            component.id = row['id']
            
            # Update cache
            self._component_cache[component.id] = component
            
            components.append(component)
        
        return components
    
    def update_component(self, component):
        """Update a component in the database.
        
        Args:
            component: Component object to update
            
        Returns:
            True if successful, False otherwise
        """
        properties_json = json.dumps(component.properties)
        
        try:
            self.execute_query(
                """
                UPDATE components
                SET type = ?, name = ?, description = ?, properties = ?, image_path = ?
                WHERE id = ?
                """,
                (component.type, component.name, component.description,
                 properties_json, component.image_path, component.id),
                commit=True
            )
            
            # Update cache
            self._component_cache[component.id] = component
            
            logger.debug(f"Updated component: {component.name} (ID: {component.id})")
            return True
        except sqlite3.Error as e:
            logger.error(f"Error updating component: {e}")
            return False
    
    def delete_component(self, component_id):
        """Delete a component from the database.
        
        Args:
            component_id: Component ID
            
        Returns:
            True if successful, False otherwise
        """
        try:
            self.execute_query(
                "DELETE FROM components WHERE id = ?",
                (component_id,),
                commit=True
            )
            
            # Remove from cache
            if component_id in self._component_cache:
                del self._component_cache[component_id]
            
            logger.debug(f"Deleted component ID: {component_id}")
            return True
        except sqlite3.Error as e:
            logger.error(f"Error deleting component: {e}")
            return False
    
    def save_circuit(self, circuit):
        """Save a circuit to the database.
        
        Args:
            circuit: SavedCircuit object
            
        Returns:
            Circuit ID
        """
        circuit_data_json = json.dumps(circuit.circuit_data)
        
        if circuit.id is None:
            # New circuit
            cursor = self.execute_query(
                """
                INSERT INTO saved_circuits (name, description, circuit_data, thumbnail)
                VALUES (?, ?, ?, ?)
                """,
                (circuit.name, circuit.description, circuit_data_json, circuit.thumbnail),
                commit=True
            )
            
            circuit_id = cursor.lastrowid
            circuit.id = circuit_id
        else:
            # Update existing circuit
            cursor = self.execute_query(
                """
                UPDATE saved_circuits
                SET name = ?, description = ?, circuit_data = ?, thumbnail = ?,
                    modified_at = CURRENT_TIMESTAMP
                WHERE id = ?
                """,
                (circuit.name, circuit.description, circuit_data_json, 
                 circuit.thumbnail, circuit.id),
                commit=True
            )
            
            circuit_id = circuit.id
        
        # Update cache
        self._circuit_cache[circuit_id] = circuit
        
        logger.debug(f"Saved circuit: {circuit.name} (ID: {circuit_id})")
        return circuit_id
    
    def get_circuit(self, circuit_id):
        """Get a circuit by ID.
        
        Args:
            circuit_id: Circuit ID
            
        Returns:
            SavedCircuit object or None if not found
        """
        # Check cache first
        if circuit_id in self._circuit_cache:
            return self._circuit_cache[circuit_id]
        
        cursor = self.execute_query(
            "SELECT * FROM saved_circuits WHERE id = ?",
            (circuit_id,)
        )
        row = cursor.fetchone()
        
        if row:
            circuit_data = json.loads(row['circuit_data'])
            circuit = SavedCircuit(
                row['name'],
                circuit_data,
                row['description'],
                row['thumbnail']
            )
            circuit.id = row['id']
            circuit.created_at = row['created_at']
            circuit.modified_at = row['modified_at']
            
            # Update cache
            self._circuit_cache[circuit_id] = circuit
            
            return circuit
        
        return None
    
    def get_all_circuits(self):
        """Get all saved circuits.
        
        Returns:
            List of SavedCircuit objects
        """
        cursor = self.execute_query("SELECT * FROM saved_circuits ORDER BY modified_at DESC")
        
        circuits = []
        for row in cursor.fetchall():
            circuit_data = json.loads(row['circuit_data'])
            circuit = SavedCircuit(
                row['name'],
                circuit_data,
                row['description'],
                row['thumbnail']
            )
            circuit.id = row['id']
            circuit.created_at = row['created_at']
            circuit.modified_at = row['modified_at']
            
            # Update cache
            self._circuit_cache[circuit.id] = circuit
            
            circuits.append(circuit)
        
        return circuits
    
    def delete_circuit(self, circuit_id):
        """Delete a circuit from the database.
        
        Args:
            circuit_id: Circuit ID
            
        Returns:
            True if successful, False otherwise
        """
        try:
            self.execute_query(
                "DELETE FROM saved_circuits WHERE id = ?",
                (circuit_id,),
                commit=True
            )
            
            # Remove from cache
            if circuit_id in self._circuit_cache:
                del self._circuit_cache[circuit_id]
            
            logger.debug(f"Deleted circuit ID: {circuit_id}")
            return True
        except sqlite3.Error as e:
            logger.error(f"Error deleting circuit: {e}")
            return False
    
    def log_usage(self, component_id=None, circuit_id=None, action=""):
        """Log component or circuit usage.
        
        Args:
            component_id: Component ID (optional)
            circuit_id: Circuit ID (optional)
            action: Description of the action
        """
        try:
            self.execute_query(
                """
                INSERT INTO usage_stats (component_id, circuit_id, action)
                VALUES (?, ?, ?)
                """,
                (component_id, circuit_id, action),
                commit=True
            )
            return True
        except sqlite3.Error as e:
            logger.error(f"Error logging usage: {e}")
            return False
    
    def get_component_usage_stats(self, limit=10):
        """Get most frequently used components.
        
        Args:
            limit: Maximum number of results
            
        Returns:
            List of tuples (component_id, component_name, usage_count)
        """
        cursor = self.execute_query(
            """
            SELECT component_id, COUNT(*) as count
            FROM usage_stats
            WHERE component_id IS NOT NULL
            GROUP BY component_id
            ORDER BY count DESC
            LIMIT ?
            """,
            (limit,)
        )
        
        results = []
        for row in cursor.fetchall():
            component_id = row['component_id']
            component = self.get_component(component_id)
            if component:
                results.append((component_id, component.name, row['count']))
        
        return results
