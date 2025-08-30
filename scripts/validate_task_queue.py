#!/usr/bin/env python3
"""
Validate TASK_QUEUE.yml against ISSUE_DEPENDENCIES.yml

This script validates the generated task queue for:
- Correct version format
- All issue IDs exist in dependencies
- No duplicates across sections
- Blocked issues have unmet dependencies
- Ordering matches declared policy
- Basic data integrity

Exit codes:
- 0: Validation passed
- 1: Validation failed
- 2: File read/parse errors
"""

import argparse
import sys
import yaml
from typing import Dict, List, Any, Set
from collections import Counter


def load_yaml_file(path: str) -> Dict[str, Any]:
    """Load and parse YAML file"""
    try:
        with open(path, 'r', encoding='utf-8') as f:
            return yaml.safe_load(f)
    except FileNotFoundError:
        raise RuntimeError(f"File not found: {path}")
    except yaml.YAMLError as e:
        raise RuntimeError(f"YAML parse error in {path}: {e}")
    except Exception as e:
        raise RuntimeError(f"Failed to read {path}: {e}")


def validate_task_queue_structure(queue_data: Dict[str, Any]) -> List[str]:
    """Validate basic structure of task queue"""
    errors = []
    
    # Check version
    if queue_data.get('version') != 1:
        errors.append(f"Invalid version: expected 1, got {queue_data.get('version')}")
    
    # Check required fields
    required_fields = ['version', 'generated_at', 'ready', 'blocked', 'in_progress', 'done']
    for field in required_fields:
        if field not in queue_data:
            errors.append(f"Missing required field: {field}")
    
    # Check that status sections are lists
    status_sections = ['ready', 'blocked', 'in_progress', 'done']
    for section in status_sections:
        if section in queue_data and not isinstance(queue_data[section], list):
            errors.append(f"Section '{section}' must be a list")
    
    return errors


def extract_all_issue_ids(queue_data: Dict[str, Any]) -> Dict[str, List[int]]:
    """Extract all issue IDs by section"""
    issue_ids_by_section = {}
    status_sections = ['ready', 'blocked', 'in_progress', 'done']
    
    for section in status_sections:
        issue_ids = []
        for item in queue_data.get(section, []):
            if isinstance(item, dict) and 'issue' in item:
                issue_ids.append(item['issue'])
        issue_ids_by_section[section] = issue_ids
    
    return issue_ids_by_section


def validate_issue_existence(issue_ids_by_section: Dict[str, List[int]], 
                            dependencies: Dict[str, Any]) -> List[str]:
    """Validate that all issue IDs exist in dependencies"""
    errors = []
    dep_issues = set(dependencies.get('issues', {}).keys())
    dep_issues_int = {int(id_str) for id_str in dep_issues}
    
    for section, issue_ids in issue_ids_by_section.items():
        for issue_id in issue_ids:
            if issue_id not in dep_issues_int:
                errors.append(f"Issue {issue_id} in section '{section}' not found in dependencies")
    
    return errors


def validate_no_duplicates(issue_ids_by_section: Dict[str, List[int]]) -> List[str]:
    """Validate no duplicate issues across sections"""
    errors = []
    all_issues = []
    
    for section, issue_ids in issue_ids_by_section.items():
        all_issues.extend(issue_ids)
    
    duplicates = [item for item, count in Counter(all_issues).items() if count > 1]
    if duplicates:
        errors.append(f"Duplicate issues found across sections: {duplicates}")
    
    # Check duplicates within sections
    for section, issue_ids in issue_ids_by_section.items():
        section_duplicates = [item for item, count in Counter(issue_ids).items() if count > 1]
        if section_duplicates:
            errors.append(f"Duplicate issues within section '{section}': {section_duplicates}")
    
    return errors


def validate_blocked_dependencies(queue_data: Dict[str, Any], 
                                dependencies: Dict[str, Any]) -> List[str]:
    """Validate that blocked issues truly have unmet dependencies"""
    errors = []
    dep_issues = dependencies.get('issues', {})
    
    # Get all done/completed issues
    done_issues = set()
    for item in queue_data.get('done', []):
        if isinstance(item, dict) and 'issue' in item:
            done_issues.add(item['issue'])
    
    # Check blocked issues
    for item in queue_data.get('blocked', []):
        if not isinstance(item, dict) or 'issue' not in item:
            continue
            
        issue_id = item['issue']
        issue_str = str(issue_id)
        
        if issue_str not in dep_issues:
            continue  # Already caught by existence validation
        
        issue_data = dep_issues[issue_str]
        depends = issue_data.get('depends', [])
        
        if not depends:
            errors.append(f"Issue {issue_id} in blocked section has no dependencies")
            continue
        
        # Check if all dependencies are met
        unmet_deps = [dep for dep in depends if int(dep) not in done_issues]
        if not unmet_deps:
            errors.append(f"Issue {issue_id} in blocked section has all dependencies met: {depends}")
    
    return errors


def validate_ordering_policy(queue_data: Dict[str, Any], 
                           dependencies: Dict[str, Any]) -> List[str]:
    """Validate that ordering follows declared policy"""
    errors = []
    
    # Get generation config if available
    gen_config = queue_data.get('generation_config', {})
    ordering = gen_config.get('ordering', [])
    critical_path_higher_is_prior = gen_config.get('critical_path_higher_is_prior', True)
    
    if not ordering:
        # No ordering policy specified, skip validation
        return errors
    
    dep_issues = dependencies.get('issues', {})
    
    # Check ordering within ready section
    ready_items = queue_data.get('ready', [])
    if len(ready_items) > 1:
        for i in range(len(ready_items) - 1):
            current = ready_items[i]
            next_item = ready_items[i + 1]
            
            current_id = str(current.get('issue', ''))
            next_id = str(next_item.get('issue', ''))
            
            if current_id in dep_issues and next_id in dep_issues:
                current_data = dep_issues[current_id]
                next_data = dep_issues[next_id]
                
                # Multi-criteria ordering validation
                # Check if the order makes sense according to the criteria
                current_keys = []
                next_keys = []
                
                for order_type in ordering:
                    if order_type == 'critical_path_rank':
                        current_rank = current_data.get('critical_path_rank', 0)
                        next_rank = next_data.get('critical_path_rank', 0)
                        # Higher rank = higher priority if critical_path_higher_is_prior
                        current_keys.append(-current_rank if critical_path_higher_is_prior else current_rank)
                        next_keys.append(-next_rank if critical_path_higher_is_prior else next_rank)
                    elif order_type == 'priority':
                        current_priority = current_data.get('meta', {}).get('priority', 'P9')
                        next_priority = next_data.get('meta', {}).get('priority', 'P9')
                        current_p = int(current_priority[1:]) if current_priority.startswith('P') else 9
                        next_p = int(next_priority[1:]) if next_priority.startswith('P') else 9
                        current_keys.append(current_p)
                        next_keys.append(next_p)
                    elif order_type == 'longest_distance':
                        # This would require recalculating distances, skip for now
                        current_keys.append(0)
                        next_keys.append(0)
                
                # Check if current should come before next based on multi-criteria
                if current_keys > next_keys:
                    # Get human-readable values for error message
                    current_priority = current_data.get('meta', {}).get('priority', 'P9')
                    next_priority = next_data.get('meta', {}).get('priority', 'P9')
                    current_rank = current_data.get('critical_path_rank', 0)
                    next_rank = next_data.get('critical_path_rank', 0)
                    
                    errors.append(f"Multi-criteria ordering violation: Issue {current_id} "
                                f"(priority={current_priority}, rank={current_rank}) should come after "
                                f"Issue {next_id} (priority={next_priority}, rank={next_rank}) "
                                f"according to ordering criteria: {ordering}")
    
    return errors


def validate_dependencies_constraint(queue_data: Dict[str, Any], 
                                   dependencies: Dict[str, Any]) -> List[str]:
    """Validate that ready/in_progress issues have all dependencies met"""
    errors = []
    dep_issues = dependencies.get('issues', {})
    
    # Get all done issues
    done_issues = set()
    for item in queue_data.get('done', []):
        if isinstance(item, dict) and 'issue' in item:
            done_issues.add(item['issue'])
    
    # Check ready and in_progress sections
    for section in ['ready', 'in_progress']:
        for item in queue_data.get(section, []):
            if not isinstance(item, dict) or 'issue' not in item:
                continue
                
            issue_id = item['issue']
            issue_str = str(issue_id)
            
            if issue_str not in dep_issues:
                continue  # Already caught by existence validation
            
            issue_data = dep_issues[issue_str]
            depends = issue_data.get('depends', [])
            
            # Check that all dependencies are done
            for dep in depends:
                if int(dep) not in done_issues:
                    errors.append(f"Issue {issue_id} in '{section}' section has unmet dependency: {dep}")
    
    return errors


def validate_task_queue(queue_path: str, dependencies_path: str, verbose: bool = False) -> bool:
    """
    Main validation function.
    Returns True if validation passes, False otherwise.
    """
    try:
        # Load files
        if verbose:
            print(f"Loading task queue from {queue_path}")
        queue_data = load_yaml_file(queue_path)
        
        if verbose:
            print(f"Loading dependencies from {dependencies_path}")
        dependencies = load_yaml_file(dependencies_path)
        
        all_errors = []
        
        # Run validations
        if verbose:
            print("Validating task queue structure...")
        all_errors.extend(validate_task_queue_structure(queue_data))
        
        if verbose:
            print("Extracting issue IDs...")
        issue_ids_by_section = extract_all_issue_ids(queue_data)
        
        if verbose:
            print("Validating issue existence...")
        all_errors.extend(validate_issue_existence(issue_ids_by_section, dependencies))
        
        if verbose:
            print("Validating no duplicates...")
        all_errors.extend(validate_no_duplicates(issue_ids_by_section))
        
        if verbose:
            print("Validating blocked dependencies...")
        all_errors.extend(validate_blocked_dependencies(queue_data, dependencies))
        
        if verbose:
            print("Validating ordering policy...")
        all_errors.extend(validate_ordering_policy(queue_data, dependencies))
        
        if verbose:
            print("Validating dependency constraints...")
        all_errors.extend(validate_dependencies_constraint(queue_data, dependencies))
        
        # Report results
        if all_errors:
            print("VALIDATION FAILED:")
            for error in all_errors:
                print(f"  ERROR: {error}")
            return False
        else:
            if verbose:
                total_issues = sum(len(ids) for ids in issue_ids_by_section.values())
                print(f"VALIDATION PASSED: {total_issues} issues validated")
                for section, ids in issue_ids_by_section.items():
                    print(f"  {section}: {len(ids)} issues")
            else:
                print("VALIDATION PASSED")
            return True
            
    except RuntimeError as e:
        print(f"ERROR: {e}")
        return False
    except Exception as e:
        print(f"UNEXPECTED ERROR: {e}")
        if verbose:
            import traceback
            traceback.print_exc()
        return False


def main():
    parser = argparse.ArgumentParser(description='Validate TASK_QUEUE.yml against ISSUE_DEPENDENCIES.yml')
    parser.add_argument('--queue', default='docs/roadmap/TASK_QUEUE.yml', 
                       help='Path to TASK_QUEUE.yml (default: docs/roadmap/TASK_QUEUE.yml)')
    parser.add_argument('--dependencies', default='docs/roadmap/ISSUE_DEPENDENCIES.yml',
                       help='Path to ISSUE_DEPENDENCIES.yml (default: docs/roadmap/ISSUE_DEPENDENCIES.yml)')
    parser.add_argument('--verbose', action='store_true', help='Verbose output')
    
    args = parser.parse_args()
    
    success = validate_task_queue(args.queue, args.dependencies, args.verbose)
    sys.exit(0 if success else 1)


if __name__ == '__main__':
    main()