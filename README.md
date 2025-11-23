# Actions speak louder than words. Evaluating and securing AI Actions

Defensive Acceleration Hackaton.

<p align="center">
  <img src="https://yt3.googleusercontent.com/a62bOMN7EEnjW0F992zUvj4BBFpHwpfwVpPPbdpSGeQu9s6mw7bE_uqow5AY6NsgVwC0sclyUA=w1707-fcrop64=1,00005a57ffffa5a8-k-c0xffffffff-no-nd-rj" alt="Apart Header" style="max-width: 100%; height: auto;">
</p>

## Deployed evals

You can find our AI OW tool / MCP usage **main experiment results deployed here:
https://ow-ai-cyber-bio-actions-eval.streamlit.app/**

<br>


## Preparation

Base env setup using `python 3.12` and `UV`.

If you are lucky, a simple 

```
uv sync --all-groups
```

would make your env ready to work.

If you face some vllm-pytorch-gcc-cpu/gpu-CUDA-OS headaches running it multiplatform, you can follow the `make setup` (or `make setup-with-deps` if you face gcc problems, take a look before executing!) steps and adapt some commands for your infra setup.


## Run experiment

Run in `2xH100`. It should be possible and easy to run it also in 1xH100 or even a A100/T4 by twicking the params.

```
make run-all TENSOR_PARALLEL_SIZE=2
```

## App

The app serves the database created after running the evaluations. It uses the same repository to retrieve overall stats and experiment runs.

```
make run-app
```

## Models

### MiroThinker-1.0-8B

```
make run-eval SCENARIOS=decision_making,cyber,bio MODEL_NAME="miromind-ai/MiroThinker-v1.0-8B" MODEL_PARENT="miromind-ai/MiroThinker-v1.0-8B" MAX_TOKENS=900 TENSOR_PARALLEL_SIZE=2
```

Abliterated

```
make run-eval SCENARIOS=decision_making,cyber,bio MODEL_NAME="huihui-ai/Huihui-MiroThinker-v1.0-8B-abliterated" MODEL_PARENT="miromind-ai/MiroThinker-v1.0-8B" MAX_TOKENS=900 TENSOR_PARALLEL_SIZE=2
```


### Qwen3-8B

```
make run-eval SCENARIOS=decision_making,cyber,bio MODEL_NAME="Qwen/Qwen3-8B" MODEL_PARENT="Qwen3-8B" MAX_MODEL_LEN=17000
``` 

Abliterated

```
make run-eval SCENARIOS=decision_making,cyber,bio MODEL_NAME="Goekdeniz-Guelmez/Josiefied-Qwen3-8B-abliterated-v1" MODEL_PARENT="Qwen3-8B" MAX_MODEL_LEN=20000
``` 

### Mistral-8B

```
make run-eval SCENARIOS=decision-making,cyber,bio MODEL_NAME="mistralai/Ministral-8B-Instruct-2410" MODEL_PARENT="Mistral-8B" TOOL_CALL_PARSER="mistral" TOKENIZER_MODE="mistral" EXTRA_BODY='{}'
``` 

Abliterated

```
make run-eval SCENARIOS=decision-making,cyber MODEL_NAME="realoperator42/ministral-8B-Instruct-2410-abliterated" MODEL_PARENT="Mistral-8B" TOOL_CALL_PARSER="mistral" TOKENIZER_MODE="mistral" TOKENIZER="mistralai/Ministral-8B-Instruct-2410"  EXTRA_BODY='{}' MAX_MODEL_LEN=32768
``` 

### Qwen/Qwen3-32B

```
make run-eval SCENARIOS=decision_making,cyber,bio MODEL_NAME="Qwen/Qwen3-32B" MODEL_PARENT="Qwen3-32B" MAX_MODEL_LEN=17000 TENSOR_PARALLEL_SIZE=2
```
Abliterated, (need request access and HF token! `hf auth login`)
```
make run-eval SCENARIOS=decision_making,cyber,bio MODEL_NAME="huihui-ai/Qwen3-32B-abliterated" MODEL_PARENT="Qwen3-32B" MAX_MODEL_LEN=17000 TENSOR_PARALLEL_SIZE=2
```


### Olmo-3-32B-Think

```
make run-eval SCENARIOS=decision_making,cyber,bio MODEL_NAME="allenai/Olmo-3-32B-Think" MODEL_PARENT="Olmo-3-32B" MAX_TOKENS=900 TENSOR_PARALLEL_SIZE=2 TOOL_CALL_PARSER="olmo3"
```

### GTP-OSS 120B

```
make run-eval SCENARIOS=decision-making,cyber,bio MODEL_NAME="openai/gpt-oss-120b" MODEL_PARENT="gptoss-120B" TOOL_CALL_PARSER="openai" EXTRA_BODY='{}'
```

Abliterated

```
make run-eval SCENARIOS=decision-making,cyber,bio MODEL_NAME="kldzj/gpt-oss-120b-heretic" MODEL_PARENT="gptoss-120B" TOOL_CALL_PARSER="openai" EXTRA_BODY='{}'
```

#### If you want to run them with separated serving and the evals:
```
vllm serve kldzj/gpt-oss-120b-heretic-v2-bf16 --tensor-parallel-size 2 --tool-call-parser openai --enable-auto-tool-choice --max-model-len 4096 --gpu-memory-utilization 0.8 --max-num-batched-tokens 256

uv run python scripts/run_eval.py --scenarios decision-making --model-name openai/gpt-oss-120b --model-parent gtposs-120B

vllm serve mistralai/Ministral-8B-Instruct-2410 --tensor-parallel-size 1 --gpu-memory-utilization 0.95 --max-model-len 12000 --enable-auto-tool-choice --tool-call-parser mistral --load-format mistral --config-format mistral

uv run python scripts/run_eval.py --scenarios decision-making --model-name mistralai/Ministral-8B-Instruct-2410 --model-parent Mistral-8B
```