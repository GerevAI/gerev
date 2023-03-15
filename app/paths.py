import sys
import os

from pathlib import Path

_in_docker = False if (sys.platform == "win32" or not hasattr(os, "geteuid")) else os.geteuid()

STORAGE_PATH = Path('/opt/storage/') if _in_docker else Path('~/.gerev/storage/')

if not STORAGE_PATH.exists():
    STORAGE_PATH.mkdir(parents=True)

UI_PATH = Path('/ui/') if _in_docker else Path('../ui/build/')
SQLITE_DB_PATH = STORAGE_PATH / 'db.sqlite3'
FAISS_INDEX_PATH = str(STORAGE_PATH / 'faiss_index.bin')
BM25_INDEX_PATH = str(STORAGE_PATH / 'bm25_index.bin')
