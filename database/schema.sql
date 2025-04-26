-- Circuit Simulator Database Schema

-- Components table
CREATE TABLE IF NOT EXISTS components (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    type TEXT NOT NULL,
    name TEXT NOT NULL,
    description TEXT,
    properties TEXT NOT NULL,  -- JSON object
    image_path TEXT,
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Saved circuits table
CREATE TABLE IF NOT EXISTS saved_circuits (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    description TEXT,
    circuit_data TEXT NOT NULL,  -- JSON object
    thumbnail TEXT,  -- Base64 encoded image
    created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    modified_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Usage statistics table
CREATE TABLE IF NOT EXISTS usage_stats (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    component_id INTEGER,
    circuit_id INTEGER,
    action TEXT NOT NULL,
    timestamp TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (component_id) REFERENCES components (id),
    FOREIGN KEY (circuit_id) REFERENCES saved_circuits (id)
);

-- User settings table
CREATE TABLE IF NOT EXISTS user_settings (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    setting_key TEXT NOT NULL UNIQUE,
    setting_value TEXT NOT NULL,
    updated_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
);

-- Tags table for organizing circuits
CREATE TABLE IF NOT EXISTS tags (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL UNIQUE,
    color TEXT
);

-- Circuit tags relationship table
CREATE TABLE IF NOT EXISTS circuit_tags (
    circuit_id INTEGER NOT NULL,
    tag_id INTEGER NOT NULL,
    PRIMARY KEY (circuit_id, tag_id),
    FOREIGN KEY (circuit_id) REFERENCES saved_circuits (id) ON DELETE CASCADE,
    FOREIGN KEY (tag_id) REFERENCES tags (id) ON DELETE CASCADE
);

-- Create indexes for better performance
CREATE INDEX IF NOT EXISTS idx_components_type ON components (type);
CREATE INDEX IF NOT EXISTS idx_saved_circuits_modified ON saved_circuits (modified_at);
CREATE INDEX IF NOT EXISTS idx_usage_stats_component ON usage_stats (component_id);
CREATE INDEX IF NOT EXISTS idx_usage_stats_circuit ON usage_stats (circuit_id);
CREATE INDEX IF NOT EXISTS idx_usage_stats_timestamp ON usage_stats (timestamp);
