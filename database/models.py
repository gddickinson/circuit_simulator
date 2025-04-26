"""
Circuit Simulator - Database Models
---------------------------------
This module defines the data models for database entities.
"""

import datetime
import json


class Component:
    """Model representing an electronic component."""

    def __init__(self, type, name, description=None, properties=None, image_path=None):
        """Initialize a component.

        Args:
            type: Component type (resistor, capacitor, etc.)
            name: Component name
            description: Component description
            properties: Dictionary of component properties
            image_path: Path to component image
        """
        self.id = None
        self.type = type
        self.name = name
        self.description = description or ""
        self.properties = properties or {}
        self.image_path = image_path
        self.created_at = datetime.datetime.now()

    def __str__(self):
        return f"{self.name} ({self.type})"

    def to_dict(self):
        """Convert component to dictionary."""
        return {
            "id": self.id,
            "type": self.type,
            "name": self.name,
            "description": self.description,
            "properties": self.properties,
            "image_path": self.image_path,
            "created_at": self.created_at.isoformat() if self.created_at else None
        }

    @classmethod
    def from_dict(cls, data):
        """Create component from dictionary."""
        component = cls(
            data["type"],
            data["name"],
            data.get("description", ""),
            data.get("properties", {}),
            data.get("image_path")
        )
        component.id = data.get("id")

        if "created_at" in data and data["created_at"]:
            component.created_at = datetime.datetime.fromisoformat(data["created_at"])

        return component


class SavedCircuit:
    """Model representing a saved circuit."""

    def __init__(self, name, circuit_data, description=None, thumbnail=None):
        """Initialize a saved circuit.

        Args:
            name: Circuit name
            circuit_data: Dictionary of circuit data
            description: Circuit description
            thumbnail: Base64-encoded circuit thumbnail image
        """
        self.id = None
        self.name = name
        self.description = description or ""
        self.circuit_data = circuit_data
        self.thumbnail = thumbnail
        self.created_at = datetime.datetime.now()
        self.modified_at = self.created_at

    def __str__(self):
        return f"{self.name}"

    def to_dict(self):
        """Convert saved circuit to dictionary."""
        return {
            "id": self.id,
            "name": self.name,
            "description": self.description,
            "circuit_data": self.circuit_data,
            "thumbnail": self.thumbnail,
            "created_at": self.created_at.isoformat() if self.created_at else None,
            "modified_at": self.modified_at.isoformat() if self.modified_at else None
        }

    @classmethod
    def from_dict(cls, data):
        """Create saved circuit from dictionary."""
        circuit = cls(
            data["name"],
            data["circuit_data"],
            data.get("description", ""),
            data.get("thumbnail")
        )
        circuit.id = data.get("id")

        if "created_at" in data and data["created_at"]:
            circuit.created_at = datetime.datetime.fromisoformat(data["created_at"])

        if "modified_at" in data and data["modified_at"]:
            circuit.modified_at = datetime.datetime.fromisoformat(data["modified_at"])

        return circuit
