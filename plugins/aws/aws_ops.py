from plugins.shared import collect_files, summarize_paths


def aws_list_cloudformation_files(project_path: str) -> str:
    files = collect_files(
        project_path,
        patterns=("*.yaml", "*.yml", "*.json"),
        content_terms=("awstemplateformatversion", "resources:", "type: aws::"),
        path_terms=("cloudformation", "cfn", "sam", "template", "infra", "deploy"),
        limit=100,
    )
    return summarize_paths("AWS CloudFormation/SAM files:", files, "No CloudFormation or SAM files found.")


def aws_find_lambda_files(project_path: str) -> str:
    files = collect_files(
        project_path,
        patterns=("*.py", "*.ts", "*.js", "*.yaml", "*.yml", "*.json"),
        content_terms=("lambda_handler", "def handler(", "exports.handler", "handler:", "runtime:"),
        path_terms=("lambda", "functions", "serverless", "sam"),
        limit=100,
    )
    return summarize_paths("AWS Lambda-related files:", files, "No AWS Lambda-related files found.")


def aws_find_iam_policy_files(project_path: str) -> str:
    files = collect_files(
        project_path,
        patterns=("*.json", "*.yaml", "*.yml", "*.tf"),
        content_terms=("iam", "policy", "assumerolepolicydocument", "action:", "effect:"),
        path_terms=("iam", "policy", "policies", "terraform", "cloudformation", "infra"),
        limit=100,
    )
    return summarize_paths("AWS IAM policy files:", files, "No AWS IAM policy files found.")


def aws_find_terraform_aws_files(project_path: str) -> str:
    files = collect_files(
        project_path,
        patterns=("*.tf", "*.tfvars"),
        content_terms=("provider \"aws\"", "resource \"aws_", "module", "data \"aws_"),
        limit=100,
    )
    return summarize_paths("AWS Terraform files:", files, "No AWS Terraform files found.")


def aws_find_service_configs(project_path: str) -> str:
    files = collect_files(
        project_path,
        patterns=("*.yaml", "*.yml", "*.json", "*.tf", "*.py", "*.ts", "*.js"),
        content_terms=("s3", "dynamodb", "rds", "sqs", "sns", "ecs", "eks", "cloudfront", "apigateway"),
        limit=100,
    )
    return summarize_paths("AWS service config files:", files, "No AWS service config files found.")


TOOLS = {
    "aws_list_cloudformation_files": {"fn": aws_list_cloudformation_files, "description": "List AWS CloudFormation or SAM files"},
    "aws_find_lambda_files": {"fn": aws_find_lambda_files, "description": "Find AWS Lambda-related files"},
    "aws_find_iam_policy_files": {"fn": aws_find_iam_policy_files, "description": "Find AWS IAM policy files"},
    "aws_find_terraform_aws_files": {"fn": aws_find_terraform_aws_files, "description": "Find Terraform files using AWS resources"},
    "aws_find_service_configs": {"fn": aws_find_service_configs, "description": "Find AWS service configuration files"},
}
