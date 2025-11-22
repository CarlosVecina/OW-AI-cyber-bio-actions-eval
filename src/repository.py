"""
Repository for storing and retrieving evaluation runs.
"""
import json
from typing import List, Dict, Any, Optional
from datetime import datetime
from datasets import Dataset
from pydantic import BaseModel

from src.database import Database


class EvalRun(BaseModel):
    id: int
    model_parent: str | None
    model_name: str
    scenario_type: str
    temperature: Optional[float] = None
    top_p: Optional[float] = None
    max_tokens: Optional[int] = None
    created_at: datetime
    results: List[Dict[str, Any]]
    summary: Optional[Dict[str, Any]] = None


class EvalRunRepository:
    """Repository for managing evaluation runs in the database."""
    
    def __init__(self, db_path: str = "eval_runs.db"):
        """
        Initialize repository with database connection.
        
        Args:
            db_path: Path to SQLite database file
        """
        self.db = Database(db_path)
    
    def save_eval_run(
        self,
        model_parent: str | None,
        model_name: str,
        scenario_type: str,
        results: Dataset,
        temperature: Optional[float] = None,
        top_p: Optional[float] = None,
        max_tokens: Optional[int] = None,
        summary: Optional[Dict[str, Any]] = None,
    ) -> int:
        """
        Save an evaluation run to the database.
        
        Args:
            model_parent: Parent name of the model used
            model_name: Name of the model used
            scenario_type: Type of scenarios (e.g., "decision_making", "cyber")
            results: Dataset containing the evaluation results
            temperature: Temperature parameter used
            top_p: Top-p parameter used
            max_tokens: Max tokens parameter used
            summary: Optional summary statistics dictionary
        
        Returns:
            ID of the inserted eval run
        """
        conn = self.db.get_connection()
        cursor = conn.cursor()
        
        # Convert dataset to JSON
        # Convert to list of dicts for JSON serialization
        results_list = [dict(row) for row in results]
        results_json = json.dumps(results_list)
        
        # Convert summary to JSON if provided
        summary_json = json.dumps(summary) if summary else None
        
        # TODO: migrate to SQLModel
        cursor.execute("""
            INSERT INTO eval_runs 
            (model_parent, model_name, scenario_type, temperature, top_p, max_tokens, results_json, summary_json)
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
        """, (
            model_parent,
            model_name,
            scenario_type,
            temperature,
            top_p,
            max_tokens,
            results_json,
            summary_json,
        ))
        
        run_id = cursor.lastrowid
        conn.commit()
        
        return run_id
    
    def get_eval_run(self, run_id: int) -> EvalRun | None:
        """
        Retrieve an evaluation run by ID.
        
        Args:
            run_id: ID of the eval run
        
        Returns:
            EvalRun object, or None if not found
        """
        conn = self.db.get_connection()
        cursor = conn.cursor()
        
        cursor.execute("""
            SELECT * FROM eval_runs WHERE id = ?
        """, (run_id,))
        
        row = cursor.fetchone()
        if row is None:
            return None
        
        return EvalRun(
            id=int(row["id"]),
            model_parent=row["model_parent"],
            model_name=row["model_name"],
            scenario_type=row["scenario_type"],
            temperature=float(row["temperature"]),
            top_p=float(row["top_p"]),
            max_tokens=row["max_tokens"],
            created_at=row["created_at"],
            results=json.loads(row["results_json"]),
            summary=json.loads(row["summary_json"]) if row["summary_json"] else None,
        )
    
    def get_eval_runs(
        self,
        model_parent: Optional[str] = None,
        model_name: Optional[str] = None,
        scenario_type: Optional[str] = None,
        limit: Optional[int] = None,
        order_by: str = "created_at",
        order_desc: bool = True,
    ) -> List[EvalRun | None] | None:
        """
        Retrieve evaluation runs with optional filters.
        
        Args:
            model_parent: Filter by model parent
            model_name: Filter by model name
            scenario_type: Filter by scenario type
            limit: Maximum number of results to return
            order_by: Column to order by (default: created_at)
            order_desc: Whether to order descending (default: True)
        
        Returns:
            List of EvalRun objects, or None if no runs found
        """
        conn = self.db.get_connection()
        cursor = conn.cursor()
        
        # Build query
        query = "SELECT * FROM eval_runs WHERE 1=1"
        params = []
        
        if model_parent:
            query += " AND model_parent = ?"
            params.append(model_parent)
        
        if model_name:
            query += " AND model_name = ?"
            params.append(model_name)
        
        if scenario_type:
            query += " AND scenario_type = ?"
            params.append(scenario_type)
        
        # Validate order_by column
        valid_columns = ["id", "model_parent", "model_name", "scenario_type", "created_at"]
        if order_by not in valid_columns:
            order_by = "created_at"
        
        query += f" ORDER BY {order_by} {'DESC' if order_desc else 'ASC'}"
        
        if limit:
            query += " LIMIT ?"
            params.append(limit)
        
        cursor.execute(query, params)
        rows = cursor.fetchall()
        
        return [
            EvalRun(
                id=int(row["id"]),
                model_parent=row["model_parent"],
                model_name=row["model_name"],
                scenario_type=row["scenario_type"],
                temperature=float(row["temperature"]),
                top_p=float(row["top_p"]),
                max_tokens=row["max_tokens"],
                created_at=row["created_at"],
                results=json.loads(row["results_json"]),
                summary=json.loads(row["summary_json"]) if row["summary_json"] else None,
            )
            for row in rows
        ] if rows else None
    
    def get_eval_run_results_as_dataset(self, run_id: int) -> Optional[Dataset]:
        """
        Retrieve an evaluation run and return results as a Dataset.
        
        Args:
            run_id: ID of the eval run
        
        Returns:
            Dataset containing the results, or None if not found
        """
        eval_run = self.get_eval_run(run_id)
        if eval_run is None:
            return None
        
        # Convert results list back to Dataset
        return Dataset.from_list(eval_run["results"])
    
    def get_summary_stats(self) -> Dict[str, Any]:
        """
        Get summary statistics about all eval runs.
        
        Returns:
            Dictionary with summary statistics
        """
        conn = self.db.get_connection()
        cursor = conn.cursor()
        
        # Total runs
        cursor.execute("SELECT COUNT(*) as total FROM eval_runs")
        total = cursor.fetchone()["total"]
        
        # Runs by model
        cursor.execute("""
            SELECT model_name, COUNT(*) as count 
            FROM eval_runs 
            GROUP BY model_name
        """)
        by_model = {row["model_name"]: row["count"] for row in cursor.fetchall()}
        
        # Runs by scenario type
        cursor.execute("""
            SELECT scenario_type, COUNT(*) as count 
            FROM eval_runs 
            GROUP BY scenario_type
        """)
        by_scenario = {row["scenario_type"]: row["count"] for row in cursor.fetchall()}
        
        # Latest run
        cursor.execute("""
            SELECT id, model_name, scenario_type, created_at 
            FROM eval_runs 
            ORDER BY created_at DESC 
            LIMIT 1
        """)
        latest = cursor.fetchone()
        latest_run = {
            "id": latest["id"],
            "model_name": latest["model_name"],
            "scenario_type": latest["scenario_type"],
            "created_at": latest["created_at"],
        } if latest else None
        
        return {
            "total_runs": total,
            "by_model": by_model,
            "by_scenario_type": by_scenario,
            "latest_run": latest_run,
        }
    
    def close(self):
        """Close database connection."""
        self.db.close()

