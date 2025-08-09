# Test Suite for Crypto Prop Firm Trading System

This comprehensive test suite validates the complete trading system from signal processing to trade execution and notifications.

## Test Structure

```
tests/
├── unit/                      # Unit tests - test individual components
│   ├── test_signal_processor.py
│   ├── test_prop_firm_processor.py
│   ├── test_database.py
│   └── test_trading_engine.py
├── integration/               # Integration tests - test component interactions
│   ├── test_database_integration.py
│   └── test_telegram_integration.py
├── e2e/                      # End-to-end tests - test complete workflows
│   ├── test_full_workflow.py
│   └── test_stress_scenarios.py
├── mocks/                    # Mock objects for external dependencies
│   ├── mock_mt5.py
│   ├── mock_telegram.py
│   └── mock_binance.py
├── fixtures/                 # Test data and fixtures
├── conftest.py              # Shared pytest configuration and fixtures
├── pytest.ini              # Pytest configuration
└── requirements-test.txt    # Test dependencies
```

## Quick Start

### 1. Install Test Dependencies

```bash
pip install -r tests/requirements-test.txt
```

### 2. Run All Tests

```bash
python run_tests.py
```

### 3. Run Specific Test Categories

```bash
# Unit tests only
python run_tests.py unit

# Integration tests only
python run_tests.py integration

# End-to-end tests only
python run_tests.py e2e

# Stress tests only
python run_tests.py stress
```

### 4. Run with Coverage

```bash
python run_tests.py --coverage
```

### 5. Run Tests in Parallel

```bash
python run_tests.py --parallel
```

## Test Categories

### Unit Tests (`tests/unit/`)

Test individual components in isolation with mocked dependencies.

- **Signal Processing**: Validates signal parsing, validation, and risk calculations
- **Prop Firm Rules**: Tests prop firm compliance and decision logic
- **Database Operations**: Tests CRUD operations, transactions, and data integrity
- **Trading Engine**: Tests trade execution logic and risk management

**Run unit tests:**
```bash
pytest tests/unit/ -m unit
```

### Integration Tests (`tests/integration/`)

Test component interactions and system integration points.

- **Database Integration**: Tests multi-component database operations
- **Telegram Integration**: Tests notification system with various scenarios
- **System Integration**: Tests interactions between major components

**Run integration tests:**
```bash
pytest tests/integration/ -m integration
```

### End-to-End Tests (`tests/e2e/`)

Test complete workflows from signal reception to trade closure.

- **Full Workflow**: Complete signal → processing → trade → notification → close cycle
- **Prop Firm Workflow**: Signal evaluation through prop firm rules
- **Risk Management**: Tests risk limits and position management
- **Error Handling**: Tests system behavior under various failure conditions

**Run e2e tests:**
```bash
pytest tests/e2e/ -m e2e
```

### Stress Tests (`tests/e2e/test_stress_scenarios.py`)

Test system performance and reliability under high load.

- **High Volume Processing**: Thousands of signals processed rapidly
- **Concurrent Operations**: Multiple threads processing signals simultaneously
- **Memory Usage**: Large dataset handling and memory management
- **Network Failures**: Simulated connection failures and recovery
- **Database Stress**: Connection pooling and transaction handling under load

**Run stress tests:**
```bash
pytest tests/e2e/test_stress_scenarios.py -m stress
```

## Mock Components

### MockMT5Terminal (`tests/mocks/mock_mt5.py`)

Simulates MetaTrader 5 terminal for testing without live connection.

Features:
- Account management simulation
- Order execution simulation
- Position tracking
- Price movement simulation
- Stop loss/Take profit triggers

### MockTelegramNotifier (`tests/mocks/mock_telegram.py`)

Simulates Telegram API for notification testing.

Features:
- Message sending simulation
- Failure simulation
- Message history tracking
- Statistics collection
- Rate limiting simulation

### MockBinanceWebSocket (`tests/mocks/mock_binance.py`)

Simulates Binance WebSocket for market data testing.

Features:
- Real-time price simulation
- Market condition simulation
- Connection failure simulation
- High-frequency data generation

## Test Configuration

### pytest.ini

Central configuration for pytest with markers and settings:

```ini
[tool:pytest]
markers =
    unit: Unit tests
    integration: Integration tests  
    e2e: End-to-end tests
    stress: Stress tests
    slow: Slow running tests
    network: Tests requiring network access
```

### Environment Variables

Tests use these environment variables (automatically set by test runner):

- `TESTING=true`: Indicates test mode
- `DATABASE_URL=:memory:`: Use in-memory database
- `TELEGRAM_BOT_TOKEN=test_token`: Test Telegram token
- `TELEGRAM_CHAT_ID=12345`: Test chat ID
- `MT5_LOGIN=12345`: Test MT5 login
- `MT5_PASSWORD=test_password`: Test MT5 password
- `MT5_SERVER=test_server`: Test MT5 server

## Key Test Scenarios

### 1. Complete Signal-to-Notification Workflow

Tests the entire process:
1. Signal message received
2. Signal parsed and validated
3. Risk management checks pass
4. Trade executed in database
5. Telegram notification sent
6. Position monitored
7. Trade closed on TP/SL hit
8. Close notification sent
9. Database updated with results

### 2. Prop Firm Rule Validation

Tests comprehensive prop firm compliance:
- Risk-reward ratio validation (minimum 1.5:1)
- Position sizing calculations (max 2% risk)
- Daily loss limits ($500 max)
- Maximum drawdown limits ($600 max)
- Daily trade limits (10 trades max)
- Trading suspension triggers

### 3. High-Volume Stress Testing

Tests system under extreme load:
- 5,000+ signals processed rapidly
- Concurrent processing from 10+ threads
- Memory usage monitoring
- Performance degradation detection
- Database connection management

### 4. Error Recovery and Resilience

Tests system behavior under failures:
- Database connection failures
- Network timeouts
- Invalid signal formats
- MT5 connection issues
- Telegram API failures

## Test Data Management

### Fixtures (`tests/conftest.py`)

Shared test fixtures provide:
- Temporary databases
- Mock components
- Sample trade data
- Signal message templates
- Test configuration

### Data Generation

Tests use various data generation methods:
- **Static fixtures**: Predefined test data
- **Random generation**: Dynamic test scenarios  
- **Factory patterns**: Consistent object creation
- **Property-based testing**: Edge case discovery

## Coverage Reports

### Generate Coverage Reports

```bash
python run_tests.py --coverage
```

Coverage reports are generated in multiple formats:
- **HTML**: `htmlcov/index.html` (detailed interactive report)
- **Terminal**: Summary displayed after test run
- **XML**: `coverage.xml` (for CI integration)

### Coverage Targets

- **Unit Tests**: 90%+ coverage expected
- **Integration Tests**: Focus on component interactions
- **E2E Tests**: Focus on complete workflows
- **Overall**: 85%+ coverage target

## Performance Testing

### Benchmarking

Performance benchmarks are included for:
- Signal processing rate (target: 100+ signals/second)
- Database operations (target: <1s for 1000 trades)
- Memory usage (target: <500MB for 10k trades)
- Notification rate (target: 100+ notifications/second)

### Performance Regression Detection

Stress tests detect performance degradation:
- Baseline performance measurement
- Load testing with increasing data
- Degradation percentage calculation
- Alerts for >50% performance drops

## Continuous Integration

### GitHub Actions Integration

For CI/CD integration, add to `.github/workflows/test.yml`:

```yaml
- name: Run Tests
  run: |
    pip install -r tests/requirements-test.txt
    python run_tests.py --coverage --parallel
```

### Test Automation

The test suite supports automation with:
- Exit codes (0=success, 1=failure)
- JUnit XML output for CI systems
- Coverage reports in XML format
- Parallel execution for speed
- Selective test execution by marker

## Troubleshooting

### Common Issues

1. **Import Errors**
   - Ensure project root is in Python path
   - Install all dependencies: `pip install -r requirements.txt`
   - Install test dependencies: `pip install -r tests/requirements-test.txt`

2. **Database Errors**
   - Tests use temporary databases
   - Check file permissions in temp directory
   - Ensure SQLite is available

3. **Slow Tests**
   - Use `--fast` flag to skip slow tests
   - Use `--parallel` for parallel execution
   - Consider running only specific test categories

4. **Memory Issues**
   - Stress tests may use significant memory
   - Close other applications during stress testing
   - Monitor system resources

### Debug Mode

For debugging specific test failures:

```bash
# Run with verbose output and no capture
pytest tests/unit/test_signal_processor.py -v -s

# Run specific test function
pytest tests/unit/test_signal_processor.py::TestSignalProcessor::test_parse_signal_format_1_smrt_signals -v -s

# Drop to debugger on failure
pytest tests/unit/test_signal_processor.py --pdb
```

## Contributing Tests

### Adding New Tests

1. **Choose appropriate category** (unit/integration/e2e)
2. **Follow naming conventions** (`test_*.py`, `Test*` classes, `test_*` methods)
3. **Use appropriate markers** (`@pytest.mark.unit`, etc.)
4. **Include docstrings** explaining test purpose
5. **Use fixtures** for common setup/teardown
6. **Mock external dependencies** appropriately

### Test Quality Guidelines

- **Test one thing**: Each test should verify one specific behavior
- **Clear naming**: Test names should describe what is being tested
- **Arrange-Act-Assert**: Structure tests clearly
- **Independent**: Tests should not depend on other tests
- **Deterministic**: Tests should produce consistent results
- **Fast**: Unit tests should complete quickly (<1s each)

### Mock Usage Guidelines

- **Mock external systems**: MT5, Telegram API, external price feeds
- **Don't mock core logic**: Test actual business logic
- **Verify mock calls**: Ensure mocks are called as expected
- **Reset mocks**: Clear state between tests
- **Realistic behavior**: Mocks should behave like real systems

## Conclusion

This comprehensive test suite ensures the reliability, performance, and correctness of the crypto prop firm trading system. It covers everything from individual component testing to complete workflow validation, providing confidence in system behavior across all scenarios.

The combination of unit, integration, end-to-end, and stress tests creates a robust safety net that catches issues early and ensures the system performs reliably in production environments.