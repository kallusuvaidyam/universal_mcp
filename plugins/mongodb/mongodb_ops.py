from plugins.shared import collect_files, summarize_paths


def mongodb_find_connection_files(project_path: str) -> str:
    files = collect_files(
        project_path,
        patterns=("*.env*", "*.py", "*.ts", "*.js", "*.json", "*.yaml", "*.yml", "*.toml"),
        content_terms=("mongodb://", "mongodb+srv://", "mongoose.connect", "pymongo", "mongoengine", "motor"),
        limit=60,
    )
    return summarize_paths("MongoDB connection files:", files, "No MongoDB connection files found.")


def mongodb_list_model_files(project_path: str) -> str:
    files = collect_files(
        project_path,
        patterns=("*.py", "*.ts", "*.js"),
        path_terms=("models/", "schemas/"),
        content_terms=("mongoose", "mongoengine", "beanie", "document"),
        limit=60,
    )
    return summarize_paths("MongoDB model/schema files:", files, "No MongoDB model files found.")


def mongodb_list_seed_files(project_path: str) -> str:
    files = collect_files(
        project_path,
        patterns=("*.py", "*.ts", "*.js", "*.json"),
        path_terms=("seeds/", "fixtures/"),
        name_terms=("seed", "fixture"),
        limit=60,
    )
    return summarize_paths("MongoDB seed files:", files, "No MongoDB seed files found.")


def mongodb_list_index_files(project_path: str) -> str:
    files = collect_files(
        project_path,
        patterns=("*.py", "*.ts", "*.js"),
        content_terms=("createindex", ".index(", "indexes =", "index=True"),
        limit=60,
    )
    return summarize_paths("MongoDB index files:", files, "No MongoDB index definitions found.")


TOOLS = {
    "mongodb_find_connection_files": {"fn": mongodb_find_connection_files, "description": "Find MongoDB connection files"},
    "mongodb_list_model_files": {"fn": mongodb_list_model_files, "description": "List MongoDB model/schema files"},
    "mongodb_list_seed_files": {"fn": mongodb_list_seed_files, "description": "List MongoDB seed files"},
    "mongodb_list_index_files": {"fn": mongodb_list_index_files, "description": "Find MongoDB index definitions"},
}
