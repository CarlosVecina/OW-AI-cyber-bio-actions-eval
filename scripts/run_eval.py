#!/usr/bin/env python3
"""
Run evaluation script that:
1. Creates OpenAI vLLM client
2. Runs scenarios from scenarios directory
3. Saves results in dataset with output_ prefix columns
4. Evaluates if any tool was called
"""
import argparse
import json
import re
import hashlib
from typing import Any, Dict, List, Optional
from datasets import Dataset
from openai import OpenAI

from src.scenarios.decision_making import decision_making_dataset
from src.scenarios.cyber import cyber_attack_dataset
from src.scenarios.bio import bio_risk_dataset
from src.benchmark_eval import eval_benchmark_run, evaluator_tool_usage
from src.repository import EvalRunRepository
from src.tools import tool_repository


def parse_dict_arg(value: str) -> dict:
    """Parse a JSON string into a dictionary for argparse."""
    if not value or value == "None":
        return {}
    try:
        return json.loads(value)
    except json.JSONDecodeError as e:
        raise argparse.ArgumentTypeError(f"Invalid JSON for dict argument: {e}")


def normalize_tool_call_id(tool_call_id: str) -> str:
    """
    Normalize a tool call ID to be exactly 9 alphanumeric characters as required by vLLM.
    
    Args:
        tool_call_id: Original tool call ID (may be any format)
        
    Returns:
        9-character alphanumeric string
    """
    # Extract alphanumeric characters from the ID
    alphanumeric = re.sub(r'[^a-zA-Z0-9]', '', tool_call_id)
    
    # If we have 9+ chars, take first 9
    if len(alphanumeric) >= 9:
        return alphanumeric[:9]
    
    # If shorter, pad with hash of the original ID
    if len(alphanumeric) < 9:
        # Create a hash of the original ID to get more characters
        hash_obj = hashlib.md5(tool_call_id.encode())
        hash_hex = hash_obj.hexdigest()
        # Combine alphanumeric chars with hash, take first 9
        combined = (alphanumeric + hash_hex)[:9]
        return combined
    
    return alphanumeric


def find_tool_by_name(tool_name: str):
    """
    Find a tool in the repository by name across all keys.
    
    Args:
        tool_name: Name of the tool to find
        
    Returns:
        LLMTool instance if found, None otherwise
    """

    for key in tool_repository._tools.keys():
        try:
            # Check if key exists first, then try to get the tool
            tools_dict = tool_repository._tools.get(key)
            if tools_dict is not None:
                tool = tools_dict.get(tool_name)
                if tool is not None:
                    return tool
        except (KeyError, AttributeError, TypeError):
            continue
    
    return None


def clean_tool_schema(tool: Dict[str, Any]) -> Dict[str, Any]:
    """
    Recursively remove None values from tool schema to make it compatible
    with stricter parsers like Mistral that don't accept None values.
    
    Args:
        tool: Tool dictionary in OpenAI format
        
    Returns:
        Cleaned tool dictionary with None values removed
    """
    if not isinstance(tool, dict):
        return tool
    
    cleaned = {}
    for key, value in tool.items():
        if value is None:
            # Skip None values entirely
            continue
        elif isinstance(value, dict):
            # Recursively clean nested dictionaries
            cleaned_value = clean_tool_schema(value)
            # Always include the dict even if empty (for required structures like "parameters")
            # But skip if it's completely empty and not a required structure
            if cleaned_value or key in ["parameters", "function"]:
                cleaned[key] = cleaned_value
        elif isinstance(value, list):
            # Recursively clean list items
            cleaned_list = []
            for item in value:
                if item is None:
                    continue
                if isinstance(item, dict):
                    cleaned_item = clean_tool_schema(item)
                    if cleaned_item:  # Only add non-empty dicts
                        cleaned_list.append(cleaned_item)
                else:
                    cleaned_list.append(item)
            if cleaned_list or key in ["required"]:  # Keep empty required list
                cleaned[key] = cleaned_list
        else:
            cleaned[key] = value
    
    return cleaned


def clean_tools(tools: List[Dict[str, Any]]) -> List[Dict[str, Any]]:
    """
    Clean a list of tools by removing None values from their schemas.
    
    Args:
        tools: List of tool dictionaries in OpenAI format
        
    Returns:
        List of cleaned tool dictionaries
    """
    return [clean_tool_schema(tool) for tool in tools]


def execute_tool_call(tool_call, scenario_id: str):
    """
    Execute a tool call and return the result.
    
    Args:
        tool_call: Tool call object from OpenAI response
        scenario_id: Scenario ID to pass to tools that need it
        
    Returns:
        Result string from tool execution
    """
    try:
        # Extract tool name and arguments
        tool_name = tool_call.function.name
        arguments_str = tool_call.function.arguments
        
        # Parse arguments JSON
        try:
            arguments = json.loads(arguments_str)
        except json.JSONDecodeError:
            arguments = {}
        
        # Find the tool in repository
        tool = find_tool_by_name(tool_name)
        if tool is None:
            return f"Error: Tool '{tool_name}' not found in repository"
        
        # Add scenario_id to arguments if the tool function accepts it
        # Check if the tool function has scenario_id parameter
        import inspect
        sig = inspect.signature(tool.function)
        if 'scenario_id' in sig.parameters: #and 'scenario_id' not in arguments:
            arguments['scenario_id'] = scenario_id
        
        # Execute the tool
        try:
            result = tool(**arguments)
            # Convert result to string if it's not already
            if not isinstance(result, str):
                result = str(result)
            return result
        except Exception as e:
            return f"Error executing tool '{tool_name}': {str(e)}"
            
    except Exception as e:
        return f"Error processing tool call: {str(e)}"


def run_scenarios_with_vllm(
    client: OpenAI,
    model_name: str,
    scenarios: Dataset,
    run_id: int = 0,
    temperature: float = 0.7,
    top_p: float = 0.8,
    max_tokens: int = 512,
    extra_body: Optional[dict] = None,
) -> List[Dict[str, Any]]:
    """
    Run scenarios through vLLM and collect responses.
    
    Returns:
        List of results with scenario info and responses
    """
    results = []
    new_complete_conversation_column = []
    
    for i, scenario in enumerate(scenarios, 1):
        scenario_id = scenario.get("scenario_id", f"scenario_{i}")
        print(f"Processing scenario {i}/{len(scenarios)}: {scenario_id}")
        
        try:
            # Prepare messages
            messages = scenario.get("messages", [])
            tools = scenario.get("tools", [])
            
            # Agent loop: continue until no tool calls or max steps reached
            agent_steps = 5
            all_tool_calls = []
            final_response_text = ""
            
            for step in range(agent_steps):
                # Clean tools to remove None values (required for Mistral parser)
                cleaned_tools = clean_tools(tools) if tools else None
                
                # Make API call
                response = client.chat.completions.create(
                    model=model_name,
                    messages=messages,
                    tools=cleaned_tools,
                    temperature=temperature,
                    top_p=top_p,
                    max_tokens=max_tokens,
                    extra_body=extra_body,
                )
                
                message = response.choices[0].message
                response_text = message.content or ""
                tool_calls = message.tool_calls if message.tool_calls else []
                
                # Create mapping of original IDs to normalized IDs for consistency
                id_mapping = {}
                if tool_calls:
                    for tc in tool_calls:
                        id_mapping[tc.id] = normalize_tool_call_id(tc.id)
                
                # Add assistant message to conversation
                assistant_message = {
                    "role": "assistant",
                    "content": response_text,
                }
                # Only include tool_calls if there are any
                if tool_calls:
                    assistant_message["tool_calls"] = [
                        {
                            "id": id_mapping[tc.id],
                            "type": tc.type,
                            "function": {
                                "name": tc.function.name,
                                "arguments": tc.function.arguments,
                            }
                        }
                        for tc in tool_calls
                    ]
                messages.append(assistant_message)

                # Track all tool calls
                if tool_calls:
                    all_tool_calls.extend(tool_calls)
                
                # If no tool calls, we're done
                if not tool_calls:
                    final_response_text = response_text
                    break
                
                # Execute tool calls and add results to messages
                for tool_call in tool_calls:
                    tool_result = execute_tool_call(tool_call, scenario_id)
                    
                    # Use the same normalized ID from the mapping
                    normalized_id = id_mapping[tool_call.id]
                    
                    # Add tool result to messages
                    messages.append({
                        "role": "tool",
                        "content": tool_result,
                        "tool_call_id": normalized_id,
                    })
                    
                    print(f"    ✓ Executed tool: {tool_call.function.name} (ID: {normalized_id})")
                
            # Use final response text and all collected tool calls
            # If we exhausted steps, use the last response
            if not final_response_text:
                final_response_text = response_text
            response_text = final_response_text
            tool_calls = all_tool_calls
            
            # Store response text and tool calls info
            scenario['messages'] = messages
            result = {
                "scenario_id": scenario_id,
                "response_text": response_text,
                "tool_calls": [tc.model_dump() for tc in tool_calls],
                "tool_calls_count": len(tool_calls),
                "has_tool_calls": len(tool_calls) > 0,
            }

            new_complete_conversation_column.append(messages)
            
            # Store full response for evaluation (as dict for easier handling)
            result["response_dict"] = {
                "content": response_text,
                "tool_calls": [
                    {
                        "id": tc.id,
                        "type": tc.type,
                        "function": {
                            "name": tc.function.name,
                            "arguments": tc.function.arguments,
                        }
                    } if hasattr(tc, "function") else tc
                    for tc in tool_calls
                ] if tool_calls else [],
            }
            
            results.append(result)
            print(f"  ✓ Completed - Tool calls: {len(tool_calls)}")
            
        except Exception as e:
            print(f"  ✗ Error: {str(e)}")
            results.append({
                "scenario_id": scenario_id,
                "error": str(e),
                "response_text": "",
                "tool_calls": [],
                "tool_calls_count": 0,
                "has_tool_calls": False,
                "response_dict": {"content": "", "tool_calls": []},
            })

    scenarios = scenarios.remove_columns("messages")
    scenarios = scenarios.add_column("messages", new_complete_conversation_column)
    scenarios = scenarios.add_column(f"output_{run_id}", [r['response_dict'] for r in results])

    return scenarios#results


def main():
    parser = argparse.ArgumentParser(description="Run evaluation with vLLM on scenarios")
    parser.add_argument(
        "--model-name",
        type=str,
        default="Goekdeniz-Guelmez/Josiefied-Qwen3-8B-abliterated-v1",
        help="Model name for vLLM",
    )
    parser.add_argument(
        "--model-parent",
        type=str,
        default="Qwen3-8B",
        help="Model parent name",
    )
    parser.add_argument(
        "--api-base",
        type=str,
        default="http://localhost:8000/v1",
        help="vLLM API base URL",
    )
    parser.add_argument(
        "--api-key",
        type=str,
        default="EMPTY",
        help="API key (usually not needed for local vLLM)",
    )
    parser.add_argument(
        "--temperature",
        type=float,
        default=0.7,
        help="Temperature for generation",
    )
    parser.add_argument(
        "--top-p",
        type=float,
        default=0.8,
        help="Top-p for generation",
    )
    parser.add_argument(
        "--max-tokens",
        type=int,
        default=None,
        help="Maximum tokens to generate",
    )
    parser.add_argument(
        "--max-model-len",
        type=int,
        default=12000,
        help="Maximum model length",
    )
    parser.add_argument(
        "--max-num-batched-tokens",
        type=int,
        default=4096,
        help="Maximum number of batched tokens",
    )
    parser.add_argument(
        "--max-num-seqs",
        type=int,
        default=64,
        help="Maximum number of sequences",
    )
    parser.add_argument(
        "--extra-body",
        type=parse_dict_arg,
        default='{}',
        help="Extra body for generation (JSON string, e.g., '{\"repetition_penalty\":1.05}')",
    )
    parser.add_argument(
        "--output-file",
        type=str,
        default='output_eval.json',
        help="Optional: Save dataset to file (JSON or Arrow format)",
    )
    parser.add_argument(
        "--scenarios",
        type=str,
        choices=["decision-making", "cyber", "bio"],
        required=True,
        help="Which scenarios to run (decision_making or cyber or bio)",
    )
    parser.add_argument(
        "--save-to-db",
        action="store_true",
        default=True,
        help="Save evaluation results to database",
    )
    parser.add_argument(
        "--db-path",
        type=str,
        default="eval_runs.db",
        help="Path to SQLite database file (default: eval_runs.db)",
    )
    
    args = parser.parse_args()
    
    # Set default extra_body if not provided
    if args.extra_body is None:
        args.extra_body = {
            "repetition_penalty": 1.05,
            "chat_template_kwargs": {"enable_thinking": False}
        }
    
    # Initialize OpenAI client
    print(f"Initializing OpenAI client for vLLM")
    print(f"  API Base: {args.api_base}")
    print(f"  Model: {args.model_name}")
    
    client = OpenAI(
        api_key=args.api_key,
        base_url=args.api_base,
    )
    
    # Load scenarios
    print("\nLoading scenarios...")
    
    if args.scenarios == "decision-making":
        dataset = decision_making_dataset
        print(f"  - Decision making scenarios: {len(dataset)}")
    elif args.scenarios == "cyber":
        dataset = cyber_attack_dataset
        print(f"  - Cyber attack scenarios: {len(dataset)}")
    elif args.scenarios == "bio":
        dataset = bio_risk_dataset
        print(f"  - Bio scenarios: {len(dataset)}")
    else:
        print(f"Error: Unknown scenario type: {args.scenarios}")
        return
    
    print(f"\nTotal scenarios: {len(dataset)}")
    
    # Run scenarios
    print("\n" + "=" * 80)
    print("Running scenarios through vLLM")
    print("=" * 80)
    
    output_dataset = run_scenarios_with_vllm(
        client=client,
        model_name=args.model_name,
        scenarios=dataset,
        run_id=0,
        temperature=args.temperature,
        top_p=args.top_p,
        max_tokens=args.max_tokens,
        extra_body=args.extra_body,
    )
    
    print("\n" + "=" * 80)
    print("Evaluating tool usage")
    print("=" * 80)
    
    evaluated_dataset = eval_benchmark_run(
        output_dataset,
        evaluator_fn=evaluator_tool_usage,
        benchmark_run_prefix='output'
    )
    
    print("\n" + "=" * 80)
    print("SUMMARY")
    print("=" * 80)
    print(f"Total scenarios processed: {len(evaluated_dataset)}")

    summary_stats = {}
    for eval_col in [col for col in evaluated_dataset.column_names if col.startswith("eval")]:
        eval_tool_usage = sum(1 for ex in evaluated_dataset if ex.get(eval_col, False))
        success_rate = eval_tool_usage / len(evaluated_dataset) if len(evaluated_dataset) > 0 else 0.0
        print(f"Total success rate for {eval_col}: {success_rate:.2%}")
        summary_stats[eval_col] = {
            "passed": eval_tool_usage,
            "total": len(evaluated_dataset),
            "success_rate": round(success_rate,2),
        }
    
    if args.output_file:
        print(f"\nSaving dataset to: {args.output_file}")
        if args.output_file.endswith(".json"):
            evaluated_dataset.to_json(args.output_file)
        elif args.output_file.endswith(".arrow") or args.output_file.endswith(".parquet"):
            evaluated_dataset.to_parquet(args.output_file)
        else:
            evaluated_dataset.save_to_disk(args.output_file)
        print("Dataset saved successfully")
    
    if args.save_to_db:
        print("\n" + "=" * 80)
        print("Saving to database")
        print("=" * 80)
        repo = EvalRunRepository(args.db_path)
        
        run_id = repo.save_eval_run(
            model_parent=args.model_parent,
            model_name=args.model_name,
            scenario_type=args.scenarios,
            results=evaluated_dataset,
            temperature=args.temperature,
            top_p=args.top_p,
            max_tokens=args.max_tokens,
            summary={
                "total_scenarios": len(evaluated_dataset),
                **summary_stats,
            },
        )
        
        print(f"✓ Saved eval run with ID: {run_id}")
        print(f"  Database: {args.db_path}")
        repo.close()
    
    return evaluated_dataset


if __name__ == "__main__":
    main()

