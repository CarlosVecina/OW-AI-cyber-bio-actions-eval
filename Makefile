.PHONY: setup setup-with-deps help run-eval run-decision-making run-cyber run-all clean

# Default configuration
MODEL_NAME ?= Goekdeniz-Guelmez/Josiefied-Qwen3-8B-abliterated-v1
MODEL_PARENT ?= Qwen3-8B
PORT ?= 8000
HOST ?= 0.0.0.0
TENSOR_PARALLEL_SIZE ?= 1
GPU_MEMORY_UTILIZATION ?= 0.95
MAX_NUM_BATCHED_TOKENS ?= 4096
MAX_NUM_SEQS ?= 64
MAX_MODEL_LEN ?= 40000
MAX_TOKENS ?= none
ENABLE_AUTO_TOOL_CHOICE ?= true
TOOL_CALL_PARSER ?= hermes
SCENARIOS ?= decision_making
TEMPERATURE ?= 0.7
TOP_P ?= 0.8
#MAX_TOKENS ?= 512
OUTPUT_FILE ?= output_eval.json

ENFORCE_EAGER ?= false
CONFIG_FORMAT ?= none
LOAD_FORMAT ?= none
TOKENIZER_MODE ?= auto
TOKENIZER ?= none
EXTRA_BODY ?= {}

API_BASE = http://localhost:$(PORT)/v1

setup:
	@echo "Running setup script..."
	bash scripts/setup.sh

setup-with-deps:
	@echo "Running setup script with system dependencies..."
	bash scripts/setup.sh --install-system-deps

help:
	@echo "Available targets:"
	@echo "  make run-eval SCENARIOS=<decision_making|cyber>  - Run evaluation with specified scenarios"
	@echo "  make run-decision-making                         - Run decision_making scenarios"
	@echo "  make run-cyber                                   - Run cyber scenarios"
	@echo ""
	@echo "Configuration variables (override with VAR=value):"
	@echo "  MODEL_NAME              - Model name (default: $(MODEL_NAME))"
	@echo "  MODEL_PARENT            - Model parent name (default: $(MODEL_PARENT))"
	@echo "  PORT                    - Server port (default: $(PORT))"
	@echo "  HOST                    - Server host (default: $(HOST))"
	@echo "  SCENARIOS               - Scenario type (default: $(SCENARIOS))"
	@echo "  TEMPERATURE             - Generation temperature (default: $(TEMPERATURE))"
	@echo "  TOP_P                   - Top-p sampling (default: $(TOP_P))"
	@echo "  MAX_TOKENS              - Max tokens to generate (default: $(MAX_TOKENS))"
	@echo "  OUTPUT_FILE             - Output file path (default: $(OUTPUT_FILE))"
	@echo "  TENSOR_PARALLEL_SIZE    - Tensor parallel size (default: $(TENSOR_PARALLEL_SIZE))"
	@echo "  GPU_MEMORY_UTILIZATION  - GPU memory utilization (default: $(GPU_MEMORY_UTILIZATION))"
	@echo "  MAX_MODEL_LEN           - Max model length (default: $(MAX_MODEL_LEN))"
	@echo "  TOKENIZER_MODE          - Tokenizer mode (default: $(TOKENIZER_MODE))"
	@echo "  TOKENIZER               - Tokenizer model path (default: $(TOKENIZER))"
	@echo "  CONFIG_FORMAT           - Config format (default: $(CONFIG_FORMAT))"
	@echo "  LOAD_FORMAT             - Load format (default: $(LOAD_FORMAT))"

# Generic run target
run-eval:
	@echo "Running evaluation with scenarios: $(SCENARIOS)"
	@echo "Model: $(MODEL_NAME)"
	@echo "Port: $(PORT), Host: $(HOST)"
	MODEL_NAME=$(MODEL_NAME) \
	MODEL_PARENT=$(MODEL_PARENT) \
	PORT=$(PORT) \
	HOST=$(HOST) \
	TENSOR_PARALLEL_SIZE=$(TENSOR_PARALLEL_SIZE) \
	GPU_MEMORY_UTILIZATION=$(GPU_MEMORY_UTILIZATION) \
	MAX_NUM_BATCHED_TOKENS=$(MAX_NUM_BATCHED_TOKENS) \
	MAX_NUM_SEQS=$(MAX_NUM_SEQS) \
	MAX_MODEL_LEN=$(MAX_MODEL_LEN) \
	MAX_TOKENS=$(MAX_TOKENS) \
	ENABLE_AUTO_TOOL_CHOICE=$(ENABLE_AUTO_TOOL_CHOICE) \
	TOOL_CALL_PARSER=$(TOOL_CALL_PARSER) \
	TOKENIZER_MODE=$(TOKENIZER_MODE) \
	TOKENIZER=$(TOKENIZER) \
	CONFIG_FORMAT=$(CONFIG_FORMAT) \
	LOAD_FORMAT=$(LOAD_FORMAT) \
	SCENARIOS=$(SCENARIOS) \
	bash scripts/run_vllm_and_test.sh
#	PYTHON_SCRIPT="scripts/run_eval.py --scenarios $(SCENARIOS) --model-name $(MODEL_NAME) --model-parent $(MODEL_PARENT) --api-base $(API_BASE) --temperature $(TEMPERATURE) --top-p $(TOP_P) --output-file $(OUTPUT_FILE) --extra-body '$(EXTRA_BODY)'" \

run-decision-making:
	$(MAKE) run-eval SCENARIOS=decision_making

run-cyber:
	$(MAKE) run-eval SCENARIOS=cyber

# Clean up generated files
clean:
	rm -f vllm_server.log output_eval.json

run-all:
	make setup-with-deps
	make run-eval SCENARIOS=decision-making,cyber,bio MODEL_NAME="Qwen/Qwen3-8B" MODEL_PARENT="Qwen3-8B" MAX_MODEL_LEN=17000 TENSOR_PARALLEL_SIZE=2
	make run-eval SCENARIOS=decision-making,cyber,bio MODEL_NAME="Goekdeniz-Guelmez/Josiefied-Qwen3-8B-abliterated-v1" MODEL_PARENT="Qwen3-8B" MAX_MODEL_LEN=20000 TENSOR_PARALLEL_SIZE=2
	make run-eval SCENARIOS=decision-making,cyber,bio MODEL_NAME="mistralai/Ministral-8B-Instruct-2410" MODEL_PARENT="Mistral-8B" TOOL_CALL_PARSER="mistral" LOAD_FORMAT="mistral" CONFIG_FORMAT="mistral" TOKENIZER_MODE="mistral" EXTRA_BODY='{}' TENSOR_PARALLEL_SIZE=2
	make run-eval SCENARIOS=decision-making,cyber,bio MODEL_NAME="openai/gpt-oss-120b" MODEL_PARENT="gptoss-120B" TOOL_CALL_PARSER="openai" EXTRA_BODY='{}' TENSOR_PARALLEL_SIZE=2
	make run-eval SCENARIOS=decision-making,cyber,bio MODEL_NAME="kldzj/gpt-oss-120b-heretic" MODEL_PARENT="gptoss-120B" TOOL_CALL_PARSER="openai" EXTRA_BODY='{}' TENSOR_PARALLEL_SIZE=2
