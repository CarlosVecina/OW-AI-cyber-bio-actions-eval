# Actions speak louder than words. Evaluating and securing AI Actions

Defensive Acceleration Hackaton.

<p align="center">
  <img src="https://yt3.googleusercontent.com/a62bOMN7EEnjW0F992zUvj4BBFpHwpfwVpPPbdpSGeQu9s6mw7bE_uqow5AY6NsgVwC0sclyUA=w1707-fcrop64=1,00005a57ffffa5a8-k-c0xffffffff-no-nd-rj" alt="Apart Header" style="max-width: 100%; height: auto;">
</p>


## Preparation

Base env setup using `python 3.12` and `UV`.

If you are lucky, a simple 

```
uv sync
```

would make your env ready to work.

If you face some vllm-pytorch-gcc-cpu/gpu-CUDA-OS headaches running it multiplatform, you can follow the `make setup` (or `make setup-with-deps` if you face gcc problems, take a look before executing!) steps and adapt some commands for your infra setup.


## Models

Run in `2xH100`. It should be possible and easy to run it also in 1xH100 or even a A100/T4 by twicking the params.

```
make run-all
```

### VibeThinker-1.5B

`make run-eval SCENARIOS=decision_making,cyber,bio MODEL_NAME="WeiboAI/VibeThinker-1.5B" MODEL_PARENT="WeiboAI/VibeThinker-1.5B" MAX_MODEL_LEN=17000 `

Abliterated

`make run-eval SCENARIOS=decision_making,cyber,bio MODEL_NAME=DavidAU/Qwen2.5-1.5B-VibeThinker-heretic-uncensored-abliterated" MODEL_PARENT="WeiboAI/VibeThinker-1.5B" MAX_MODEL_LEN=17000`


### Qwen3-8B

`make run-eval SCENARIOS=decision_making,cyber,bio MODEL_NAME="Qwen/Qwen3-8B" MODEL_PARENT="Qwen3-8B" MAX_MODEL_LEN=17000` 

Abliterated

`make run-eval SCENARIOS=decision_making,cyber,bio MODEL_NAME="Goekdeniz-Guelmez/Josiefied-Qwen3-8B-abliterated-v1" MODEL_PARENT="Qwen3-8B" MAX_MODEL_LEN=20000` 

Step by step:
`vllm serve Goekdeniz-Guelmez/Josiefied-Qwen3-8B-abliterated-v1 --tensor-parallel-size 1 --gpu-memory-utilization 0.95 --max-model-len 12000 --enable-auto-tool-choice --tool-call-parser hermes`
`uv run python scripts/run_eval.py --scenarios decision-making`


### Mistral-8B

```
make run-eval SCENARIOS=decision-making,cyber,bio MODEL_NAME="mistralai/Ministral-8B-Instruct-2410" MODEL_PARENT="Mistral-8B" TOOL_CALL_PARSER="mistral" TOKENIZER_MODE="mistral" EXTRA_BODY='{}'
``` 

Abliterated

```
make run-eval SCENARIOS=decision-making,cyber MODEL_NAME="realoperator42/ministral-8B-Instruct-2410-abliterated" MODEL_PARENT="Mistral-8B" TOOL_CALL_PARSER="mistral" TOKENIZER_MODE="mistral" TOKENIZER="mistralai/Ministral-8B-Instruct-2410"  EXTRA_BODY='{}' MAX_MODEL_LEN=32768
``` 

Step by step:
`vllm serve mistralai/Ministral-8B-Instruct-2410 --tensor-parallel-size 1 --gpu-memory-utilization 0.95 --max-model-len 12000 --enable-auto-tool-choice --tool-call-parser mistral --load-format mistral --config-format mistral`
`uv run python scripts/run_eval.py --scenarios decision-making --model-name mistralai/Ministral-8B-Instruct-2410 --model-parent Mistral-8B`

### Deepseek

make run-eval SCENARIOS=decision-making,cyber,bio MODEL_NAME="deepseek-ai/DeepSeek-R1-Distill-Llama-70B" MODEL_PARENT="DeepSeek-R1-70B" TOOL_CALL_PARSER="deepseek_v31" MAX_MODEL_LEN=4096 GPU_MEMORY_UTILIZATION=0.8 MAX_NUM_BATCHED_TOKENS=256 EXTRA_BODY='{}' ENFORCE_EAGER=true

vllm serve deepseek-ai/DeepSeek-R1-Distill-Llama-70B
    --enable-auto-tool-choice 
    --tensor-parallel-size 2
    --tool-call-parser deepseek_v31 
    --max-model-len 4096 --gpu-memory-utilization 0.8 --max-num-batched-tokens 256

deepseek-ai/DeepSeek-R1-Distill-Llama-70B

vllm serve cerebras/MiniMax-M2-REAP-162B-A10B \
    --tensor-parallel-size 8 \
    --tool-call-parser minimax_m2 \
    --reasoning-parser minimax_m2_append_think \
    --trust-remote-code \
    --enable_expert_parallel \
    --enable-auto-tool-choice --gpu-memory-utilization 0.8 --max-model-len 4096  

### GTP-OSS 120B

```
make run-eval SCENARIOS=decision-making,cyber,bio MODEL_NAME="openai/gpt-oss-120b" MODEL_PARENT="gptoss-120B" TOOL_CALL_PARSER="openai" EXTRA_BODY='{}'
```

Abliterated

```
make run-eval SCENARIOS=decision-making,cyber,bio MODEL_NAME="kldzj/gpt-oss-120b-heretic" MODEL_PARENT="gptoss-120B" TOOL_CALL_PARSER="openai" EXTRA_BODY='{}'
```

Step by step:
```
vllm serve kldzj/gpt-oss-120b-heretic-v2-bf16 --tensor-parallel-size 2 --tool-call-parser openai --enable-auto-tool-choice --max-model-len 4096 --gpu-memory-utilization 0.8 --max-num-batched-tokens 256

uv run python scripts/run_eval.py --scenarios decision-making --model-name openai/gpt-oss-120b --model-parent gtposs-120B
```

## App

The app serves the database created after running the evaluations. It uses the same repository to retrieve overall stats and experiment runs.

`uv run streamlit run app/app.py`