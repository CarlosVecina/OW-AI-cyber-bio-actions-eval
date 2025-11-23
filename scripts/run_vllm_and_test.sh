#!/bin/bash

# Get the directory where this script is located and change to project root
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
PROJECT_ROOT="$( cd "$SCRIPT_DIR/.." && pwd )"
cd "$PROJECT_ROOT" || exit 1

# Configuration
if [ "$ENFORCE_EAGER" = "true" ]; then
    echo "Enforcing eager mode"
    ENFORCE_EAGER_FLAG="--enforce-eager"
else
    ENFORCE_EAGER_FLAG=""
fi

if [ "$ENABLE_AUTO_TOOL_CHOICE" = "true" ]; then
    echo "Enabling auto tool choice"
    ENABLE_AUTO_TOOL_CHOICE_FLAG="--enable-auto-tool-choice"
else
    ENABLE_AUTO_TOOL_CHOICE_FLAG=""
fi

if [ "$MAX_TOKENS" != "none" ]; then
    MAX_TOKENS_FLAG="--max-tokens $MAX_TOKENS"
else
    MAX_TOKENS_FLAG=""
fi

if [ "$TOKENIZER_MODE" != "none" ]; then
    TOKENIZER_MODE_FLAG="--tokenizer-mode \"$TOKENIZER_MODE\""
else
    TOKENIZER_MODE_FLAG=""
fi

if [ "$CONFIG_FORMAT" != "none" ]; then
    CONFIG_FORMAT_FLAG="--config-format \"$CONFIG_FORMAT\""
else
    CONFIG_FORMAT_FLAG=""
fi

if [ "$LOAD_FORMAT" != "none" ]; then
    LOAD_FORMAT_FLAG="--load-format \"$LOAD_FORMAT\""
else
    LOAD_FORMAT_FLAG=""
fi

if [ "$TOKENIZER" != "none" ] && [ -n "$TOKENIZER" ]; then
    TOKENIZER_FLAG="--tokenizer \"$TOKENIZER\""
else
    TOKENIZER_FLAG=""
fi

# Parse SCENARIOS into an array (support space or comma separated)
# Convert to array by replacing commas with spaces, then splitting
SCENARIOS_STR=$(echo "$SCENARIOS" | tr ',' ' ')
read -ra SCENARIOS_ARRAY <<< "$SCENARIOS_STR"

# Normalize scenario names: convert underscores to hyphens (e.g., decision_making -> decision-making)
normalize_scenario() {
    echo "$1" | tr '_' '-'
}

echo "Scenarios to run: ${SCENARIOS_ARRAY[*]}"

echo "Starting vLLM server with model: $MODEL_NAME"
echo "Port: $PORT, Host: $HOST"

# Start vLLM server in background
VLLM_CMD="vllm serve \"$MODEL_NAME\" \
    --tensor-parallel-size \"$TENSOR_PARALLEL_SIZE\" \
    --gpu-memory-utilization \"$GPU_MEMORY_UTILIZATION\" \
    --max-num-batched-tokens \"$MAX_NUM_BATCHED_TOKENS\" \
    --max-model-len \"$MAX_MODEL_LEN\" \
    --max-num-seqs \"$MAX_NUM_SEQS\" \
    --host \"$HOST\" \
    --port \"$PORT\" \
    $ENFORCE_EAGER_FLAG \
    $ENABLE_AUTO_TOOL_CHOICE_FLAG \
    --tool-call-parser \"$TOOL_CALL_PARSER\" \
    $TOKENIZER_MODE_FLAG \
    $TOKENIZER_FLAG \
    $CONFIG_FORMAT_FLAG \
    $LOAD_FORMAT_FLAG \
    > vllm_server.log 2>&1 &"
echo ""
echo "vLLM launch command:"
echo "$VLLM_CMD"
eval $VLLM_CMD

VLLM_PID=$!

echo "vLLM server started with PID: $VLLM_PID"
echo "Waiting for server to be ready..."

# Wait for server to be ready by checking the health endpoint
MAX_WAIT=300  # 5 minutes max wait
WAIT_INTERVAL=5
ELAPSED=0

while [ $ELAPSED -lt $MAX_WAIT ]; do
    if curl -s -f "http://localhost:$PORT/health" > /dev/null 2>&1; then
        echo "Server is ready!"
        break
    fi
    
    # Check if process is still running
    if ! kill -0 $VLLM_PID 2>/dev/null; then
        echo "Error: vLLM server process died. Check vllm_server.log for details."
        exit 1
    fi
    
    echo "Waiting for server... (${ELAPSED}s elapsed)"
    sleep $WAIT_INTERVAL
    ELAPSED=$((ELAPSED + WAIT_INTERVAL))
done

if [ $ELAPSED -ge $MAX_WAIT ]; then
    echo "Error: Server did not become ready within $MAX_WAIT seconds."
    kill $VLLM_PID 2>/dev/null
    exit 1
fi

# Run evaluation for each scenario
EXIT_CODE=0
SCENARIO_COUNT=${#SCENARIOS_ARRAY[@]}

for i in "${!SCENARIOS_ARRAY[@]}"; do
    SCENARIO="${SCENARIOS_ARRAY[$i]}"
    NORMALIZED_SCENARIO=$(normalize_scenario "$SCENARIO")
    
    echo ""
    echo "=========================================="
    echo "Running scenario $((i+1))/$SCENARIO_COUNT: $NORMALIZED_SCENARIO"
    echo "=========================================="
    
    # Build the Python command
    if [ -n "$PYTHON_SCRIPT" ]; then
        # If PYTHON_SCRIPT is provided, replace --scenarios argument with current scenario
        # Pattern: match --scenarios followed by one or more non-space words until next -- or end
        # First, try to remove --scenarios and all following words until next -- flag
        if echo "$PYTHON_SCRIPT" | grep -q -- "--scenarios"; then
            # Remove --scenarios and everything after it until next -- or end, then add new --scenarios
            PYTHON_CMD=$(echo "$PYTHON_SCRIPT" | sed -E "s/--scenarios[ ]+[^ ]+([ ]+--|$)/--scenarios $NORMALIZED_SCENARIO\1/")
            # If replacement didn't work (multiple words after --scenarios), use a different approach
            if [[ "$PYTHON_CMD" == "$PYTHON_SCRIPT" ]]; then
                # Remove everything from --scenarios to the next -- or end of line
                BASE_CMD=$(echo "$PYTHON_SCRIPT" | sed -E 's/[ ]+--scenarios.*(--|$)/ \1/' | sed 's/[ ]*$//')
                # Insert --scenarios after script name
                PYTHON_CMD=$(echo "$BASE_CMD" | sed "s|scripts/run_eval.py|scripts/run_eval.py --scenarios $NORMALIZED_SCENARIO|")
            fi
        else
            # --scenarios not found, append it after script name
            PYTHON_CMD=$(echo "$PYTHON_SCRIPT" | sed "s|scripts/run_eval.py|scripts/run_eval.py --scenarios $NORMALIZED_SCENARIO|")
        fi
    else
        # Build command from environment variables
        PYTHON_CMD="scripts/run_eval.py --scenarios $NORMALIZED_SCENARIO"
        [ -n "$MODEL_NAME" ] && PYTHON_CMD="$PYTHON_CMD --model-name $MODEL_NAME"
        [ -n "$MODEL_PARENT" ] && PYTHON_CMD="$PYTHON_CMD --model-parent $MODEL_PARENT"
        PYTHON_CMD="$PYTHON_CMD --api-base http://localhost:$PORT/v1"
        [ -n "$TEMPERATURE" ] && PYTHON_CMD="$PYTHON_CMD --temperature $TEMPERATURE"
        [ -n "$TOP_P" ] && PYTHON_CMD="$PYTHON_CMD --top-p $TOP_P"
        [ -n "$MAX_MODEL_LEN" ] && PYTHON_CMD="$PYTHON_CMD --max-model-len $MAX_MODEL_LEN"
        [ -n "$MAX_NUM_BATCHED_TOKENS" ] && PYTHON_CMD="$PYTHON_CMD --max-num-batched-tokens $MAX_NUM_BATCHED_TOKENS"
        [ -n "$MAX_NUM_SEQS" ] && PYTHON_CMD="$PYTHON_CMD --max-num-seqs $MAX_NUM_SEQS"
        [ -n "$MAX_TOKENS_FLAG" ] && PYTHON_CMD="$PYTHON_CMD $MAX_TOKENS_FLAG"
        [ -n "$OUTPUT_FILE" ] && PYTHON_CMD="$PYTHON_CMD --output-file $OUTPUT_FILE"
        [ -n "$EXTRA_BODY" ] && PYTHON_CMD="$PYTHON_CMD --extra-body '$EXTRA_BODY'"
    fi
    
    echo "Running: uv run python $PYTHON_CMD"
    
    # Run the Python script for this scenario
    eval "uv run python $PYTHON_CMD"
    SCENARIO_EXIT_CODE=$?
    
    if [ $SCENARIO_EXIT_CODE -ne 0 ]; then
        echo "Error: Scenario $NORMALIZED_SCENARIO failed with exit code $SCENARIO_EXIT_CODE"
        EXIT_CODE=$SCENARIO_EXIT_CODE
        # Continue with other scenarios instead of breaking
    else
        echo "✓ Scenario $NORMALIZED_SCENARIO completed successfully"
    fi
done

echo ""
echo "=========================================="
echo "All scenarios completed"
echo "=========================================="

# Cleanup: kill vLLM server
echo "Stopping vLLM server..."
kill $VLLM_PID 2>/dev/null
wait $VLLM_PID 2>/dev/null

exit $EXIT_CODE

