from datetime import datetime
from decimal import Decimal
from typing import Generator, List, Dict

import pytz
from privex.helpers import empty, sleep
from privex.jsonrpc.objects import MoneroTransfer

from privex.coin_handlers.base.objects import Deposit, Coin
from privex.jsonrpc import MoneroRPC

from privex.coin_handlers.Monero.MoneroMixin import MoneroMixin
from privex.coin_handlers.base.BaseLoader import BaseLoader

import logging

log = logging.getLogger(__name__)


class MoneroLoader(BaseLoader, MoneroMixin):

    def __init__(self, settings: Dict[str, dict] = None, coins: List[Coin] = None, *args, **kwargs):
        super(MoneroLoader, self).__init__(settings=settings, coins=coins, *args, **kwargs)
        self.tx_count = 1000
        self.loaded = False
        # Get all RPC objects
        self.rpcs = self._get_rpcs()
        self.wallet_opened = False

    def list_txs(self, batch=100) -> Generator[Deposit, None, None]:
        log.debug('Symbols: %s', self.symbols)
        for s in self.symbols:
            log.debug('Entering wallet for %s', s)
            with self.wallet(s) as w:  # type: MoneroRPC
                log.debug('Looking up account ID for symbol %s', s)
                acc_id = self.account_id(symbol=s)
                log.debug('Loading transfers for account ID %s', acc_id)
                txs = w.get_transfers(account_index=acc_id)
            log.debug('Looping over "in" txs')
            for tx in txs.get('in', []):
                try:
                    cleaned = self._clean_tx(tx=tx, symbol=s)

                    if cleaned is None:
                        continue

                    yield Deposit(**cleaned)
                except Exception:
                    log.exception('(skipping) Error processing Monero TX %s', tx)
                    continue

    def _clean_tx(self, tx: MoneroTransfer, symbol, address=None) -> dict:
        """Filters an individual transaction. See :meth:`.clean_txs` for info"""

        need_confs = self.settings[symbol].get('confirms_needed', 1)

        txid = tx.txid
        category = tx.type
        amt = tx.decimal_amount

        log.debug('Filtering/cleaning transaction, Cat: %s, Amt: %s, TXID: %s', category, amt, txid)

        if category != 'in': return None  # Ignore non-receive transactions
        # if 'generated' in tx and tx['generated'] in [True, 'true', 1]: return None  # Ignore mining transactions
        # Filter by receiving address if needed
        if not empty(address) and tx.address != address: return None
        # If a TX has less confirmations than needed, check if we can trust unconfirmed TXs.
        # If not, we can't accept this TX.
        confs = int(tx.confirmations)
        if confs < need_confs:
            if confs < int(tx.suggested_confirmations_threshold):
                log.debug('Got %s transaction %s, but only has %d confs, needs %d', symbol, txid, confs, need_confs)
                return None
        d = datetime.utcfromtimestamp(tx.timestamp)
        d = pytz.utc.localize(d)

        return dict(
            txid=txid,
            coin=self.coins[symbol].symbol,
            vout=int(0),
            tx_timestamp=d,
            address=tx.address,
            amount=Decimal(amt)
        )

    def load(self, tx_count=1000):
        pass

    def __enter__(self):
        log.debug('%s entering with statement', self.__class__.__name__)

        if self.wallet_opened:
            log.debug('Wallet already open')
            return self
        s = self.xmr_settings
        if empty(s['wallet']):
            log.debug('%s entered. No wallet specified for %s. Not opening any wallet.', self.__class__.__name__)
            return self

        sleep(3)
        log.debug('Opening wallet %s', s['wallet'])
        self.rpcs['XMR'].open_wallet(filename=s['wallet'], password=s['walletpass'])
        log.debug('Wallet opened')
        self.wallet_opened = True
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        s = self.xmr_settings
        if empty(s['wallet']):
            log.debug('%s exiting. No wallet specified. Not closing any wallet.', self.__class__.__name__)
            return self
        log.debug('%s exiting. Calling store()', self.__class__.__name__)
        self.rpcs['XMR'].store()
        self.wallet_opened = False
