# Frappe Plugin

`plugins/frappe` ab built-in hai. Alag `frappe-mcp` se files copy karne ki zarurat nahi hai.

## Kya Milta Hai

- `frappe_list_sites`
- `frappe_bench_restart`
- `frappe_bench_start`
- `frappe_bench_migrate`
- `frappe_bench_backup`
- `frappe_bench_build`
- `frappe_bench_setup_requirements`
- `frappe_api_call`
- `frappe_create_doctype`
- `frappe_execute`
- `frappe_get_logs`

## Minimum `.mcp-config.json`

Host bench setup ke liye:

```json
{
  "framework": "frappe",
  "language": "python",
  "frappe": {
    "bench_id": "erp-bench",
    "site": "wlp.localhost",
    "bench_path": "/home/kk/Desktop/frappe_docker/development/erp-bench",
    "site_port": 8002,
    "api_key": "your_api_key",
    "api_secret": "your_api_secret"
  }
}
```

Docker `docker exec ... bench` setup ke liye:

```json
{
  "framework": "frappe",
  "language": "python",
  "frappe": {
    "bench_id": "erp-bench",
    "site": "wlp.localhost",
    "bench_path": "/home/kk/Desktop/frappe_docker/development/erp-bench",
    "bench_cmd": "docker exec -w /workspace/development/erp-bench devcontainer_frappe_1 bench",
    "node_version": "24",
    "site_port": 8002,
    "api_key": "your_api_key",
    "api_secret": "your_api_secret"
  }
}
```

## Multiple Sites

```json
{
  "framework": "frappe",
  "language": "python",
  "frappe": {
    "bench_id": "erp-bench",
    "bench_path": "/home/kk/Desktop/frappe_docker/development/erp-bench",
    "bench_cmd": "docker exec -w /workspace/development/erp-bench devcontainer_frappe_1 bench",
    "site": "wlp.localhost",
    "site_credentials": {
      "wlp.localhost": {
        "api_key": "key1",
        "api_secret": "secret1",
        "port": 8002
      },
      "test.localhost:8001": {
        "api_key": "key2",
        "api_secret": "secret2",
        "port": 8001
      }
    }
  }
}
```

`site` aur `bench_id` tool call me override bhi kar sakte ho.

## Notes

- `bench_path` agar project already bench ke andar hai to auto-detect bhi ho sakta hai.
- Docker setup me `bench_cmd` dena best hai.
- `frappe_api_call` ke liye `api_key`, `api_secret`, aur port required hain.
- `frappe_execute` warn-level expressions ke liye `confirmed=true` maangta hai.
