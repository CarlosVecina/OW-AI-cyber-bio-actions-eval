#!/usr/bin/env python3
"""
Example script showing how to save evaluation results to the database.
This can be integrated into run_eval.py or used standalone.
"""
import argparse
import json
from datasets import Dataset

from src.repository import EvalRunRepository


def save_eval_results_to_db(
    results_file: str,
    model_name: str,
    scenario_type: str,
    temperature: float = None,
    top_p: float = None,
    max_tokens: int = None,
    db_path: str = "eval_runs.db",
):
    """
    Load evaluation results from a JSON file and save to database.
    
    Args:
        results_file: Path to JSON file containing evaluation results
        model_name: Name of the model used
        scenario_type: Type of scenarios (decision_making or cyber)
        temperature: Temperature parameter used
        top_p: Top-p parameter used
        max_tokens: Max tokens parameter used
        db_path: Path to SQLite database file
    """
    # Load results from JSON file
    print(f"Loading results from: {results_file}")
    dataset = Dataset.from_json(results_file)
    
    # Calculate summary statistics
    summary = {}
    if "eval_0" in dataset.column_names:
        eval_col = "eval_0"
        total = len(dataset)
        passed = sum(1 for ex in dataset if ex.get(eval_col, False))
        summary = {
            "total_scenarios": total,
            "passed": passed,
            "failed": total - passed,
            "success_rate": passed / total if total > 0 else 0.0,
        }
    
    # Save to database
    print(f"Saving to database: {db_path}")
    repo = EvalRunRepository(db_path)
    
    run_id = repo.save_eval_run(
        model_name=model_name,
        scenario_type=scenario_type,
        results=dataset,
        temperature=temperature,
        top_p=top_p,
        max_tokens=max_tokens,
        summary=summary,
    )
    
    print(f"✓ Saved eval run with ID: {run_id}")
    print(f"  Model: {model_name}")
    print(f"  Scenario type: {scenario_type}")
    if summary:
        print(f"  Success rate: {summary['success_rate']:.2%}")
    
    # Show summary stats
    stats = repo.get_summary_stats()
    print(f"\nDatabase summary:")
    print(f"  Total runs: {stats['total_runs']}")
    print(f"  By model: {stats['by_model']}")
    print(f"  By scenario: {stats['by_scenario_type']}")
    
    repo.close()


def main():
    parser = argparse.ArgumentParser(description="Save evaluation results to database")
    parser.add_argument(
        "--results-file",
        type=str,
        required=True,
        help="Path to JSON file containing evaluation results",
    )
    parser.add_argument(
        "--model-name",
        type=str,
        required=True,
        help="Name of the model used",
    )
    parser.add_argument(
        "--scenario-type",
        type=str,
        choices=["decision_making", "cyber"],
        required=True,
        help="Type of scenarios",
    )
    parser.add_argument(
        "--temperature",
        type=float,
        default=None,
        help="Temperature parameter used",
    )
    parser.add_argument(
        "--top-p",
        type=float,
        default=None,
        help="Top-p parameter used",
    )
    parser.add_argument(
        "--max-tokens",
        type=int,
        default=None,
        help="Max tokens parameter used",
    )
    parser.add_argument(
        "--db-path",
        type=str,
        default="eval_runs.db",
        help="Path to SQLite database file",
    )
    
    args = parser.parse_args()
    
    save_eval_results_to_db(
        results_file=args.results_file,
        model_name=args.model_name,
        scenario_type=args.scenario_type,
        temperature=args.temperature,
        top_p=args.top_p,
        max_tokens=args.max_tokens,
        db_path=args.db_path,
    )


if __name__ == "__main__":
    main()

