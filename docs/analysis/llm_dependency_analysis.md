# LLM Dependency Analysis for Issue #43

## Objective
Complete isolation of LLM-related dependencies when ENABLE_LLM=false.
Application must run with requirements-minimal.txt only (no langchain, openai, anthropic, etc.)

## LLM-Related Packages (to be isolated)
1. langchain (+ langchain-*)
2. openai
3. anthropic
4. deepseek
5. ollama
6. mem0ai
7. browser-use
8. faiss-cpu

## Analysis Date
2025-10-16

## Files with LLM Dependencies

### Critical Files (Direct LLM imports)
