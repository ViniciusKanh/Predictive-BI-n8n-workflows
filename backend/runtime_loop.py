"""Loop opcional sem socketpair para Windows com bloqueio de conexões locais.

Alguns ambientes restritos permitem bind/listen, mas impedem o socketpair TCP
usado internamente pelo asyncio no Windows. Este loop substitui apenas o sinal
de sincronização por polling limitado; não libera conexões de rede bloqueadas.
"""

import asyncio
import selectors
import time


class PollingSelector(selectors.SelectSelector):
    def select(self, timeout=None):
        timeout = min(.02, timeout) if timeout is not None else .02
        if not self.get_map():
            if timeout:
                time.sleep(timeout)
            return []
        return super().select(timeout)


class LocalLoop(asyncio.SelectorEventLoop):
    def __init__(self):
        super().__init__(selector=PollingSelector())

    def _make_self_pipe(self):
        # Sem comunicação TCP para sinalizar tarefas entre threads.
        self._ssock = self._csock = None

    def _close_self_pipe(self):
        pass

    def _write_to_self(self):
        # O selector acorda em até vinte milissegundos.
        pass


def create_loop():
    return LocalLoop()
