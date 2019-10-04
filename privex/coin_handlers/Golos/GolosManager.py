from decimal import Decimal, ROUND_DOWN
from typing import Union, Dict, List, Tuple

from golos import Api
from privex.coin_handlers.base.objects import Coin
from privex.helpers import empty, dec_round

from privex.coin_handlers.KeyStore import get_key_store
from privex.coin_handlers.base import exceptions
from privex.coin_handlers.base.BaseManager import BaseManager
from privex.coin_handlers.Golos.GolosMixin import GolosMixin

import logging

log = logging.getLogger(__name__)


class GolosManager(BaseManager, GolosMixin):
    def __init__(self, settings: Dict[str, dict] = None, coin: Coin = None, *args, **kwargs):
        super().__init__(settings=settings, coin=coin, *args, **kwargs)
        self._rpc = None
        # List of Golos instances mapped by symbol
        self._rpcs = {}  # type: Dict[str, Api]
        self._precision = None

    def address_valid(self, address) -> bool:
        return len(self.rpc.get_accounts([address])) > 0

    def health(self) -> Tuple[str, tuple, tuple]:
        """
        Return health data for the passed symbol.

        Health data will include: 'Symbol', 'Status', 'Coin Name', 'API Node', 'Head Block', 'Block Time',
        'RPC Version', 'Our Account', 'Our Balance' (all strings)

        :return tuple health_data: (manager_name:str, headings:list/tuple, health_data:list/tuple,)
        """
        headers = ('Symbol', 'Status', 'Coin Name', 'API Node', 'Head Block', 'Block Time', 'RPC Version',
                   'Our Account', 'Our Balance')
    
        class_name = type(self).__name__
        api_node = asset_name = head_block = block_time = rpc_ver = our_account = balance = ''
    
        status = 'Okay'
        try:
            rpc = self.rpc
            our_account = self.coin.our_account
            if not self.address_valid(our_account):
                status = 'Account {} not found'.format(our_account)
        
            asset_name = self.coin.display_name
            balance = ('{0:,.' + str(self.precision) + 'f}').format(self.balance(our_account))
            api_node = rpc.rpc.url
            props = rpc.get_dynamic_global_properties()
            head_block = str(props.get('head_block_number', ''))
            block_time = props.get('time', '')
            rpc_ver = rpc.get_config()['STEEMIT_BLOCKCHAIN_VERSION']
        except:
            status = 'ERROR'
            log.exception('Exception during %s.health for symbol %s', class_name, self.symbol)
    
        if status == 'Okay':
            status = '<b style="color: green">{}</b>'.format(status)
        else:
            status = '<b style="color: red">{}</b>'.format(status)
    
        data = (self.symbol, status, asset_name, api_node, head_block, block_time, rpc_ver, our_account, balance)
        return class_name, headers, data

    def health_test(self) -> bool:
        """
        Check if our Golos node works or not, by requesting basic information such as the current block + time, and
        checking if our sending/receiving account exists on Golos.

        :return bool: True if Golos appears to be working, False if it seems to be broken.
        """
        try:
            _, _, health_data = self.health()
            if 'Okay' in health_data[1]:
                return True
            return False
        except:
            return False

    def get_deposit(self) -> tuple:
        """
        Returns the deposit account for this symbol
        :return tuple: A tuple containing ('account', receiving_account). The memo must be generated
                       by the calling function.
        """
        return 'account', self.coin.our_account

    def balance(self, address: str = None, memo: str = None, memo_case: bool = False) -> Decimal:
        if not address:
            address = self.coin.our_account
        
        if not self.address_valid(address):
            raise exceptions.AccountNotFound(f'Account "{address}" does not exist.')
        
        acc = self.rpc.get_balances(address)[address]
        return Decimal(acc[self.symbol.upper()])
    
    def send(self, amount: Decimal, address: str, from_address: str = None, memo: str = None,
             trigger_data: Union[dict, list] = None) -> dict:
        # Try from_address first. If that's empty, try using self.coin.our_account. If both are empty, abort.
        if empty(from_address):
            if empty(self.coin.our_account):
                raise AttributeError("Both 'from_address' and 'coin.our_account' are empty. Cannot send.")
            from_address = self.coin.our_account
            
        if not self.address_valid(address):
            raise exceptions.AccountNotFound(f'Account "{address}" does not exist.')
        if not self.address_valid(from_address):
            raise exceptions.AccountNotFound(f'Account "{address}" does not exist.')
        
        memo = "" if empty(memo) else memo
        prec = self.precision
        sym = self.symbol.upper()
        amount = dec_round(Decimal(amount), dp=prec, rounding=ROUND_DOWN)
        
        if amount < Decimal(pow(10, -prec)):
            log.warning('Amount %s was passed, but is lower than precision for %s', amount, sym)
            raise ArithmeticError('Amount {} is lower than token {}s precision of {} DP'.format(amount, sym, prec))
        bal = self.balance(from_address)
        if bal < amount:
            raise exceptions.NotEnoughBalance(
                'Account {} has balance {} but needs {} to send this tx'.format(from_address, bal, amount)
            )

        ###
        # Broadcast the transfer transaction on the network, and return the necessary data
        ###
        log.info('Sending %f %s to @%s', amount, sym, address)
        _, wif = self.get_priv(from_address)
        t = self.rpc.transfer(
            to=address, amount=amount, from_account=from_address, memo=memo, asset=sym, wif=wif
        )
        return {
            'txid': t['id'],
            'coin': self.symbol,
            'amount': amount,
            'fee': Decimal(0),
            'from': from_address,
            'send_type': 'send'
        }

    def get_priv(self, from_account: str, key_types: list = None):
        key_types = ['active'] if not key_types else key_types
        kstore = get_key_store()
        priv_key = kstore.get(network='golos', account=from_account, key_type__in=key_types)
        if priv_key is None:
            raise exceptions.AuthorityMissing(
                f'No private key found for GOLOS account {from_account} matching types: {key_types}'
            )
        
        return priv_key.key_type, priv_key.private_key
    
    def __enter__(self):
        pass

    def __exit__(self, exc_type, exc_val, exc_tb):
        pass
