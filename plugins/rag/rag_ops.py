from plugins.shared import collect_files, summarize_paths


def rag_list_knowledge_files(project_path: str) -> str:
    files = collect_files(
        project_path,
        patterns=("*.md", "*.txt", "*.pdf", "*.html", "*.docx"),
        path_terms=("docs/", "knowledge/", "corpus/", "content/", "data/"),
        limit=80,
    )
    return summarize_paths("RAG knowledge files:", files, "No obvious RAG knowledge files found.")


def rag_find_embedding_config(project_path: str) -> str:
    files = collect_files(
        project_path,
        patterns=("*.py", "*.ts", "*.js", "*.json", "*.yaml", "*.yml", "*.toml"),
        content_terms=("embedding", "chunk_size", "retriever", "similarity_search"),
        limit=60,
    )
    return summarize_paths("Embedding/retrieval config files:", files, "No embedding or retrieval config files found.")


def rag_find_vector_store_files(project_path: str) -> str:
    files = collect_files(
        project_path,
        patterns=("*.py", "*.ts", "*.js", "*.json", "*.yaml", "*.yml"),
        content_terms=("faiss", "chroma", "qdrant", "weaviate", "pinecone", "milvus"),
        limit=60,
    )
    return summarize_paths("Vector store files:", files, "No vector store integration files found.")


def rag_list_eval_files(project_path: str) -> str:
    files = collect_files(
        project_path,
        patterns=("*.json", "*.jsonl", "*.yaml", "*.yml", "*.csv", "*.md"),
        name_terms=("eval", "question", "answer", "ground_truth", "retrieval"),
        limit=60,
    )
    return summarize_paths("RAG evaluation files:", files, "No RAG evaluation files found.")


TOOLS = {
    "rag_list_knowledge_files": {"fn": rag_list_knowledge_files, "description": "List likely RAG knowledge-base files"},
    "rag_find_embedding_config": {"fn": rag_find_embedding_config, "description": "Find embedding and retriever configs"},
    "rag_find_vector_store_files": {"fn": rag_find_vector_store_files, "description": "Find vector store integration files"},
    "rag_list_eval_files": {"fn": rag_list_eval_files, "description": "List RAG evaluation assets"},
}
