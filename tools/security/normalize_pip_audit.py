#!/usr/bin/env python3
"""
Normalize pip-audit output to standardized vulnerability report format.

This script processes pip-audit JSON output and converts it to a standardized
vulnerability report format used across the security scanning pipeline.

Usage:
    python tools/security/normalize_pip_audit.py <input_file> <output_file>
    python tools/security/normalize_pip_audit.py - <output_file>  # Read from stdin
"""

import json
import sys
import argparse
from datetime import datetime, timezone
from typing import Dict, Any, List, Optional
from pathlib import Path
import yaml


def normalize_severity(severity: str) -> str:
    """Normalize severity to standard levels."""
    severity_map = {
        'CRITICAL': 'critical',
        'HIGH': 'high',
        'MODERATE': 'medium',
        'MEDIUM': 'medium',
        'LOW': 'low',
        'INFO': 'info',
        'UNKNOWN': 'unknown'
    }
    return severity_map.get(severity.upper(), 'unknown')


def parse_pip_audit_json(data: Dict[str, Any]) -> Dict[str, Any]:
    """Parse pip-audit JSON output and normalize to standard format.

    Supports both legacy/top-level "vulnerabilities" format and the
    "dependencies"-centric format where each dependency lists its "vulns".
    """
    vulnerabilities: List[Dict[str, Any]] = []
    suppressed_count = 0

    # Case 1: Newer/alternate format with top-level vulnerabilities list
    top_level_vulns = data.get('vulnerabilities')
    if isinstance(top_level_vulns, list):
        for vuln in top_level_vulns:
            # Check if vulnerability is suppressed
            if is_suppressed(vuln):
                suppressed_count += 1
                continue

            normalized_vuln = {
                'id': vuln.get('id', ''),
                'package': vuln.get('package', ''),
                'version': vuln.get('version', ''),
                'severity': normalize_severity(vuln.get('severity', 'unknown')),
                'description': vuln.get('description', ''),
                'cve': vuln.get('cve', ''),
                'urls': vuln.get('urls', []),
                'fix_available': vuln.get('fix_available', False),
                'fix_version': vuln.get('fix_version'),
                'source': 'pip-audit'
            }
            vulnerabilities.append(normalized_vuln)

    # Case 2: Dependency-centric format: {"dependencies": [{ name, version, vulns: [...] }]}
    deps = data.get('dependencies')
    if isinstance(deps, list):
        for dep in deps:
            name = dep.get('name', '')
            version = dep.get('version', '')
            for dv in dep.get('vulns', []) or []:
                # Align to the fields used above
                # Safely extract CVE-like alias (first truthy value)
                aliases = dv.get('aliases') or []
                cve_alias = next((a for a in aliases if a), '')
                # Safely extract first available fix version
                fix_versions = dv.get('fix_versions') or []
                first_fix = next((v for v in fix_versions if v), None)
                vuln_obj = {
                    'id': dv.get('id', ''),  # often GHSA-...
                    'package': name,
                    'version': version,
                    # Severity often missing in this format; leave unknown
                    'severity': 'unknown',
                    'description': dv.get('description', ''),
                    # pip-audit may not provide CVE here; use first alias if present
                    'cve': cve_alias or '',
                    'urls': [],
                    'fix_available': bool(fix_versions),
                    'fix_version': first_fix,
                }

                if is_suppressed(vuln_obj):
                    suppressed_count += 1
                    continue

                vuln_obj['source'] = 'pip-audit'
                vulnerabilities.append(vuln_obj)

    # Build normalized report
    report = {
        'metadata': {
            'tool': 'pip-audit',
            'version': data.get('meta', {}).get('version', 'unknown'),
            'generated_at': datetime.now(timezone.utc).isoformat(),
            'total_vulnerabilities': len(vulnerabilities),
            'suppressed_count': suppressed_count,
            'scan_target': 'python-dependencies'
        },
        'vulnerabilities': vulnerabilities,
        'summary': {
            'by_severity': count_by_severity(vulnerabilities),
            'suppressed': suppressed_count,
            'total': len(vulnerabilities) + suppressed_count
        }
    }

    return report


def is_suppressed(vulnerability: Dict[str, Any], project_root: Optional[Path] = None) -> bool:
    """Check if a vulnerability should be suppressed based on suppressions.yaml."""
    try:
        # Use provided project root or find it automatically
        if project_root is None:
            current_path = Path(__file__).resolve()
            project_root = find_project_root(current_path)

        suppressions_file = project_root / "security" / "suppressions.yaml"
        if not suppressions_file.exists():
            return False

        with open(suppressions_file, 'r', encoding='utf-8') as f:
            suppressions_data = yaml.safe_load(f) or {}

        suppressions_raw = suppressions_data.get('suppressions', [])
        # Normalize suppressions to a list of dicts with an 'id' field
        suppressions: List[Dict[str, Any]] = []
        if isinstance(suppressions_raw, dict):
            for key, meta in suppressions_raw.items():
                entry = {'id': key}
                if isinstance(meta, dict):
                    entry.update(meta)
                suppressions.append(entry)
        elif isinstance(suppressions_raw, list):
            suppressions = suppressions_raw  # assume list of dicts
        else:
            suppressions = []

        # Check various suppression criteria
        vuln_id = vulnerability.get('id', '')
        vuln_cve = vulnerability.get('cve', '')
        vuln_package = vulnerability.get('package', '')
        vuln_version = vulnerability.get('version', '')

        for suppression in suppressions:
            sup_id = suppression.get('id')
            # Check by CVE ID
            if sup_id and vuln_cve and sup_id == vuln_cve:
                return True

            # Check by advisory ID (e.g., GHSA-...)
            if sup_id and sup_id == vulnerability.get('id'):
                return True

            # Check by package@version
            if sup_id == f"{vuln_package}@{vuln_version}":
                return True

            # Check by package name only
            if sup_id == vuln_package:
                return True

        return False

    except Exception as e:
        # If suppression check fails, don't suppress (fail-safe)
        print(f"Warning: Suppression check failed: {e}", file=sys.stderr)
        return False


def find_project_root(start_path: Path) -> Path:
    """Find project root by looking for common markers."""
    # Try to find project root by traversing up until we find a marker
    for parent in start_path.parents:
        if (parent / "pyproject.toml").exists() or (parent / "requirements.txt").exists():
            return parent

    # Fallback to going up 3 levels from current file
    return start_path.parent.parent.parent


def count_by_severity(vulnerabilities: List[Dict[str, Any]]) -> Dict[str, int]:
    """Count vulnerabilities by severity level."""
    counts = {
        'critical': 0,
        'high': 0,
        'medium': 0,
        'low': 0,
        'info': 0,
        'unknown': 0
    }

    for vuln in vulnerabilities:
        severity = vuln.get('severity', 'unknown')
        if severity in counts:
            counts[severity] += 1

    return counts


def main():
    parser = argparse.ArgumentParser(
        description='Normalize pip-audit output to standardized format'
    )
    parser.add_argument(
        'input_file',
        help='Input file (use - for stdin)'
    )
    parser.add_argument(
        'output_file',
        help='Output file path'
    )

    args = parser.parse_args()

    try:
        # Read input
        if args.input_file == '-':
            data = json.load(sys.stdin)
        else:
            with open(args.input_file, 'r', encoding='utf-8') as f:
                data = json.load(f)

        # Normalize data
        normalized_report = parse_pip_audit_json(data)

        # Write output
        with open(args.output_file, 'w', encoding='utf-8') as f:
            json.dump(normalized_report, f, indent=2, ensure_ascii=False)

        print(f"Normalized report written to {args.output_file}")
        print(f"Found {normalized_report['metadata']['total_vulnerabilities']} vulnerabilities")
        print(f"Suppressed {normalized_report['summary']['suppressed']} vulnerabilities")

    except Exception as e:
        print(f"Error: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == '__main__':
    main()
