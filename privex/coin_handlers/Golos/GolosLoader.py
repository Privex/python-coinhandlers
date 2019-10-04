from decimal import Decimal
from typing import Generator, Optional, Dict, List

import pytz
from dateutil.parser import parse
from golos import TransactionNotFound, Api

from privex.coin_handlers.base.objects import Coin
from privex.helpers import empty

from privex.coin_handlers import Deposit
from privex.coin_handlers.base import BaseLoader
from .GolosMixin import GolosMixin
import logging

log = logging.getLogger(__name__)


class GolosLoader(BaseLoader, GolosMixin):
    def __init__(self, settings: Dict[str, dict] = None, coins: List[Coin] = None, *args, **kwargs):
        self._rpc = None
        # List of Golos instances mapped by symbol
        self._rpcs = {}  # type: Dict[str, Api]
        
        super(GolosLoader, self).__init__(settings=settings, coins=coins, *args, **kwargs)
        self.tx_count = 1000

    def list_txs(self, batch=100) -> Generator[Deposit, None, None]:
        log.debug('Symbols: %s', self.symbols)
        for s in self.symbols:
            rpc = self.get_rpc(s)
            our_account = self.coins[s].our_account
            txs = rpc.get_account_history(our_account)
            log.debug('Looping over %s txs', s)
            for tx in txs:
                try:
                    cleaned = self._clean_tx(tx=tx, symbol=s, account=our_account)
                
                    if cleaned is None:
                        continue
                
                    yield Deposit(**cleaned)
                except Exception:
                    log.exception('(skipping) Error processing Golos TX %s', tx)
                    continue

    def load(self, tx_count=1000):
        # Unlike other coins, it's important to load a lot of TXs, because many won't actually be transfers
        # Thus the default TX count for Steem is 10,000
        self.tx_count = tx_count
        coins = dict(self.coins)
        for symbol, coin in coins.items():
            coin: Coin
            if not empty(coin.our_account):
                continue
            log.warning('The coin %s does not have `our_account` set. Refusing to load transactions.', coin)
            del self.coins[symbol]
            self.symbols = [s for s in self.symbols if s != symbol]

    def __enter__(self):
        pass

    def __exit__(self, exc_type, exc_val, exc_tb):
        pass

    def _clean_tx(self, tx: dict, symbol, account: str = None, memo: str = None) -> Optional[dict]:
        """Filters an individual transaction dictionary"""
        
        if tx.get('type_op') != 'transfer':
            return
        
        res = {
            'coin': self.coins[symbol].symbol, 'from_account': tx.get('from'), 'to_account': tx.get('to'),
            'vout': int(0), 'txid': tx['trx_id'], 'memo': tx.get('memo', '').strip(),
        }
        if account is not None and (res['to_account'] != account or res['from_account'] == account):
            return None  # If the transaction isn't to us (account), or it's from ourselves, ignore it.
        if memo is not None and res['memo'] != memo.strip():
            return None
            
        amt, sym = tx['amount'].split(' ')
        if sym.upper() != symbol.upper():
            log.debug(f'Skipping TX as symbol was {sym.upper()} (expected {symbol.upper()})')
            return
        res['amount'] = Decimal(amt)
        res['tx_timestamp'] = pytz.utc.localize(parse(tx['timestamp']))
        
        return res
        

