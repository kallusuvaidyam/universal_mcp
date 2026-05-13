from plugins.shared import collect_files, summarize_paths


def mysql_find_connection_files(project_path: str) -> str:
    files = collect_files(
        project_path,
        patterns=("*.env*", "*.py", "*.ts", "*.js", "*.json", "*.yaml", "*.yml", "*.toml", "*.php"),
        content_terms=("mysql", "mysql2", "pymysql", "mysqlclient", "mysql.connector"),
        limit=60,
    )
    return summarize_paths("MySQL connection files:", files, "No MySQL connection files found.")


def mysql_list_migration_files(project_path: str) -> str:
    files = collect_files(
        project_path,
        patterns=("*.py", "*.ts", "*.js", "*.php", "*.sql"),
        path_terms=("migrations/", "database/migrations/", "prisma/migrations/", "db/migrate/"),
        limit=80,
    )
    return summarize_paths("MySQL migration files:", files, "No MySQL migration files found.")


def mysql_list_schema_files(project_path: str) -> str:
    files = collect_files(
        project_path,
        patterns=("*.sql", "schema.prisma", "*.php", "*.py"),
        name_terms=("schema", "ddl", "structure"),
        limit=60,
    )
    return summarize_paths("MySQL schema files:", files, "No MySQL schema files found.")


def mysql_list_seed_files(project_path: str) -> str:
    files = collect_files(
        project_path,
        patterns=("*.py", "*.ts", "*.js", "*.php", "*.sql", "*.json"),
        path_terms=("seeds/", "fixtures/", "database/seeders/"),
        name_terms=("seed", "fixture"),
        limit=60,
    )
    return summarize_paths("MySQL seed files:", files, "No MySQL seed files found.")


TOOLS = {
    "mysql_find_connection_files": {"fn": mysql_find_connection_files, "description": "Find MySQL connection files"},
    "mysql_list_migration_files": {"fn": mysql_list_migration_files, "description": "List MySQL migration files"},
    "mysql_list_schema_files": {"fn": mysql_list_schema_files, "description": "List MySQL schema files"},
    "mysql_list_seed_files": {"fn": mysql_list_seed_files, "description": "List MySQL seed files"},
}
