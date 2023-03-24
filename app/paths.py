from pathlib import Path
import os

IS_IN_DOCKER = os.geteuid() == 0

STORAGE_PATH = Path('/opt/storage/') if IS_IN_DOCKER else Path(f'/home/{os.getlogin()}/.gerev/storage/')

if not STORAGE_PATH.exists():
    STORAGE_PATH.mkdir(parents=True)

UI_PATH = Path('/ui/') if IS_IN_DOCKER else Path('../ui/build/')
SQLITE_DB_PATH = STORAGE_PATH / 'db.sqlite3'
FAISS_INDEX_PATH = str(STORAGE_PATH / 'faiss_index.bin')
BM25_INDEX_PATH = str(STORAGE_PATH / 'bm25_index.bin')
UUID_PATH = str(STORAGE_PATH / '.uuid')
