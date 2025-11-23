#!/usr/bin/env python3
"""
Script to query and display evaluation runs from the database.
"""
import argparse
import json
from src.repository import EvalRunRepository


def list_runs(
    model_name: str = None,
    scenario_type: str = None,
    limit: int = 10,
    db_path: str = "eval_runs.db",
):
    """List evaluation runs from the database."""
    repo = EvalRunRepository(db_path)
    
    runs = repo.get_eval_runs(
        model_name=model_name,
        scenario_type=scenario_type,
        limit=limit,
    )
    
    if not runs:
        print("No evaluation runs found.")
        return
    
    print(f"\nFound {len(runs)} evaluation run(s):\n")
    print("-" * 80)
    
    for run in runs:
        print(f"ID: {run['id']}")
        print(f"  Model: {run['model_name']}")
        print(f"  Scenario Type: {run['scenario_type']}")
        print(f"  Created: {run['created_at']}")
        if run['temperature'] is not None:
            print(f"  Temperature: {run['temperature']}")
        if run['top_p'] is not None:
            print(f"  Top-p: {run['top_p']}")
        if run['max_tokens'] is not None:
            print(f"  Max Tokens: {run['max_tokens']}")
        if run['summary']:
            print(f"  Summary: {json.dumps(run['summary'], indent=4)}")
        print(f"  Results: {len(run['results'])} scenarios")
        print("-" * 80)
    
    repo.close()


def show_run(run_id: int, db_path: str = "eval_runs.db"):
    """Show details of a specific evaluation run."""
    repo = EvalRunRepository(db_path)
    
    run = repo.get_eval_run(run_id)
    if not run:
        print(f"Evaluation run with ID {run_id} not found.")
        return
    
    print(f"\nEvaluation Run #{run_id}")
    print("=" * 80)
    print(f"Model: {run['model_name']}")
    print(f"Scenario Type: {run['scenario_type']}")
    print(f"Created: {run['created_at']}")
    if run['temperature'] is not None:
        print(f"Temperature: {run['temperature']}")
    if run['top_p'] is not None:
        print(f"Top-p: {run['top_p']}")
    if run['max_tokens'] is not None:
        print(f"Max Tokens: {run['max_tokens']}")
    
    if run['summary']:
        print(f"\nSummary:")
        print(json.dumps(run['summary'], indent=2))
    
    print(f"\nResults: {len(run['results'])} scenarios")
    print("\nFirst 3 scenarios:")
    for i, result in enumerate(run['results'][:3], 1):
        print(f"\n  Scenario {i}:")
        print(f"    ID: {result.get('scenario_id', 'N/A')}")
        if 'eval_0' in result:
            print(f"    Eval Result: {result['eval_0']}")
    
    repo.close()


def show_stats(db_path: str = "eval_runs.db"):
    """Show summary statistics."""
    repo = EvalRunRepository(db_path)
    
    stats = repo.get_summary_stats()
    
    print("\nDatabase Statistics")
    print("=" * 80)
    print(f"Total Runs: {stats['total_runs']}")
    
    if stats['by_model']:
        print(f"\nRuns by Model:")
        for model, count in stats['by_model'].items():
            print(f"  {model}: {count}")
    
    if stats['by_scenario_type']:
        print(f"\nRuns by Scenario Type:")
        for scenario, count in stats['by_scenario_type'].items():
            print(f"  {scenario}: {count}")
    
    if stats['latest_run']:
        print(f"\nLatest Run:")
        print(f"  ID: {stats['latest_run']['id']}")
        print(f"  Model: {stats['latest_run']['model_name']}")
        print(f"  Scenario Type: {stats['latest_run']['scenario_type']}")
        print(f"  Created: {stats['latest_run']['created_at']}")
    
    repo.close()


def main():
    parser = argparse.ArgumentParser(description="Query evaluation runs database")
    subparsers = parser.add_subparsers(dest="command", help="Command to execute")
    
    # List command
    list_parser = subparsers.add_parser("list", help="List evaluation runs")
    list_parser.add_argument("--model-name", type=str, help="Filter by model name")
    list_parser.add_argument("--scenario-type", type=str, choices=["decision_making", "cyber"], help="Filter by scenario type")
    list_parser.add_argument("--limit", type=int, default=10, help="Maximum number of results")
    list_parser.add_argument("--db-path", type=str, default="eval_runs.db", help="Path to database file")
    
    # Show command
    show_parser = subparsers.add_parser("show", help="Show details of a specific run")
    show_parser.add_argument("run_id", type=int, help="ID of the evaluation run")
    show_parser.add_argument("--db-path", type=str, default="eval_runs.db", help="Path to database file")
    
    # Stats command
    stats_parser = subparsers.add_parser("stats", help="Show database statistics")
    stats_parser.add_argument("--db-path", type=str, default="eval_runs.db", help="Path to database file")
    
    args = parser.parse_args()
    
    if args.command == "list":
        list_runs(
            model_name=args.model_name,
            scenario_type=args.scenario_type,
            limit=args.limit,
            db_path=args.db_path,
        )
    elif args.command == "show":
        show_run(args.run_id, db_path=args.db_path)
    elif args.command == "stats":
        show_stats(db_path=args.db_path)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()

