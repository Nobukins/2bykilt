#!/usr/bin/env python3
"""
Generate TASK_QUEUE.yml from ISSUE_DEPENDENCIES.yml with optional GitHub API enrichment.

This script creates a deterministic, machine-readable task queue for issue dependency management.
Features:
- Topological sorting with critical path ranking
- Status classification (done, in_progress, blocked, ready)
- Work-in-progress limits and parallel execution constraints
- GitHub API enrichment for issue/PR states
- Stable YAML output ordering
"""

import argparse
import os
import sys
import yaml
import json
import requests
from datetime import datetime, timezone
from typing import Dict, List, Any, Set, Optional, Tuple
from collections import defaultdict, deque


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


def compute_longest_distances(issues: Dict[str, Any]) -> Dict[str, int]:
    """
    Compute longest distance from leaf nodes using topological sorting.
    Returns dict mapping issue_id -> longest_distance_to_leaf
    """
    # Build dependency graph (who depends on whom)
    dependents = defaultdict(list)  # issue -> list of issues that depend on it
    all_issues = set(issues.keys())
    
    for issue_id, issue_data in issues.items():
        for dep in issue_data.get('depends', []):
            if str(dep) in all_issues:
                dependents[str(dep)].append(issue_id)
    
    # Find leaf nodes (no dependents)
    leaves = [issue_id for issue_id in all_issues if not dependents[issue_id]]
    
    # BFS to compute longest distances
    distances = {}
    queue = deque([(leaf, 0) for leaf in leaves])
    
    while queue:
        current, dist = queue.popleft()
        if current in distances:
            distances[current] = max(distances[current], dist)
        else:
            distances[current] = dist
            
        # Add dependencies of current issue to queue
        issue_data = issues.get(current, {})
        for dep in issue_data.get('depends', []):
            dep_str = str(dep)
            if dep_str in all_issues:
                queue.append((dep_str, dist + 1))
    
    # Ensure all issues have a distance
    for issue_id in all_issues:
        if issue_id not in distances:
            distances[issue_id] = 0
            
    return distances


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


def classify_issue_status(issue_id: str,
                          issue_data: Dict[str, Any],
                          api_data: Dict[str, Any],
                          issues: Dict[str, Any],
                          dependency_api_data: Dict[str, Dict[str, Any]]) -> str:
    """Classify issue status based on:
    - Manual progress.state (highest priority)
    - Own issue API state
    - Primary PR (if any)
    - Closure state of all dependency issues

    Rules:
      * progress.state = 'done' -> done
      * progress.state = 'in_progress' -> in_progress
      * closed -> done
      * active PR (open) -> in_progress
      * has dependencies and ANY dependency not closed -> blocked
      * otherwise -> ready
    """
    # Check manual progress.state first (highest priority)
    progress = issue_data.get('progress', {})
    state = progress.get('state')
    if state == 'done':
        return 'done'
    elif state == 'in_progress':
        return 'in_progress'
    
    # Closed
    if api_data.get('issue_state') == 'closed':
        return 'done'

    # PR present (simplified; treat draft/open similarly as in_progress for now)
    primary_pr = progress.get('primary_pr')
    if primary_pr and api_data.get('primary_pr_state') == 'open':
        return 'in_progress'

    # Dependency gating
    depends = issue_data.get('depends', [])
    if depends:
        for dep_id in depends:
            dep_str = str(dep_id)
            if dep_str in issues:
                dep_api = dependency_api_data.get(dep_str, {})
                # If we lack API data, assume NOT closed (conservative -> stays blocked)
                if dep_api.get('issue_state', 'open') != 'closed':
                    return 'blocked'
    # All dependencies closed (or none) => ready
    return 'ready'


def apply_filters_and_ordering(issues_list: List[Dict[str, Any]], 
                              include_phases: List[str],
                              exclude_risk: List[str],
                              exclude_labels: List[str],
                              ordering: List[str],
                              critical_path_higher_is_prior: bool) -> List[Dict[str, Any]]:
    """
    Apply filters and ordering to issues list.
    """
    filtered = []
    
    for issue in issues_list:
        # Phase filter
        if include_phases:
            phase = issue.get('meta', {}).get('phase', '')
            if phase not in include_phases:
                continue
        
        # Risk filter
        if exclude_risk:
            risk = issue.get('risk')
            if risk in exclude_risk:
                continue
        
        # Label filter (would need GitHub API data)
        # Skip for now since we don't have full API integration
        
        filtered.append(issue)
    
    # Apply ordering
    def sort_key(issue):
        keys = []
        for order_type in ordering:
            if order_type == 'critical_path_rank':
                rank = issue.get('critical_path_rank', 0)
                # Higher rank = higher priority if critical_path_higher_is_prior
                keys.append(-rank if critical_path_higher_is_prior else rank)
            elif order_type == 'priority':
                priority = issue.get('meta', {}).get('priority', 'P9')
                # Convert P0, P1, P2 to numeric for sorting
                priority_num = int(priority[1:]) if priority.startswith('P') else 9
                keys.append(priority_num)
            elif order_type == 'longest_distance':
                keys.append(-issue.get('longest_distance', 0))  # Higher distance first
        return keys
    
    filtered.sort(key=sort_key)
    return filtered


def apply_constraints(issues_by_status: Dict[str, List[Dict[str, Any]]], 
                     wip_limit: int, 
                     max_parallel_per_area: int) -> Tuple[Dict[str, List[Dict[str, Any]]], List[str]]:
    """
    Apply WIP limits and area constraints.
    Returns (updated_issues_by_status, constraint_violations)
    """
    violations = []
    
    # Apply WIP limit to in_progress
    in_progress = issues_by_status.get('in_progress', [])
    if len(in_progress) > wip_limit:
        violations.append(f"WIP limit exceeded: {len(in_progress)} > {wip_limit}")
    
    # Apply area constraints
    area_counts = defaultdict(int)
    for issue in in_progress:
        area = issue.get('meta', {}).get('area', 'unknown')
        area_counts[area] += 1
        if area_counts[area] > max_parallel_per_area:
            violations.append(f"Area {area} parallel limit exceeded: {area_counts[area]} > {max_parallel_per_area}")
    
    return issues_by_status, violations


def generate_task_queue(repo: str, input_path: str, output_path: str,
                       wip_limit: int = 5, max_parallel_per_area: int = 2,
                       include_phases: List[str] = None,
                       exclude_risk: List[str] = None,
                       exclude_labels: List[str] = None,
                       ordering: List[str] = None,
                       critical_path_higher_is_prior: bool = True,
                       priority_order: List[str] = None,
                       no_api: bool = False,
                       verbose: bool = False) -> bool:
    """
    Main generation function.
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
        
        # Compute longest distances
        logger.info("Computing topological distances")
        distances = compute_longest_distances(issues)
        
        # Get GitHub API token if not disabled
        github_token = None if no_api else os.environ.get('GITHUB_TOKEN')
        if not no_api and not github_token:
            logger.warning("GITHUB_TOKEN not found, proceeding without API enrichment")
        
        # Pre-fetch API data for all issues (if token available)
        api_data_map: Dict[str, Dict[str, Any]] = {}
        if github_token and not no_api:
            for issue_id in issues.keys():
                api_data_map[issue_id] = get_github_api_data(repo, issue_id, github_token)
        else:
            # Empty map (validator will treat dependencies as open via classify logic)
            api_data_map = {}

        # Process each issue
        issues_list = []
        for issue_id, issue_data in issues.items():
            # Own API data
            api_data = api_data_map.get(issue_id, {})

            # Classify status using pre-fetched dependency API data
            status = classify_issue_status(issue_id, issue_data, api_data, issues, api_data_map)
            
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
                'longest_distance': distances.get(issue_id, 0),
                'risk': issue_data.get('risk'),
                'meta': issue_data.get('meta', {})
            }
            
            issues_list.append(issue_record)
        
        # Apply filters and ordering
        if not ordering:
            ordering = ['critical_path_rank', 'priority', 'longest_distance']
        
        filtered_issues = apply_filters_and_ordering(
            issues_list, include_phases or [], exclude_risk or [], 
            exclude_labels or [], ordering, critical_path_higher_is_prior
        )
        
        # Group by status
        issues_by_status = defaultdict(list)
        for issue in filtered_issues:
            issues_by_status[issue['status']].append(issue)
        
        # Apply constraints
        issues_by_status, violations = apply_constraints(
            issues_by_status, wip_limit, max_parallel_per_area
        )
        
        # Build output structure
        now = datetime.now(timezone.utc)
        output_data = {
            'version': 1,
            'generated_at': now.isoformat(),
            'roadmap_commit': 'REPLACE_ME',  # Would be filled by workflow
            'dependencies_commit': 'REPLACE_ME',  # Would be filled by workflow
            'generation_config': {
                'repo': repo,
                'wip_limit': wip_limit,
                'max_parallel_per_area': max_parallel_per_area,
                'include_phases': include_phases or [],
                'exclude_risk': exclude_risk or [],
                'ordering': ordering,
                'critical_path_higher_is_prior': critical_path_higher_is_prior
            },
            'diagnostics': {
                'total_issues': len(filtered_issues),
                'constraint_violations': violations,
                'api_enrichment_enabled': not no_api
            },
            'ready': issues_by_status.get('ready', []),
            'blocked': issues_by_status.get('blocked', []),
            'in_progress': issues_by_status.get('in_progress', []),
            'done': issues_by_status.get('done', [])
        }
        
        # Clean up issue records for output (remove internal fields)
        for status_list in [output_data['ready'], output_data['blocked'], 
                           output_data['in_progress'], output_data['done']]:
            for issue in status_list:
                # Remove internal fields not needed in output
                issue.pop('longest_distance', None)
                issue.pop('meta', None)
        
        # Write output with header
        logger.info(f"Writing task queue to {output_path}")
        with open(output_path, 'w', encoding='utf-8') as f:
            f.write("# DO NOT EDIT: This file is auto-generated by scripts/generate_task_queue.py\n")
            f.write("# To update, modify docs/roadmap/ISSUE_DEPENDENCIES.yml and re-run the generator\n")
            f.write("# Last generated: " + now.isoformat() + "\n\n")
            yaml.dump(output_data, f, default_flow_style=False, allow_unicode=True, sort_keys=False)
        
        logger.info(f"Successfully generated task queue with {len(filtered_issues)} issues")
        logger.info(f"Status breakdown: ready={len(issues_by_status.get('ready', []))}, "
                   f"blocked={len(issues_by_status.get('blocked', []))}, "
                   f"in_progress={len(issues_by_status.get('in_progress', []))}, "
                   f"done={len(issues_by_status.get('done', []))}")
        
        if violations:
            logger.warning(f"Constraint violations detected: {violations}")
        
        return True
        
    except Exception as e:
        logger.error(f"Failed to generate task queue: {e}")
        if verbose:
            import traceback
            traceback.print_exc()
        return False


def main():
    parser = argparse.ArgumentParser(description='Generate TASK_QUEUE.yml from ISSUE_DEPENDENCIES.yml')
    parser.add_argument('--repo', required=True, help='GitHub repository (owner/name)')
    parser.add_argument('--input', required=True, help='Path to ISSUE_DEPENDENCIES.yml')
    parser.add_argument('--output', required=True, help='Path to output TASK_QUEUE.yml')
    parser.add_argument('--wip-limit', type=int, default=5, help='Work-in-progress limit')
    parser.add_argument('--max-parallel-per-area', type=int, default=2, help='Max parallel tasks per area')
    parser.add_argument('--include-phases', nargs='*', help='Include only these phases')
    parser.add_argument('--exclude-risk', nargs='*', help='Exclude these risk levels')
    parser.add_argument('--exclude-labels', nargs='*', help='Exclude issues with these labels')
    parser.add_argument('--ordering', nargs='*', default=['critical_path_rank', 'priority', 'longest_distance'],
                       help='Ordering criteria')
    parser.add_argument('--critical-path-higher-is-prior', action='store_true', default=True,
                       help='Higher critical path rank = higher priority')
    parser.add_argument('--priority-order', nargs='*', help='Custom priority ordering')
    parser.add_argument('--no-api', action='store_true', help='Disable GitHub API enrichment')
    parser.add_argument('--verbose', action='store_true', help='Verbose output')
    
    args = parser.parse_args()
    
    success = generate_task_queue(
        repo=args.repo,
        input_path=args.input,
        output_path=args.output,
        wip_limit=args.wip_limit,
        max_parallel_per_area=args.max_parallel_per_area,
        include_phases=args.include_phases,
        exclude_risk=args.exclude_risk,
        exclude_labels=args.exclude_labels,
        ordering=args.ordering,
        critical_path_higher_is_prior=args.critical_path_higher_is_prior,
        priority_order=args.priority_order,
        no_api=args.no_api,
        verbose=args.verbose
    )
    
    sys.exit(0 if success else 1)


if __name__ == '__main__':
    main()