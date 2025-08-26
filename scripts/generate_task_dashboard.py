#!/usr/bin/env python3
"""
Generate TASK_DASHBOARD.md from ISSUE_DEPENDENCIES.yml with optional GitHub API enrichment.

This script creates a human-readable task dashboard complementing the machine-readable TASK_QUEUE.yml.
Features:
- Markdown tables for different issue categories
- Ready queue with prioritization and notes
- Blocked issues with dependency information
- In-progress tracking
- Large issue split candidates
- KPI snapshot section
"""

import argparse
import os
import sys
import yaml
import json
import requests
from datetime import datetime, timezone
from typing import Dict, List, Any, Set, Optional
from collections import defaultdict


def setup_logging(verbose: bool = False):
    """Setup basic logging"""
    import logging
    level = logging.DEBUG if verbose else logging.INFO
    logging.basicConfig(level=level, format='%(levelname)s: %(message)s')
    return logging.getLogger(__name__)


def load_dependencies(input_path: str) -> Dict[str, Any]:
    """Load and parse ISSUE_DEPENDENCIES.yml"""
    try:
        with open(input_path, 'r', encoding='utf-8') as f:
            data = yaml.safe_load(f)
        return data
    except Exception as e:
        raise RuntimeError(f"Failed to load dependencies file {input_path}: {e}")


def get_github_api_data(repo: str, issue_id: str, token: Optional[str]) -> Dict[str, Any]:
    """
    Fetch issue and PR data from GitHub API.
    Returns dict with issue state, labels, and primary_pr info.
    """
    if not token:
        return {}
    
    try:
        headers = {
            'Authorization': f'token {token}',
            'Accept': 'application/vnd.github.v3+json'
        }
        
        # Get issue data
        issue_url = f'https://api.github.com/repos/{repo}/issues/{issue_id}'
        issue_resp = requests.get(issue_url, headers=headers, timeout=10)
        
        result = {}
        if issue_resp.status_code == 200:
            issue_data = issue_resp.json()
            result['issue_state'] = issue_data.get('state', 'open')
            result['labels'] = [label['name'] for label in issue_data.get('labels', [])]
        
        return result
        
    except Exception as e:
        # Don't fail on API errors, just return empty data
        return {}


def classify_issue_status(issue_id: str, issue_data: Dict[str, Any], 
                         api_data: Dict[str, Any], issues: Dict[str, Any]) -> str:
    """
    Classify issue status based on dependencies and API data.
    Returns: 'done', 'in_progress', 'blocked', 'ready'
    """
    # Check if issue is closed/done
    if api_data.get('issue_state') == 'closed':
        return 'done'
    
    # Check if issue has a primary PR
    primary_pr = issue_data.get('progress', {}).get('primary_pr')
    if primary_pr:
        return 'in_progress'
    
    # Check dependencies
    depends = issue_data.get('depends', [])
    if depends:
        for dep_id in depends:
            dep_str = str(dep_id)
            if dep_str in issues:
                # For dashboard, we'll assume dependencies are not done unless we have API data
                return 'blocked'
    
    return 'ready'


def generate_ready_queue_table(ready_issues: List[Dict[str, Any]]) -> str:
    """Generate the ready queue markdown table"""
    if not ready_issues:
        return "| Rank | Issue | Priority | Size | Wave | Title | Notes |\n|------|-------|----------|------|------|-------|-------|\n| - | - | - | - | - | No ready issues | - |\n"
    
    table = "| Rank | Issue | Priority | Size | Wave | Title | Notes |\n"
    table += "|------|-------|----------|------|------|-------|-------|\n"
    
    for i, issue in enumerate(ready_issues[:10], 1):  # Limit to top 10
        issue_num = issue['issue']
        title = issue['title'][:50] + "..." if len(issue['title']) > 50 else issue['title']
        priority = issue.get('priority', 'P9')
        size = issue.get('size', 'M')
        area = issue.get('area', 'unknown')
        wave = f"{area[0].upper()}{i}" if area else f"W{i}"  # Generate wave from area
        
        # Generate notes based on dependencies
        notes = "dependencies satisfied" if not issue.get('depends_on') else "independent"
        
        table += f"| {i} | #{issue_num} | {priority} | {size} | {wave} | {title} | {notes} |\n"
    
    if len(ready_issues) > 10:
        table += f"| ... | ... | ... | ... | ... | +{len(ready_issues) - 10} more issues | see queue |\n"
    
    return table


def generate_blocked_table(blocked_issues: List[Dict[str, Any]]) -> str:
    """Generate the blocked issues markdown table"""
    if not blocked_issues:
        return "| Issue | Blocking |\n|-------|----------|\n| - | No blocked issues |\n"
    
    table = "| Issue | Blocking |\n"
    table += "|-------|----------|\n"
    
    for issue in blocked_issues:
        issue_num = issue['issue']
        depends_on = issue.get('depends_on', [])
        blocking_str = ",".join([f"#{dep}" for dep in depends_on]) if depends_on else "unknown"
        table += f"| #{issue_num} | {blocking_str} |\n"
    
    return table


def generate_in_progress_table(in_progress_issues: List[Dict[str, Any]]) -> str:
    """Generate the in-progress issues markdown table"""
    if not in_progress_issues:
        return "| Issue | Title | Area | Progress |\n|-------|-------|------|----------|\n| - | No issues in progress | - | - |\n"
    
    table = "| Issue | Title | Area | Progress |\n"
    table += "|-------|-------|------|----------|\n"
    
    for issue in in_progress_issues:
        issue_num = issue['issue']
        title = issue['title'][:40] + "..." if len(issue['title']) > 40 else issue['title']
        area = issue.get('area', 'unknown')
        # Progress would come from PR data in real implementation
        progress = "PR open"
        table += f"| #{issue_num} | {title} | {area} | {progress} |\n"
    
    return table


def generate_large_split_candidates_table(issues: List[Dict[str, Any]]) -> str:
    """Generate table of large issues that might need splitting"""
    large_issues = [issue for issue in issues if issue.get('size') == 'L']
    
    if not large_issues:
        return "| Issue | Current | Proposed Split |\n|-------|---------|----------------|\n| - | No large issues | - |\n"
    
    table = "| Issue | Current | Proposed Split |\n"
    table += "|-------|---------|----------------|\n"
    
    for issue in large_issues[:5]:  # Limit to 5 candidates
        issue_num = issue['issue']
        current_size = issue.get('size', 'L')
        # Generate suggested split based on issue number for demo
        proposed = f"{issue_num}a/{issue_num}b"
        table += f"| #{issue_num} | {current_size} | {proposed} |\n"
    
    return table


def generate_kpi_snapshot(ready_count: int, blocked_count: int, in_progress_count: int, done_count: int) -> str:
    """Generate KPI snapshot section"""
    p0_remaining = ready_count + blocked_count + in_progress_count  # Simplified calculation
    blocked_over_2d = 0  # Would require date tracking in real implementation
    doc_sync_lag = 0     # Would require comparison with actual docs
    
    kpi = "## 5. KPI Snapshot (Manual for now)\n\n"
    kpi += f"- P0 Remaining: {p0_remaining}\n"
    kpi += f"- Blocked >2d: {blocked_over_2d}\n"
    kpi += f"- Doc Sync Lag: {doc_sync_lag}\n"
    
    return kpi


def generate_task_dashboard(repo: str, input_path: str, output_path: str,
                          no_api: bool = False, verbose: bool = False) -> bool:
    """
    Main generation function for task dashboard.
    Returns True if successful, False otherwise.
    """
    logger = setup_logging(verbose)
    
    try:
        # Load dependencies
        logger.info(f"Loading dependencies from {input_path}")
        deps_data = load_dependencies(input_path)
        issues = deps_data.get('issues', {})
        
        if not issues:
            logger.error("No issues found in dependencies file")
            return False
        
        # Get GitHub API token if not disabled
        github_token = None if no_api else os.environ.get('GITHUB_TOKEN')
        if not no_api and not github_token:
            logger.warning("GITHUB_TOKEN not found, proceeding without API enrichment")
        
        # Process each issue and classify by status
        issues_by_status = {
            'ready': [],
            'blocked': [],
            'in_progress': [],
            'done': []
        }
        
        for issue_id, issue_data in issues.items():
            # Get API data if available
            api_data = {} if no_api else get_github_api_data(repo, issue_id, github_token)
            
            # Classify status
            status = classify_issue_status(issue_id, issue_data, api_data, issues)
            
            # Build issue record
            issue_record = {
                'issue': int(issue_id),
                'title': issue_data.get('title', ''),
                'priority': issue_data.get('meta', {}).get('priority', 'P9'),
                'size': issue_data.get('meta', {}).get('size', 'M'),
                'area': issue_data.get('meta', {}).get('area', 'unknown'),
                'phase': issue_data.get('meta', {}).get('phase', ''),
                'status': status,
                'depends_on': issue_data.get('depends', []),
                'critical_path_rank': issue_data.get('critical_path_rank', 0),
                'risk': issue_data.get('risk')
            }
            
            issues_by_status[status].append(issue_record)
        
        # Sort each status group
        for status in issues_by_status:
            issues_by_status[status].sort(key=lambda x: (
                -x.get('critical_path_rank', 0),  # Higher rank first
                int(x.get('priority', 'P9')[1:]) if x.get('priority', 'P9').startswith('P') else 9,  # P0 before P1
                x.get('issue')  # Issue number as tiebreaker
            ))
        
        # Generate markdown content
        now = datetime.now(timezone.utc)
        
        content = "# Task Dashboard\n\n"
        content += f"最終更新: {now.strftime('%Y-%m-%d')}\n"
        content += "Roadmap Commit: (to be set)\n"
        content += "Dependencies Commit: (to be set)\n\n"
        content += "⚠️ **DO NOT EDIT**: This file is auto-generated by scripts/generate_task_dashboard.py\n\n"
        
        # 1. Ready Queue
        content += "## 1. READY QUEUE\n\n"
        content += generate_ready_queue_table(issues_by_status['ready'])
        content += "\n(後続はスクリプトにより自動拡張)\n\n"
        
        # 2. Blocked
        content += "## 2. BLOCKED\n\n"
        content += generate_blocked_table(issues_by_status['blocked'])
        content += "\n"
        
        # 3. In Progress  
        content += "## 3. IN PROGRESS\n\n"
        content += generate_in_progress_table(issues_by_status['in_progress'])
        content += "\n"
        
        # 4. Large Split Candidates
        content += "## 4. LARGE Split Candidates\n\n"
        all_issues = []
        for status_issues in issues_by_status.values():
            all_issues.extend(status_issues)
        content += generate_large_split_candidates_table(all_issues)
        content += "\n"
        
        # 5. KPI Snapshot
        content += generate_kpi_snapshot(
            len(issues_by_status['ready']),
            len(issues_by_status['blocked']),
            len(issues_by_status['in_progress']),
            len(issues_by_status['done'])
        )
        content += "\n(EOF)\n"
        
        # Write output
        logger.info(f"Writing task dashboard to {output_path}")
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write(content)
        
        logger.info(f"Successfully generated task dashboard")
        logger.info(f"Status breakdown: ready={len(issues_by_status['ready'])}, "
                   f"blocked={len(issues_by_status['blocked'])}, "
                   f"in_progress={len(issues_by_status['in_progress'])}, "
                   f"done={len(issues_by_status['done'])}")
        
        return True
        
    except Exception as e:
        logger.error(f"Failed to generate task dashboard: {e}")
        if verbose:
            import traceback
            traceback.print_exc()
        return False


def main():
    parser = argparse.ArgumentParser(description='Generate TASK_DASHBOARD.md from ISSUE_DEPENDENCIES.yml')
    parser.add_argument('--repo', required=True, help='GitHub repository (owner/name)')
    parser.add_argument('--input', required=True, help='Path to ISSUE_DEPENDENCIES.yml')
    parser.add_argument('--output', required=True, help='Path to output TASK_DASHBOARD.md')
    parser.add_argument('--no-api', action='store_true', help='Disable GitHub API enrichment')
    parser.add_argument('--verbose', action='store_true', help='Verbose output')
    
    args = parser.parse_args()
    
    success = generate_task_dashboard(
        repo=args.repo,
        input_path=args.input,
        output_path=args.output,
        no_api=args.no_api,
        verbose=args.verbose
    )
    
    sys.exit(0 if success else 1)


if __name__ == '__main__':
    main()