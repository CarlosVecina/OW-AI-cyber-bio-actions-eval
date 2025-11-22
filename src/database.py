"""
SQLite database initialization and schema for storing evaluation runs.
"""
import sqlite3
import json
import threading
from pathlib import Path
from typing import Optional
from datetime import datetime


class Database:
    """SQLite database manager for evaluation runs."""
    
    def __init__(self, db_path: str = "eval_runs.db"):
        """
        Initialize database connection.
        
        Args:
            db_path: Path to SQLite database file
        """
        self.db_path = db_path
        self._local = threading.local()
        self._initialized = False
        self._init_lock = threading.Lock()
    
    def _get_connection(self) -> sqlite3.Connection:
        """Get thread-local database connection."""
        if not hasattr(self._local, 'conn') or self._local.conn is None:
            # Create connection with check_same_thread=False for thread safety
            self._local.conn = sqlite3.connect(
                self.db_path,
                check_same_thread=False
            )
            self._local.conn.row_factory = sqlite3.Row  # Enable column access by name
            
            # Initialize schema only once (using lock to prevent race conditions)
            if not self._initialized:
                with self._init_lock:
                    if not self._initialized:
                        self._initialize_schema(self._local.conn)
                        self._initialized = True
        
        return self._local.conn
    
    def _initialize_schema(self, conn: sqlite3.Connection):
        """Create database file and tables if they don't exist."""
        cursor = conn.cursor()
        
        # Create eval_runs table
        cursor.execute("""
            CREATE TABLE IF NOT EXISTS eval_runs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                model_parent TEXT,
                model_name TEXT NOT NULL,
                scenario_type TEXT NOT NULL,
                temperature REAL,
                top_p REAL,
                max_tokens INTEGER,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP,
                results_json TEXT NOT NULL,
                summary_json TEXT
            )
        """)
        
        # Create index on model_name and scenario_type for faster queries
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_model_scenario 
            ON eval_runs(model_name, scenario_type)
        """)
        
        # Create index on created_at for time-based queries
        cursor.execute("""
            CREATE INDEX IF NOT EXISTS idx_created_at 
            ON eval_runs(created_at)
        """)
        
        conn.commit()
    
    def close(self):
        """Close database connection for current thread."""
        if hasattr(self._local, 'conn') and self._local.conn:
            self._local.conn.close()
            self._local.conn = None
    
    def __enter__(self):
        """Context manager entry."""
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        self.close()
    
    def get_connection(self) -> sqlite3.Connection:
        """Get database connection (thread-safe)."""
        return self._get_connection()

