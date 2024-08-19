from typing import Generator

from privex.coin_handlers import Deposit
from privex.coin_handlers.Telos.TelosMixin import TelosMixin
from privex.coin_handlers.base import BaseLoader


class TelosLoader(BaseLoader, TelosMixin):
    
    def list_txs(self, batch=100) -> Generator[Deposit, None, None]:
        pass

    def load(self, tx_count=1000):
        pass

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        pass

    def __init__(self, symbols):
        super(TelosLoader, self).__init__(symbols=symbols)
        self.tx_count = 1000
        self.loaded = False
