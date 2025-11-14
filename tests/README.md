# Test Suite Documentation

Comprehensive test suite for the News Edit Agent prototype.

## Overview

The test suite covers all major components of the system:

- **Storage Layer**: Database and vector index operations
- **Agent Modules**: Planner, Picker, Verifier agents
- **Output Writers**: EDL and FCPXML generation
- **Working Set Builder**: Shot selection and relevance scoring

## Test Structure

```
tests/
├── __init__.py           # Test package
├── conftest.py           # Shared fixtures and configuration
├── test_storage.py       # Storage layer tests
├── test_agents.py        # Agent module tests
├── test_output.py        # Output writer tests
└── README.md            # This file
```

## Running Tests

### Run All Tests

```bash
# Using the test runner script
bash run_tests.sh

# Or directly with pytest
pytest tests/
```

### Run Specific Test Files

```bash
# Storage tests only
pytest tests/test_storage.py

# Output writer tests only
pytest tests/test_output.py

# Agent tests only
pytest tests/test_agents.py
```

### Run Specific Test Classes or Functions

```bash
# Run a specific test class
pytest tests/test_storage.py::TestShotsDatabase

# Run a specific test function
pytest tests/test_output.py::TestEDLWriter::test_write_edl
```

### Run with Verbose Output

```bash
pytest tests/ -v
```

### Run with Coverage Report

```bash
pytest tests/ --cov=. --cov-report=html
```

## Test Fixtures

The `conftest.py` file provides shared fixtures:

- `temp_dir`: Temporary directory for test files
- `test_db`: Test database instance
- `test_vector_index`: Test vector index
- `sample_shot_data`: Sample shot data
- `sample_shots_list`: List of sample shots
- `mock_llm_client`: Mocked LLM client
- `sample_plan`: Sample planner output
- `sample_selections`: Sample picker output
- `sample_verification`: Sample verifier output

## Test Coverage

### Storage Layer (`test_storage.py`)

**TestShotsDatabase**:
- Database creation
- Storing shots
- Retrieving shots by story
- Searching shots
- Getting story statistics

**TestVectorIndex**:
- Index creation
- Adding vectors
- Similarity search
- Removing vectors

### Agent Modules (`test_agents.py`)

**TestWorkingSetBuilder**:
- Builder creation
- Building working sets

**TestPlannerAgent**:
- Planner creation
- Plan generation

**TestPickerAgent**:
- Picker creation
- Shot selection

**TestVerifierAgent**:
- Verifier creation
- Edit verification

### Output Writers (`test_output.py`)

**TestEDLWriter**:
- Writer creation
- Timecode conversion
- EDL file generation
- EDL validation

**TestFCPXMLWriter**:
- Writer creation
- Frame duration calculation
- Frame conversion
- FCPXML file generation
- FCPXML validation

## Writing New Tests

### Test Naming Convention

- Test files: `test_*.py`
- Test classes: `Test*`
- Test functions: `test_*`

### Example Test

```python
def test_my_feature(test_db, sample_shot_data):
    """Test description."""
    # Arrange
    test_db.store_shot(sample_shot_data)
    
    # Act
    result = test_db.get_shot(sample_shot_data['shot_id'])
    
    # Assert
    assert result is not None
    assert result['shot_id'] == sample_shot_data['shot_id']
```

### Using Fixtures

```python
def test_with_fixtures(temp_dir, mock_llm_client):
    """Test using multiple fixtures."""
    # temp_dir and mock_llm_client are automatically provided
    output_path = Path(temp_dir) / "output.txt"
    # ... test code
```

### Mocking LLM Calls

```python
def test_agent_with_mock(mock_llm_client):
    """Test agent with mocked LLM."""
    # Configure mock response
    mock_llm_client.generate.return_value = {
        'response': '{"key": "value"}',
        'usage': {'prompt_tokens': 100, 'completion_tokens': 50}
    }
    
    # Use in test
    agent = MyAgent(mock_llm_client)
    result = agent.do_something()
    
    # Verify mock was called
    mock_llm_client.generate.assert_called_once()
```

## Test Markers

Tests can be marked for selective execution:

```python
@pytest.mark.unit
def test_unit_test():
    """Unit test."""
    pass

@pytest.mark.integration
def test_integration():
    """Integration test."""
    pass

@pytest.mark.slow
def test_slow_operation():
    """Slow test."""
    pass

@pytest.mark.requires_llm
def test_with_real_llm():
    """Test requiring LLM API."""
    pass
```

Run marked tests:

```bash
# Run only unit tests
pytest -m unit

# Run everything except slow tests
pytest -m "not slow"

# Run integration tests
pytest -m integration
```

## Continuous Integration

The test suite is designed to run in CI/CD pipelines:

```yaml
# Example GitHub Actions workflow
- name: Run tests
  run: |
    pip install -r requirements.txt
    pytest tests/ -v
```

## Troubleshooting

### Import Errors

If you see import errors, ensure you're running tests from the project root:

```bash
cd /path/to/RAWRE
pytest tests/
```

### Fixture Not Found

Make sure `conftest.py` is in the `tests/` directory and pytest can discover it.

### Mock Not Working

Verify the mock is configured before the code under test runs:

```python
# Configure mock BEFORE calling the function
mock_client.generate.return_value = {...}
result = function_using_client(mock_client)
```

## Best Practices

1. **Isolation**: Each test should be independent
2. **Clarity**: Test names should describe what they test
3. **Arrange-Act-Assert**: Structure tests clearly
4. **Fixtures**: Use fixtures for common setup
5. **Mocking**: Mock external dependencies (LLM, file I/O)
6. **Coverage**: Aim for high coverage of critical paths
7. **Speed**: Keep tests fast; mark slow tests appropriately

## Future Enhancements

- [ ] Integration tests with real video files
- [ ] Performance benchmarks
- [ ] API endpoint tests
- [ ] CLI command tests
- [ ] End-to-end workflow tests
- [ ] Load testing
- [ ] Security testing

## Resources

- [Pytest Documentation](https://docs.pytest.org/)
- [Pytest Fixtures](https://docs.pytest.org/en/stable/fixture.html)
- [Pytest Mocking](https://docs.pytest.org/en/stable/how-to/monkeypatch.html)
