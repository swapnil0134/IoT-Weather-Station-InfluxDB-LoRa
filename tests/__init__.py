"""Test configuration for pytest."""

import pytest
import sys
import os

# Add src to Python path for tests
sys.path.insert(0, os.path.join(os.path.dirname(__file__), '..', 'src'))