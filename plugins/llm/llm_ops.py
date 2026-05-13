from plugins.shared import collect_files, summarize_paths


def llm_find_prompt_files(project_path: str) -> str:
    files = collect_files(
        project_path,
        patterns=("*.md", "*.txt", "*.json", "*.yaml", "*.yml", "*.py", "*.ts", "*.js"),
        name_terms=("prompt", "system", "instruction"),
        limit=60,
    )
    return summarize_paths("Prompt files:", files, "No prompt-related files found.")


def llm_find_model_configs(project_path: str) -> str:
    files = collect_files(
        project_path,
        patterns=("*.json", "*.yaml", "*.yml", "*.py", "*.ts", "*.js", "*.toml"),
        content_terms=("model", "temperature", "max_tokens", "gpt-", "anthropic", "openai"),
        limit=60,
    )
    return summarize_paths("Model config files:", files, "No model configuration files found.")


def llm_list_eval_assets(project_path: str) -> str:
    files = collect_files(
        project_path,
        patterns=("*.json", "*.jsonl", "*.yaml", "*.yml", "*.csv", "*.md"),
        name_terms=("eval", "benchmark", "rubric", "dataset", "golden"),
        limit=60,
    )
    return summarize_paths("LLM eval assets:", files, "No eval or benchmark assets found.")


def llm_list_guardrail_files(project_path: str) -> str:
    files = collect_files(
        project_path,
        patterns=("*.json", "*.yaml", "*.yml", "*.md", "*.py", "*.ts", "*.js"),
        content_terms=("guardrail", "moderation", "safety", "policy"),
        limit=60,
    )
    return summarize_paths("Guardrail files:", files, "No guardrail or moderation files found.")


TOOLS = {
    "llm_find_prompt_files": {"fn": llm_find_prompt_files, "description": "Find prompt and instruction files"},
    "llm_find_model_configs": {"fn": llm_find_model_configs, "description": "Find LLM model configuration files"},
    "llm_list_eval_assets": {"fn": llm_list_eval_assets, "description": "List LLM eval datasets and rubrics"},
    "llm_list_guardrail_files": {"fn": llm_list_guardrail_files, "description": "Find guardrail and moderation files"},
}
