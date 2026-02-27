#!/usr/bin/env python3
"""
Setup validation script for hashicorp.terraform Ansible collection.

This script verifies that the development environment is properly configured
for developing and testing the collection.
"""

import subprocess
import sys
from pathlib import Path
from typing import List, Tuple


class Colors:
    """ANSI color codes for terminal output."""
    GREEN = '\033[92m'
    RED = '\033[91m'
    YELLOW = '\033[93m'
    BLUE = '\033[94m'
    RESET = '\033[0m'
    BOLD = '\033[1m'


def print_header(text: str) -> None:
    """Print a formatted header."""
    print(f"\n{Colors.BOLD}{Colors.BLUE}{'=' * 60}{Colors.RESET}")
    print(f"{Colors.BOLD}{Colors.BLUE}{text:^60}{Colors.RESET}")
    print(f"{Colors.BOLD}{Colors.BLUE}{'=' * 60}{Colors.RESET}\n")


def print_success(text: str) -> None:
    """Print success message."""
    print(f"{Colors.GREEN}✓{Colors.RESET} {text}")


def print_error(text: str) -> None:
    """Print error message."""
    print(f"{Colors.RED}✗{Colors.RESET} {text}")


def print_warning(text: str) -> None:
    """Print warning message."""
    print(f"{Colors.YELLOW}⚠{Colors.RESET} {text}")


def run_command(cmd: List[str], description: str = "") -> Tuple[bool, str]:
    """
    Run a shell command and return success status and output.
    
    Args:
        cmd: Command as list of strings
        description: Description of what the command checks
        
    Returns:
        Tuple of (success, output)
    """
    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=10)
        return result.returncode == 0, result.stdout + result.stderr
    except Exception as e:
        return False, str(e)


def check_python_version() -> bool:
    """Check Python version (3.9+)."""
    print_header("Python Version Check")
    
    version_info = sys.version_info
    version_str = f"{version_info.major}.{version_info.minor}.{version_info.micro}"
    
    print(f"Python version: {version_str}")
    
    if version_info.major < 3 or (version_info.major == 3 and version_info.minor < 9):
        print_error(f"Python 3.9+ required (found {version_str})")
        return False
    
    print_success(f"Python {version_str} is supported")
    return True


def check_git() -> bool:
    """Check if git is installed."""
    print_header("Git Installation Check")
    
    success, output = run_command(['git', '--version'])
    
    if not success:
        print_error("Git is not installed or not in PATH")
        return False
    
    git_version = output.strip()
    print(f"Found: {git_version}")
    print_success("Git is installed")
    return True


def check_virtual_environment() -> bool:
    """Check if running in a virtual environment."""
    print_header("Virtual Environment Check")
    
    in_venv = hasattr(sys, 'real_prefix') or (
        hasattr(sys, 'base_prefix') and sys.base_prefix != sys.prefix
    )
    
    if not in_venv:
        print_warning("Not running in a virtual environment")
        print("  Run: python3 -m venv .venv && source .venv/bin/activate")
        return False
    
    print(f"Virtual environment: {sys.prefix}")
    print_success("Running in virtual environment")
    return True


def check_ansible() -> bool:
    """Check if Ansible Core is installed."""
    print_header("Ansible Core Check")
    
    success, output = run_command(['ansible', '--version'])
    
    if not success:
        print_error("Ansible is not installed")
        print("  Run: pip install -r requirements.txt")
        return False
    
    # Extract version line
    version_line = output.split('\n')[0] if output else "unknown"
    print(f"Found: {version_line}")
    
    print_success("Ansible Core is installed")
    return True


def check_python_packages() -> bool:
    """Check if required Python packages are installed."""
    print_header("Python Packages Check")
    
    required_packages = {
        'ansible': 'ansible-core',
        'pytfe': 'pytfe',
        'requests': 'requests',
        'pydantic': 'pydantic',
        'pytest': 'pytest (test)',
        'pytest_mock': 'pytest-mock (test)',
        'black': 'black (dev)',
        'isort': 'isort (dev)',
        'flake8': 'flake8 (dev)',
    }
    
    all_installed = True
    
    for import_name, package_name in required_packages.items():
        try:
            __import__(import_name)
            print_success(f"{package_name} is installed")
        except ImportError:
            print_error(f"{package_name} is not installed")
            all_installed = False
    
    if not all_installed:
        print("\n  Run: pip install -r requirements.txt -r test-requirements.txt")
    
    return all_installed


def check_collection_structure() -> bool:
    """Check if the collection directory structure exists."""
    print_header("Collection Structure Check")
    
    required_dirs = [
        'plugins/modules',
        'plugins/module_utils',
        'plugins/module_utils/models',
        'plugins/doc_fragments',
        'plugins/lookup',
        'plugins/action',
        'plugins/filter',
        'tests/unit/plugins/modules',
        'tests/unit/plugins/module_utils',
        'tests/integration/targets',
        'changelogs/fragments',
        'docs',
        'meta',
    ]
    
    all_present = True
    
    for directory in required_dirs:
        path = Path(directory)
        if path.exists() and path.is_dir():
            print_success(f"Directory exists: {directory}/")
        else:
            print_error(f"Directory missing: {directory}/")
            all_present = False
    
    return all_present


def check_collection_files() -> bool:
    """Check if required files exist."""
    print_header("Collection Files Check")
    
    required_files = {
        'galaxy.yml': 'Collection metadata',
        'README.md': 'Collection documentation',
        'LICENSE': 'License file',
        'requirements.txt': 'Production dependencies',
        'test-requirements.txt': 'Test dependencies',
        'pyproject.toml': 'Tool configuration',
        'Makefile': 'Development commands',
        'DEVELOPMENT.md': 'Development guide',
    }
    
    all_present = True
    
    for filename, description in required_files.items():
        path = Path(filename)
        if path.exists():
            print_success(f"{filename}: {description}")
        else:
            print_error(f"Missing: {filename} ({description})")
            all_present = False
    
    return all_present


def check_collection_installation() -> bool:
    """Check if collection is installed."""
    print_header("Collection Installation Check")
    
    success, output = run_command(
        ['ansible-galaxy', 'collection', 'list', '|', 'grep', 'hashicorp.terraform'],
        shell=True
    )
    
    # More reliable check
    success, output = run_command(['ansible-galaxy', 'collection', 'list'])
    
    if 'hashicorp.terraform' in output:
        print_success("Collection is installed locally")
        return True
    else:
        print_warning("Collection is not installed locally")
        print("  Run: ansible-galaxy collection install . --force")
        return False


def check_module_files() -> bool:
    """Check if core module files exist."""
    print_header("Module Files Check")
    
    modules_dir = Path('plugins/modules')
    required_modules = [
        'workspace.py',
        'workspace_info.py',
        'run.py',
        'run_info.py',
        'project.py',
        'project_info.py',
    ]
    
    all_present = True
    
    if not modules_dir.exists():
        print_error(f"Modules directory missing: {modules_dir}/")
        return False
    
    for module in required_modules:
        path = modules_dir / module
        if path.exists():
            print_success(f"Module exists: {module}")
        else:
            print_warning(f"Module missing: {module}")
            all_present = False
    
    return all_present


def check_test_files() -> bool:
    """Check if test files exist."""
    print_header("Test Files Check")
    
    tests_unit_dir = Path('tests/unit/plugins/modules')
    tests_int_dir = Path('tests/integration/targets')
    
    if tests_unit_dir.exists():
        test_files = list(tests_unit_dir.glob('test_*.py'))
        if test_files:
            print_success(f"Found {len(test_files)} unit test file(s)")
        else:
            print_warning("No unit test files found")
    else:
        print_error(f"Unit tests directory missing: {tests_unit_dir}/")
        return False
    
    if tests_int_dir.exists():
        target_dirs = [d for d in tests_int_dir.iterdir() if d.is_dir()]
        if target_dirs:
            print_success(f"Found {len(target_dirs)} integration target(s)")
            for target in target_dirs[:5]:  # Show first 5
                print(f"  - {target.name}")
        else:
            print_warning("No integration targets found")
    else:
        print_error(f"Integration tests directory missing: {tests_int_dir}/")
        return False
    
    return True


def main() -> int:
    """Run all checks and report results."""
    print(f"{Colors.BOLD}{Colors.BLUE}")
    print("╔" + "═" * 58 + "╗")
    print("║" + "  Hashicorp Terraform Collection - Setup Validator  ".center(58) + "║")
    print("╚" + "═" * 58 + "╝")
    print(Colors.RESET)
    
    checks = [
        ("Python Version", check_python_version),
        ("Git Installation", check_git),
        ("Virtual Environment", check_virtual_environment),
        ("Python Packages", check_python_packages),
        ("Collection Structure", check_collection_structure),
        ("Collection Files", check_collection_files),
        ("Module Files", check_module_files),
        ("Test Files", check_test_files),
        ("Ansible Core", check_ansible),
        ("Collection Installation", check_collection_installation),
    ]
    
    results = []
    
    for check_name, check_func in checks:
        try:
            passed = check_func()
            results.append((check_name, passed))
        except Exception as e:
            print_error(f"Error running check: {e}")
            results.append((check_name, False))
    
    # Summary
    print_header("Summary")
    
    passed = sum(1 for _, result in results if result)
    total = len(results)
    
    for check_name, result in results:
        status = f"{Colors.GREEN}PASS{Colors.RESET}" if result else f"{Colors.RED}FAIL{Colors.RESET}"
        print(f"  [{status}] {check_name}")
    
    print(f"\n{Colors.BOLD}Result: {passed}/{total} checks passed{Colors.RESET}\n")
    
    if passed == total:
        print(f"{Colors.GREEN}{Colors.BOLD}✓ Environment is ready for development!{Colors.RESET}\n")
        print("Next steps:")
        print("  1. Run unit tests: make test-unit")
        print("  2. Check code quality: make lint_all")
        print("  3. View development guide: DEVELOPMENT.md\n")
        return 0
    else:
        print(f"{Colors.YELLOW}{Colors.BOLD}⚠ Please fix the issues above{Colors.RESET}\n")
        print("For help, see DEVELOPMENT.md or run specific checks above\n")
        return 1


if __name__ == '__main__':
    sys.exit(main())
