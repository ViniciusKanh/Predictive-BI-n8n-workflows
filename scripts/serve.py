"""Inicia a API e o build do dashboard somente em loopback."""

import os
import argparse
import socket
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

if __name__ == '__main__':
    import uvicorn
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--port', type=int, default=8100)
    args = parser.parse_args()
    if not 1024 <= args.port <= 65535:
        parser.error('A porta deve estar entre 1024 e 65535.')
    with socket.socket() as probe:
        try:
            probe.bind(('127.0.0.1', args.port))
        except OSError:
            raise SystemExit(f'A porta {args.port} já está ocupada; use outra porta. Nenhum processo foi alterado.') from None
    runtime = Path(__file__).resolve().parents[1] / '.runtime'
    runtime.mkdir(exist_ok=True)
    (runtime / 'api.pid').write_text(str(os.getpid()), encoding='ascii')
    loop = 'backend.runtime_loop:create_loop' if os.getenv('PBI_RESTRICTED_LOOP') == '1' else 'auto'
    uvicorn.run('backend.main:app', host='127.0.0.1', port=args.port, log_level='info', loop=loop)
