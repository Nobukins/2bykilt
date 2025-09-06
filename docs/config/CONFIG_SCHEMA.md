# Configuration Schema & Multi-Environment Loader (Issue #65)

This document describes the directory-based multi-environment configuration system.

## Directory Layout

```
config/
  base/
    core.yaml
  dev/
    core.yaml
  staging/
    core.yaml
  prod/
    core.yaml
  schema/
    v1.0.yml   # (Optional future validator reference)
```

Each `<env>` directory may contain one or more `*.yml` / `*.yaml` files.  
All files inside `config/base/` are merged first (sorted by name), then files in the selected environment directory override them.

## Merge Strategy

| Type   | Behavior                 |
|--------|--------------------------|
| dict   | Deep recursive merge     |
| list   | Environment file replaces whole list |
| scalar | Environment overrides    |

Type conflicts (base has dict, env has scalar, etc.) produce a warning (code: `type_conflict`).

## Environment Selection

`BYKILT_ENV` chooses the environment. Default: `dev`.  
Aliases: `development -> dev`, `production -> prod`.  
Unknown names fallback to `dev` with a warning (`unknown_env`).

## Secret Masking

Any key whose lowercase name contains: `api_key`, `token`, `secret`, `password`, or `key` is masked to `***`.  
Original value hash (SHA256 first 8 hex chars) is stored in `masked_hashes` under its dotted path (e.g. `secrets.api_key`).

## Effective Config Artifact

A JSON artifact is emitted:

```
artifacts/runs/<YYYYMMDDHHMMSS-cfg>/effective_config.json
```

Example excerpt:

```json
{
  "env": "dev",
  "pseudo_run_id": "20250827121533-cfg",
  "generated_at": "2025-08-27T12:15:33.123456+00:00",
  "files_loaded": [
    "config/base/core.yaml",
    "config/dev/core.yaml"
  ],
  "config": {
    "api_endpoint": "https://api.dev.example",
    "secrets": {
      "api_key": "***"
    }
  },
  "masked_hashes": {
    "secrets.api_key": "a1b2c3d4"
  },
  "warnings": []
}
```

## Diff CLI

Command:

```
bykilt-config diff --from dev --to prod
bykilt-config diff --from dev --to prod --json
```

Output sections: `added`, `removed`, `changed`.  
JSON mode returns a structured object; secrets remain masked.

## Show CLI

```
bykilt-config show --env staging
```

Prints masked merged configuration (without unmasked secrets).

## Warning Codes

| Code             | Meaning |
|------------------|---------|
| unknown_env      | Fallback to `dev` due to invalid env name |
| missing_dir      | Environment directory absent |
| empty_dir        | No YAML files in directory |
| empty_file       | YAML file was empty |
| parse_error      | YAML parsing failure |
| non_mapping_root | Top-level YAML not a mapping |
| type_conflict    | Conflicting types during merge |

## Security Notes

- Secret values never written in plaintext to artifacts.
- Only relative fixed directories under `config/` are scanned (no path traversal).
- Hash fragments (8 chars) are not reversible.

## Future Extensions

- Caching merged config (`.cache/config/<env_hash>`)
- Schema validation (#48 / #63)
- Feature Flags integration (#64) writing `feature_flags_resolved.json`

---
