from __future__ import annotations

import subprocess
import sys

from modules.registry import discover_and_load, get_registry


def cmd_list() -> None:
    """List all installed OpenForge plugin modules."""
    discover_and_load()
    registry = get_registry()
    if not registry:
        print("No plugin modules installed.")
        print("Install a plugin: openforge-plugins install <package>")
        return
    print(f"{'Module':<20} {'Pattern':<30} Description")
    print("-" * 70)
    for name, cls in sorted(registry.items()):
        pattern = getattr(cls, "match_pattern", "")[:28]
        desc = getattr(cls, "description", "")[:40]
        print(f"  {name:<18} {pattern:<30} {desc}")


def cmd_install(package: str) -> None:
    """Install a plugin package and discover its modules."""
    print(f"Installing {package}...")
    result = subprocess.run(["uv", "add", package], check=False)
    if result.returncode != 0:
        print(f"✗ Failed to install {package}", file=sys.stderr)
        sys.exit(1)
    print(f"✓ Installed {package}")
    discover_and_load()
    registered = list(get_registry().keys())
    if registered:
        print(f"  Modules available: {', '.join(registered)}")


def cmd_remove(package: str) -> None:
    """Remove a plugin package."""
    print(f"Removing {package}...")
    result = subprocess.run(["uv", "remove", package], check=False)
    if result.returncode != 0:
        print(f"✗ Failed to remove {package}", file=sys.stderr)
        sys.exit(1)
    print(f"✓ Removed {package}")


def main(args: list[str] | None = None) -> None:
    args = args if args is not None else sys.argv[1:]
    if not args or args[0] == "list":
        cmd_list()
    elif args[0] == "install" and len(args) > 1:
        cmd_install(args[1])
    elif args[0] == "remove" and len(args) > 1:
        cmd_remove(args[1])
    else:
        print("Usage: openforge-plugins [list | install <pkg> | remove <pkg>]")
        sys.exit(1)


if __name__ == "__main__":
    main()
