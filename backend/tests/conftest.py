"""Shared test configuration.

Point the app at a throwaway SQLite file and a test signing key *before* any application
module is imported, so the cached settings and database engine pick them up.
"""

import os
import tempfile

_tmp_db = os.path.join(tempfile.gettempdir(), "voidfall_test.db")
if os.path.exists(_tmp_db):
    os.remove(_tmp_db)

os.environ.setdefault("VOIDFALL_DATABASE_URL", f"sqlite:///{_tmp_db}")
os.environ.setdefault("VOIDFALL_JWT_SECRET", "test-secret-key-not-for-production")
os.environ.setdefault("VOIDFALL_ENVIRONMENT", "test")
# Tests must be hermetic and offline — never touch a live LLM, even if .env sets one.
os.environ["VOIDFALL_LLM_PROVIDER"] = "none"
