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
from typing import Dict, Any, List
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
    """Parse pip-audit JSON output and normalize to standard format."""
    vulnerabilities = []
    suppressed_count = 0

    # Process each vulnerability
    for vuln in data.get('vulnerabilities', []):
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


def is_suppressed(vulnerability: Dict[str, Any]) -> bool:
    """Check if a vulnerability should be suppressed based on suppressions.yaml."""
    try:
        # Find project root by looking for common markers
        current_path = Path(__file__).resolve()
        project_root = None

        # Try to find project root by traversing up until we find a marker
        for parent in current_path.parents:
            if (parent / "pyproject.toml").exists() or (parent / "requirements.txt").exists():
                project_root = parent
                break

        if not project_root:
            # Fallback to going up 3 levels from current file
            project_root = current_path.parent.parent.parent

        suppressions_file = project_root / "security" / "suppressions.yaml"
        if not suppressions_file.exists():
            return False

        with open(suppressions_file, 'r', encoding='utf-8') as f:
            suppressions_data = yaml.safe_load(f) or {}

        suppressions = suppressions_data.get('suppressions', [])

        # Check various suppression criteria
        vuln_id = vulnerability.get('id', '')
        vuln_cve = vulnerability.get('cve', '')
        vuln_package = vulnerability.get('package', '')
        vuln_version = vulnerability.get('version', '')

        for suppression in suppressions:
            # Check by CVE ID
            if suppression.get('id') == vuln_cve:
                return True

            # Check by package@version
            if suppression.get('id') == f"{vuln_package}@{vuln_version}":
                return True

            # Check by package name only
            if suppression.get('id') == vuln_package:
                return True

        return False

    except Exception as e:
        # If suppression check fails, don't suppress (fail-safe)
        print(f"Warning: Suppression check failed: {e}", file=sys.stderr)
        return False


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
