from plugins.shared import collect_files, summarize_paths


def postgres_find_connection_files(project_path: str) -> str:
    files = collect_files(
        project_path,
        patterns=("*.env*", "*.py", "*.ts", "*.js", "*.json", "*.yaml", "*.yml", "*.toml", "*.rb"),
        content_terms=("postgresql", "postgres://", "postgresql://", "psycopg", "pg.Pool", "sequelize"),
        limit=60,
    )
    return summarize_paths("Postgres connection files:", files, "No Postgres connection files found.")


def postgres_list_migration_files(project_path: str) -> str:
    files = collect_files(
        project_path,
        patterns=("*.py", "*.ts", "*.js", "*.rb", "*.sql"),
        path_terms=("migrations/", "db/migrate/", "prisma/migrations/", "supabase/migrations/"),
        limit=80,
    )
    return summarize_paths("Postgres migration files:", files, "No Postgres migration files found.")


def postgres_list_schema_files(project_path: str) -> str:
    files = collect_files(
        project_path,
        patterns=("*.sql", "schema.prisma", "structure.sql", "schema.rb"),
        limit=60,
    )
    return summarize_paths("Postgres schema files:", files, "No Postgres schema files found.")


def postgres_list_seed_files(project_path: str) -> str:
    files = collect_files(
        project_path,
        patterns=("*.py", "*.ts", "*.js", "*.rb", "*.sql", "*.json"),
        path_terms=("seeds/", "fixtures/", "db/seeds/", "supabase/seed/"),
        name_terms=("seed", "fixture"),
        limit=60,
    )
    return summarize_paths("Postgres seed files:", files, "No Postgres seed files found.")


TOOLS = {
    "postgres_find_connection_files": {"fn": postgres_find_connection_files, "description": "Find Postgres connection files"},
    "postgres_list_migration_files": {"fn": postgres_list_migration_files, "description": "List Postgres migration files"},
    "postgres_list_schema_files": {"fn": postgres_list_schema_files, "description": "List Postgres schema files"},
    "postgres_list_seed_files": {"fn": postgres_list_seed_files, "description": "List Postgres seed files"},
}
