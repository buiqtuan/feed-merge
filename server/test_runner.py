#!/usr/bin/env python3
"""
Test Runner for FeedMerge API

Usage:
    python test_runner.py                    # Run all tests
    python test_runner.py auth               # Run auth tests only
    python test_runner.py --coverage         # Run with coverage
    python test_runner.py --verbose          # Run with verbose output
"""

import sys
import subprocess
import argparse
import os


def run_command(cmd, description=""):
    """Run a command and return the exit code"""
    if description:
        print(f"\n🚀 {description}")
    print(f"Running: {' '.join(cmd)}")
    
    result = subprocess.run(cmd, capture_output=False)
    return result.returncode


def main():
    parser = argparse.ArgumentParser(description="Run FeedMerge API tests")
    parser.add_argument("suite", nargs="?", choices=["auth", "users", "posts", "all"], 
                       default="all", help="Test suite to run")
    parser.add_argument("--coverage", action="store_true", help="Run with coverage")
    parser.add_argument("--verbose", action="store_true", help="Verbose output")
    parser.add_argument("--fast", action="store_true", help="Skip slow tests")
    parser.add_argument("--markers", help="Run tests with specific markers")
    
    args = parser.parse_args()
    
    # Base pytest command
    cmd = ["python", "-m", "pytest"]
    
    # Add test path based on suite
    if args.suite == "auth":
        cmd.append("tests/api/test_auth.py")
        description = "Running Authentication API tests"
    elif args.suite == "users":
        cmd.append("tests/api/test_users.py")
        description = "Running Users API tests"
    elif args.suite == "posts":
        cmd.append("tests/api/test_posts.py")
        description = "Running Posts API tests"
    else:
        cmd.append("tests/")
        description = "Running all tests"
    
    # Add optional flags
    if args.coverage:
        cmd.extend(["--cov=app", "--cov-report=html", "--cov-report=term-missing"])
    
    if args.verbose:
        cmd.append("-vv")
    
    if args.fast:
        cmd.extend(["-m", "not slow"])
    
    if args.markers:
        cmd.extend(["-m", args.markers])
    
    # Set environment for testing
    os.environ["TESTING"] = "1"
    
    # Run the tests
    exit_code = run_command(cmd, description)
    
    if exit_code == 0:
        print("\n✅ All tests passed!")
        if args.coverage:
            print("📊 Coverage report generated in htmlcov/")
    else:
        print(f"\n❌ Tests failed with exit code {exit_code}")
    
    return exit_code


if __name__ == "__main__":
    sys.exit(main()) 