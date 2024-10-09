from decimal import Decimal
from time import sleep
from typing import Union, Dict, List

from privex.helpers import empty, is_true
from privex.jsonrpc import MoneroRPC, RPCException
from privex.jsonrpc.core import atomic_to_decimal

from privex.coin_handlers.base.objects import Coin
from privex.coin_handlers.base.exceptions import AccountNotFound, NotEnoughBalance, CoinHandlerException, DeadAPIError
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

    def send(self, amount: Decimal, address: str, from_address: int = 0, memo: str = None,
             trigger_data: Union[dict, list] = None) -> dict:
        """
        Send the amount `amount` of XMR to a given address
        Note that `from_address` should be used as the account index (int) to send from
        
        Example - send 0.1 XMR to 4xxxxxxxxxx

            >>> s = MoneroManager()
            >>> s.send(amount=Decimal('0.1'), address='4xxxxxxxxx', from_address=2)

        :param Decimal amount:      Amount of coins to send, as a Decimal()
        :param address:             Address to send the coins to
        :param from_address:        The monero account index to use as an integer
        :param memo:                NOT USED BY THIS MANAGER
        :raises AccountNotFound:    The destination `address` isn't valid
        :raises NotEnoughBalance:   The wallet does not have enough balance to send this amount.
        :return dict: Result Information

        Format::

          {
              txid:str - Transaction ID - None if not known,
              tx_key:str - Transaction Key - None if not known,
              tx_metadata:str - Transaction metadata - None if not known,
              tx_blob:str - Transaction blob - None if not known,
              coin:str - Symbol that was sent,
              amount:Decimal - The amount that was sent (after fees),
              fee:Decimal    - TX Fee that was taken from the amount,
              from:str       - The account/address the coins were sent from,
              send_type:str       - Should be statically set to "send"
          }

        """
        from_address = 0 if from_address is None else int(from_address)
        v = self.rpc.validate_address(address)
        if not v['valid']:
            raise AccountNotFound(f"Invalid Monero address '{address}'")
        try:
            snd = self.rpc.simple_transfer(
                amount=amount, address=address, account_index=from_address
            )
        except RPCException as e:
            errs = str(e)
            if 'WALLET_RPC_ERROR_CODE_WRONG_ADDRESS' in errs.upper():
                raise AccountNotFound(f"Invalid Monero address '{address}'")
            if 'not enough money' in errs.lower():
                raise NotEnoughBalance(f"Failed to send {amount} XMR to {address} - not enough balance!")
            raise e

        res = dict(
            txid=snd['tx_hash'],
            amount=self.rpc.atomic_to_decimal(snd['amount']),
            fee=self.rpc.atomic_to_decimal(snd['fee']),
            tx_key=snd.get('tx_key', None),
            tx_blob=snd.get('tx_blob', None),
            tx_metadata=snd.get('tx_metadata', None),
            coin=self.symbol,
            send_type='send'
        )
        res['from'] = from_address
        return res

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
