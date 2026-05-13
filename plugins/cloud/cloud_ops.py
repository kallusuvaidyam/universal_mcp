from plugins.shared import collect_files, summarize_paths


def cloud_list_iac_files(project_path: str) -> str:
    files = collect_files(
        project_path,
        patterns=("*.tf", "*.tfvars", "*.yaml", "*.yml", "*.json", "*.bicep"),
        path_terms=("terraform", "cloudformation", "pulumi", "infrastructure", "infra", "deploy"),
        limit=100,
    )
    return summarize_paths("Cloud IaC files:", files, "No infrastructure-as-code files found.")


def cloud_list_k8s_manifests(project_path: str) -> str:
    files = collect_files(
        project_path,
        patterns=("*.yaml", "*.yml"),
        content_terms=("apiversion:", "kind:"),
        path_terms=("k8s", "kubernetes", "helm", "charts", "manifests", "deploy"),
        limit=100,
    )
    return summarize_paths("Kubernetes manifests:", files, "No Kubernetes manifests found.")


def cloud_find_ci_deploy_files(project_path: str) -> str:
    files = collect_files(
        project_path,
        patterns=("*.yml", "*.yaml", "*.json", "*.toml", "*.sh"),
        path_terms=(".github/workflows/", ".gitlab-ci", "bitbucket-pipelines", "deploy", "release", "ci"),
        limit=100,
    )
    return summarize_paths("CI/deploy files:", files, "No CI or deploy pipeline files found.")


def cloud_list_runtime_configs(project_path: str) -> str:
    files = collect_files(
        project_path,
        patterns=("*.env", "*.env.*", "*.yaml", "*.yml", "*.json", "*.toml"),
        name_terms=("env", "config", "settings"),
        path_terms=("config", "deploy", "infrastructure", "infra", "k8s", "helm"),
        limit=100,
    )
    return summarize_paths("Cloud runtime/config files:", files, "No cloud runtime config files found.")


def cloud_find_secrets_references(project_path: str) -> str:
    files = collect_files(
        project_path,
        patterns=("*.tf", "*.yaml", "*.yml", "*.json", "*.py", "*.ts", "*.js", "*.sh"),
        content_terms=("secret", "secretsmanager", "vault", "parameter store", "ssm", "kms"),
        limit=100,
    )
    return summarize_paths("Secret-management references:", files, "No secret-management references found.")


TOOLS = {
    "cloud_list_iac_files": {"fn": cloud_list_iac_files, "description": "List infrastructure-as-code files"},
    "cloud_list_k8s_manifests": {"fn": cloud_list_k8s_manifests, "description": "List Kubernetes manifest files"},
    "cloud_find_ci_deploy_files": {"fn": cloud_find_ci_deploy_files, "description": "Find CI and deploy pipeline files"},
    "cloud_list_runtime_configs": {"fn": cloud_list_runtime_configs, "description": "List cloud runtime config files"},
    "cloud_find_secrets_references": {"fn": cloud_find_secrets_references, "description": "Find secret-management references"},
}
