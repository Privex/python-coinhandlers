from decimal import Decimal
from time import sleep
from typing import Union, Dict, List

from privex.helpers import empty, is_true
from privex.jsonrpc import MoneroRPC
from privex.jsonrpc.core import atomic_to_decimal

from privex.coin_handlers.base.objects import Coin
from privex.coin_handlers.base.BaseManager import BaseManager
from privex.coin_handlers.Monero.MoneroMixin import MoneroMixin

import logging

log = logging.getLogger(__name__)


class MoneroManager(BaseManager, MoneroMixin):

    def __init__(self, settings: Dict[str, dict] = None, coin: Coin = None, *args, **kwargs):
        super(MoneroManager, self).__init__(settings=settings, coin=coin, *args, **kwargs)
        # Get all RPC objects
        self.rpcs = self._get_rpcs()
        self.rpc = self.rpcs[self.symbol]
        self.wallet_opened = False

    def address_valid(self, address) -> bool:
        validate = self.rpc.validate_address(address=address)
        return is_true(validate['valid'])

    def get_deposit(self) -> tuple:
        """
        Returns a deposit address for this symbol
        :return tuple: A tuple containing ('address', crypto_address)
        """
        account_id = self.account_id(symbol=self.symbol)

        return 'address', self.rpc.create_address(account_index=account_id)['address']

    def balance(self, address: str = None, memo: str = None, memo_case: bool = False) -> Decimal:
        total_bal = Decimal('0')

        with self.wallet(self.symbol) as w:  # type: MoneroRPC
            account_id = self.account_id(symbol=self.symbol)
            bal = w.get_balance(account_index=account_id)
            # log.debug('Balance data: %s', bal)
            if address is None:
                return atomic_to_decimal(bal['balance'])

            for a in bal['per_subaddress']:
                log.debug('Sub-address: %s', a)
                if a['address'] == address:
                    total_bal += atomic_to_decimal(a['balance'])
        return total_bal

    def send(self, amount: Decimal, address: str, from_address: str = None, memo: str = None,
             trigger_data: Union[dict, list] = None) -> dict:
        raise NotImplemented

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
