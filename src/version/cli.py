"""
Version management CLI commands.

Provides command-line interface for version management operations.
"""

import argparse

from .version_manager import VersionManager


def _handle_version_show(manager: VersionManager) -> int:
    """Handle version show command."""
    version = manager.get_current_version()
    print(f"2bykilt version: {version}")
    return 0


def _handle_version_set(manager: VersionManager, args: argparse.Namespace) -> int:
    """Handle version set command."""
    version = args.version or args.version_arg
    if not version:
        print("Error: --version argument required for 'set' command")
        return 1
    manager.set_version(version)
    print(f"Version set to {version}")
    return 0


def _handle_version_bump(manager: VersionManager, args: argparse.Namespace) -> int:
    """Handle version bump command."""
    if not args.bump_type:
        print("Error: --type argument required for 'bump' command (major|minor|patch)")
        return 1
    new_version = manager.bump_version(args.bump_type)
    print(f"Version bumped to {new_version}")
    return 0


def _handle_version_tag(manager: VersionManager) -> int:
    """Handle version tag command."""
    tag_name = manager.create_git_tag()
    print(f"Created Git tag: {tag_name}")
    return 0


def _handle_version_tags(manager: VersionManager) -> int:
    """Handle version tags command."""
    tags = manager.get_git_tags()
    if tags:
        print("Version tags:")
        for tag in sorted(tags, reverse=True):
            print(f"  {tag}")
    else:
        print("No version tags found")
    return 0


def version_command(args: argparse.Namespace) -> int:
    """
    Handle version command.

    Subcommands:
        show: Display current version
        set <version>: Set specific version
        bump <major|minor|patch>: Bump version
        tag: Create Git tag for current version
        tags: List all version tags
    """
    manager = VersionManager()

    try:
        handlers = {
            'show': lambda: _handle_version_show(manager),
            'set': lambda: _handle_version_set(manager, args),
            'bump': lambda: _handle_version_bump(manager, args),
            'tag': lambda: _handle_version_tag(manager),
            'tags': lambda: _handle_version_tags(manager),
        }

        handler = handlers.get(args.version_subcommand)
        if handler:
            return handler()

        print(f"Unknown version subcommand: {args.version_subcommand}")
        return 1

    except Exception as e:
        print(f"Error: {e}")
        return 1


def create_version_parser(subparsers) -> argparse.ArgumentParser:
    """Create and return the version subparser."""
    parser = subparsers.add_parser(
        'version',
        help='Manage project version'
    )

    version_subparsers = parser.add_subparsers(
        dest='version_subcommand',
        help='Version management commands'
    )

    # show subcommand
    version_subparsers.add_parser('show', help='Show current version')

    # set subcommand
    set_parser = version_subparsers.add_parser('set', help='Set version')
    set_parser.add_argument('--version', required=False, help='Version string (e.g., 1.2.3)')
    set_parser.add_argument('version_arg', nargs='?', help='Version string')

    # bump subcommand
    bump_parser = version_subparsers.add_parser('bump', help='Bump version')
    bump_parser.add_argument(
        '--type',
        dest='bump_type',
        choices=['major', 'minor', 'patch'],
        help='Type of version bump'
    )

    # tag subcommand
    version_subparsers.add_parser('tag', help='Create Git tag for current version')

    # tags subcommand
    version_subparsers.add_parser('tags', help='List all version tags')

    parser.set_defaults(func=version_command)
    return parser
