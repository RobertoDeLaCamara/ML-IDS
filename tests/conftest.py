import pytest
import os
import shutil
import logging

@pytest.fixture(autouse=True)
def cleanup_files():
    """
    Clean up test files before and after tests
    """
    # Setup: remove any existing model and logs
    if os.path.exists('model.pkl'):
        os.remove('model.pkl')
    if os.path.exists('logs'):
        shutil.rmtree('logs')
    
    # Run the tests
    yield
    
    # Teardown: remove any created model and logs
    if os.path.exists('model.pkl'):
        os.remove('model.pkl')
    if os.path.exists('logs'):
        shutil.rmtree('logs')

@pytest.fixture(autouse=True)
def disable_logging():
    """Disable logging during tests"""
    logging.getLogger().setLevel(logging.ERROR)