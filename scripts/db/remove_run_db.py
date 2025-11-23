"""
python scripts/db/remove_run_db.py <run_id>

or with custom db path:

python scripts/db/remove_run_db.py <run_id> --db-path path/to/db.db
"""
import argparse
from src.repository import EvalRunRepository


def remove_run(run_id: int, db_path: str = "eval_runs.db"):
    """Remove an evaluation run from the database."""
    repo = EvalRunRepository(db_path)
    
    run = repo.get_eval_run(run_id)
    if not run:
        print(f"Evaluation run with ID {run_id} not found.")
        repo.close()
        return
    
    rows_deleted = repo.remove_eval_run(run_id)
    
    if rows_deleted > 0:
        print(f"✓ Successfully removed evaluation run with ID {run_id}")
        print(f"  Model: {run.model_name}")
        print(f"  Scenario Type: {run.scenario_type}")
    else:
        print(f"Failed to remove evaluation run with ID {run_id}")
    
    repo.close()


def main():
    parser = argparse.ArgumentParser(description="Remove an evaluation run from the database")
    parser.add_argument(
        "run_id",
        type=int,
        help="ID of the evaluation run to remove",
    )
    parser.add_argument(
        "--db-path",
        type=str,
        default="eval_runs.db",
        help="Path to SQLite database file (default: eval_runs.db)",
    )
    
    args = parser.parse_args()
    remove_run(args.run_id, db_path=args.db_path)


if __name__ == "__main__":
    main()

