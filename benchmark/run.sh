#!/usr/bin/env bash
# Reproduce the local-model injection-resistance benchmark.
#
# Requires:
#   - Ollama running with the models below pulled (`ollama pull qwen2.5:7b`, ...)
#   - the suite installed: `pip install -e .`
#
# Writes one JSON report per model under benchmark/results/.
set -euo pipefail

MODELS=("qwen2.5:7b" "qwen2.5:14b" "mistral:latest")

mkdir -p benchmark/results
for m in "${MODELS[@]}"; do
  safe="${m//[:\/]/__}"
  echo "== $m =="
  INJECT_MODEL="ollama/$m" injection-suite --adapter reference \
    --json-out "benchmark/results/${safe}.json"
done

echo "Done. Results in benchmark/results/*.json"
