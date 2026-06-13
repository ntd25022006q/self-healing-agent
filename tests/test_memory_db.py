import sys
import os
import sqlite3

# Add parent directory to sys.path
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), "..")))

from config import Config

# Configure temp db path for testing
test_db_path = os.path.abspath(os.path.join(os.path.dirname(__file__), "..", "test_memory.db"))
Config.MEMORY_DB_PATH = test_db_path

from tools.memory_db import MemoryDB

def setup_module(module):
    # Ensure test db is clean
    if os.path.exists(test_db_path):
        os.remove(test_db_path)

def teardown_module(module):
    # Clean up test db
    if os.path.exists(test_db_path):
        os.remove(test_db_path)

def test_db_initialization():
    MemoryDB.init_db()
    assert os.path.exists(test_db_path)
    
    # Check that default score is 100
    assert MemoryDB.get_agent_score() == 100

def test_score_updates():
    MemoryDB.init_db()
    new_score = MemoryDB.update_agent_score(25)
    assert new_score == 125
    assert MemoryDB.get_agent_score() == 125
    
    new_score = MemoryDB.update_agent_score(-50)
    assert new_score == 75
    assert MemoryDB.get_agent_score() == 75

def test_save_and_query_experience():
    MemoryDB.init_db()
    MemoryDB.save_experience(
        "fix bug in parser",
        "IndexError: list index out of range",
        "def parse(lst):\n    return lst[0] if lst else None",
        score=95
    )
    
    similar = MemoryDB.query_similar_experiences("IndexError parser", limit=1)
    assert len(similar) == 1
    assert similar[0]["task_description"] == "fix bug in parser"
    assert "lst[0]" in similar[0]["fix_code"]
