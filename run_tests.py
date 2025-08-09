#!/usr/bin/env python3
"""
Test runner for crypto prop firm trading system

Usage:
    python run_tests.py                    # Run all tests
    python run_tests.py unit              # Run unit tests only
    python run_tests.py integration       # Run integration tests only
    python run_tests.py e2e               # Run end-to-end tests only
    python run_tests.py stress            # Run stress tests only
    python run_tests.py --fast            # Skip slow tests
    python run_tests.py --coverage        # Run with coverage report
    python run_tests.py --parallel        # Run tests in parallel
"""

import sys
import os
import subprocess
import argparse
import time
from pathlib import Path

# Add project root to Python path
project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

def run_command(cmd, capture_output=False):
    """Run command and return result"""
    print(f"Running: {' '.join(cmd)}")
    try:
        if capture_output:
            result = subprocess.run(cmd, capture_output=True, text=True, cwd=project_root)
            return result.returncode, result.stdout, result.stderr
        else:
            return subprocess.run(cmd, cwd=project_root).returncode
    except Exception as e:
        print(f"Error running command: {e}")
        return 1

def check_dependencies():
    """Check that required test dependencies are installed"""
    try:
        import pytest
        import pytest_cov
        import pytest_asyncio
        print("✓ Test dependencies found")
        return True
    except ImportError as e:
        print(f"✗ Missing test dependencies: {e}")
        print("Install test dependencies with: pip install -r tests/requirements-test.txt")
        return False

def setup_test_environment():
    """Setup test environment variables"""
    test_env = {
        'TESTING': 'true',
        'DATABASE_URL': ':memory:',  # Use in-memory database for tests
        'TELEGRAM_BOT_TOKEN': 'test_token',
        'TELEGRAM_CHAT_ID': '12345',
        'MT5_LOGIN': '12345',
        'MT5_PASSWORD': 'test_password',
        'MT5_SERVER': 'test_server',
    }
    
    for key, value in test_env.items():
        os.environ[key] = value
    
    print("✓ Test environment configured")

def run_unit_tests(args):
    """Run unit tests"""
    cmd = ['python', '-m', 'pytest', 'tests/unit/', '-m', 'unit']
    
    if args.verbose:
        cmd.extend(['-v', '-s'])
    if args.fast:
        cmd.extend(['-m', 'not slow'])
    if args.coverage:
        cmd.extend(['--cov=./', '--cov-report=html', '--cov-report=term'])
    if args.parallel:
        cmd.extend(['-n', 'auto'])
    
    return run_command(cmd)

def run_integration_tests(args):
    """Run integration tests"""
    cmd = ['python', '-m', 'pytest', 'tests/integration/', '-m', 'integration']
    
    if args.verbose:
        cmd.extend(['-v', '-s'])
    if args.fast:
        cmd.extend(['-m', 'not slow'])
    if args.coverage:
        cmd.extend(['--cov=./', '--cov-report=html', '--cov-report=term'])
    if args.parallel:
        cmd.extend(['-n', 'auto'])
    
    return run_command(cmd)

def run_e2e_tests(args):
    """Run end-to-end tests"""
    cmd = ['python', '-m', 'pytest', 'tests/e2e/', '-m', 'e2e']
    
    if args.verbose:
        cmd.extend(['-v', '-s'])
    if args.fast:
        cmd.extend(['-m', 'not slow'])
    if args.coverage:
        cmd.extend(['--cov=./', '--cov-report=html', '--cov-report=term'])
    # E2E tests typically run sequentially for reliability
    
    return run_command(cmd)

def run_stress_tests(args):
    """Run stress tests"""
    cmd = ['python', '-m', 'pytest', 'tests/e2e/test_stress_scenarios.py', '-m', 'stress']
    
    if args.verbose:
        cmd.extend(['-v', '-s'])
    # Stress tests are inherently slow, don't skip them with --fast
    if args.coverage:
        cmd.extend(['--cov=./', '--cov-report=html', '--cov-report=term'])
    
    return run_command(cmd)

def run_all_tests(args):
    """Run all tests"""
    cmd = ['python', '-m', 'pytest', 'tests/']
    
    if args.verbose:
        cmd.extend(['-v', '-s'])
    if args.fast:
        cmd.extend(['-m', 'not slow'])
    if args.coverage:
        cmd.extend(['--cov=./', '--cov-report=html', '--cov-report=term'])
    if args.parallel:
        cmd.extend(['-n', 'auto'])
    
    return run_command(cmd)

def run_specific_test(test_path, args):
    """Run a specific test file or function"""
    cmd = ['python', '-m', 'pytest', test_path]
    
    if args.verbose:
        cmd.extend(['-v', '-s'])
    if args.coverage:
        cmd.extend(['--cov=./', '--cov-report=html', '--cov-report=term'])
    
    return run_command(cmd)

def generate_test_report():
    """Generate comprehensive test report"""
    print("\n" + "="*50)
    print("GENERATING COMPREHENSIVE TEST REPORT")
    print("="*50)
    
    # Run tests with detailed output
    cmd = [
        'python', '-m', 'pytest', 'tests/',
        '--html=test_report.html',
        '--self-contained-html',
        '--cov=./',
        '--cov-report=html',
        '--cov-report=term',
        '--cov-report=xml',
        '-v'
    ]
    
    return run_command(cmd)

def validate_system():
    """Validate system setup for testing"""
    print("Validating system setup...")
    
    # Check Python version
    if sys.version_info < (3, 8):
        print("✗ Python 3.8+ required")
        return False
    print(f"✓ Python {sys.version_info.major}.{sys.version_info.minor}")
    
    # Check project structure
    required_paths = [
        'tests/unit',
        'tests/integration', 
        'tests/e2e',
        'tests/mocks',
        'tests/conftest.py'
    ]
    
    for path in required_paths:
        if not (project_root / path).exists():
            print(f"✗ Missing: {path}")
            return False
        print(f"✓ Found: {path}")
    
    # Check core modules can be imported
    try:
        from signal_processor import SignalProcessor
        from database import DatabaseManager
        print("✓ Core modules importable")
    except ImportError as e:
        print(f"✗ Import error: {e}")
        return False
    
    return True

def main():
    parser = argparse.ArgumentParser(description='Test runner for crypto prop firm system')
    parser.add_argument('test_type', nargs='?', 
                       choices=['unit', 'integration', 'e2e', 'stress', 'all', 'validate', 'report'],
                       default='all', help='Type of tests to run')
    parser.add_argument('--fast', action='store_true', help='Skip slow tests')
    parser.add_argument('--coverage', action='store_true', help='Generate coverage report')
    parser.add_argument('--parallel', action='store_true', help='Run tests in parallel')
    parser.add_argument('--verbose', action='store_true', help='Verbose output')
    parser.add_argument('--specific', type=str, help='Run specific test file or function')
    
    args = parser.parse_args()
    
    print("🚀 Crypto Prop Firm Trading System Test Runner")
    print("="*50)
    
    start_time = time.time()
    
    # System validation
    if args.test_type == 'validate':
        success = validate_system()
        sys.exit(0 if success else 1)
    
    # Check dependencies
    if not check_dependencies():
        sys.exit(1)
    
    # Setup test environment
    setup_test_environment()
    
    # Validate system
    if not validate_system():
        print("System validation failed. Fix issues before running tests.")
        sys.exit(1)
    
    # Run specific test
    if args.specific:
        result = run_specific_test(args.specific, args)
    # Generate comprehensive report
    elif args.test_type == 'report':
        result = generate_test_report()
    # Run test suites
    elif args.test_type == 'unit':
        result = run_unit_tests(args)
    elif args.test_type == 'integration':
        result = run_integration_tests(args)
    elif args.test_type == 'e2e':
        result = run_e2e_tests(args)
    elif args.test_type == 'stress':
        result = run_stress_tests(args)
    else:  # 'all'
        result = run_all_tests(args)
    
    # Print summary
    end_time = time.time()
    duration = end_time - start_time
    
    print("\n" + "="*50)
    print("TEST EXECUTION SUMMARY")
    print("="*50)
    print(f"Duration: {duration:.2f} seconds")
    
    if result == 0:
        print("✅ ALL TESTS PASSED")
        if args.coverage:
            print("📊 Coverage report generated: htmlcov/index.html")
    else:
        print("❌ TESTS FAILED")
        print("Check output above for details")
    
    print("="*50)
    
    sys.exit(result)

if __name__ == '__main__':
    main()