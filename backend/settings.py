"""Configuração local; credenciais nunca fazem parte do código-fonte."""

import os
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[1]
if os.getenv('PBI_CONTAINER') != '1':
    load_dotenv(ROOT / '.runtime' / 'local.env', override=False)
load_dotenv(ROOT / '.env', override=False)
DATA = Path(os.getenv('DATA_DIR', str(ROOT / 'data')))
ARTIFACTS = Path(os.getenv('ARTIFACTS_DIR', str(ROOT / 'artifacts')))
DATABASE_URL = os.getenv('DATABASE_URL', 'sqlite:///' + str(DATA / 'demo.db'))
OLLAMA_URL = os.getenv('OLLAMA_BASE_URL', 'http://127.0.0.1:11434')
OLLAMA_MODEL = os.getenv('OLLAMA_MODEL', '')
MLFLOW_URI = os.getenv('MLFLOW_TRACKING_URI', 'http://127.0.0.1:5010')
for folder in (DATA, ARTIFACTS):
    folder.mkdir(parents=True, exist_ok=True)
