import logging
from abc import ABC
from typing import Dict, Any, Union, List

from privex.coin_handlers.base.exceptions import AccountNotFound
from privex.helpers import empty, sleep
from privex.jsonrpc import MoneroRPC
from privex.coin_handlers.base.SettingsMixin import SettingsMixin

log = logging.getLogger(__name__)


class RPCWrapper:
    rpc: MoneroRPC

    def __init__(self, rpc: MoneroRPC, *args, **kwargs):
        self.rpc = rpc

    def __getattr__(self, name):
        def c(*args, **kwargs):
            return getattr(self.rpc, name)(*args, **kwargs)

        return c

    def __enter__(self): return self

    def __exit__(self, exc_type, exc_val, exc_tb): pass


class MoneroWallet(RPCWrapper):
    """
    Monero wallet ``with`` wrapper. Opens wallet at start of ``with``, saves wallet after exiting ``with`` statement.

        >>> # Once an instance is used with ``with`` - the specified wallet gets opened automatically
        >>> with MoneroWallet(rpc=MoneroRPC(), wallet='mywallet', walletpass='mypass') as m:
        ...     m: MoneroRPC   # Set the type of MoneroWallet to MoneroRPC, so you can use passthru calls
        ...     accounts = m.get_accounts()
        ...     print('Current block:', m.get_height())
        ...
        >>> # Now that the ``with`` statement has ended, the wallet is properly saved.

    """
    wallet: str
    walletpass: str

    def __init__(self, rpc: MoneroRPC, wallet: str = None, walletpass=None, *args, **kwargs):
        super().__init__(rpc=rpc, *args, **kwargs)
        self.wallet, self.walletpass = wallet, walletpass

    def __enter__(self):
        if empty(self.wallet):
            log.debug('MoneroWallet entered. No wallet specified for MoneroWallet. Not opening any wallet.')
            return self
        log.debug('MoneroWallet entered for wallet %s', self.wallet)
        log.debug('Opening wallet %s', self.wallet)
        self.rpc.open_wallet(filename=self.wallet, password=self.walletpass)
        return self

    def __exit__(self, exc_type, exc_val, exc_tb):
        log.debug('MoneroWallet exiting. Saving wallet.')
        self.rpc.store()

    def __getattr__(self, name):
        """
        Pass any unknown attributes as if they were calls to our MoneroRPC.

        :param name: Name of the attribute requested
        :return: Dict or List from call result
        """

        def c(*args, **kwargs):
            return getattr(self.rpc, name)(*args, **kwargs)

        return c


class MoneroMixin(SettingsMixin, ABC):
    setting_defaults = dict(
        host='127.0.0.1', port=18100, user=None, password=None, wallet='default', walletpass=None,
        account=None, account_id=None, confirms_needed=1
    )
    rpcs: Dict[str, MoneroRPC]
    _account_ids = {}

    def __init__(self, settings: Dict[str, dict], *args, **kwargs):
        if not hasattr(self, 'wallet_opened'):
            self.wallet_opened = False
        super().__init__(*args, settings=settings, **kwargs)

    def wallet(self, symbol: str = 'XMR') -> Union[MoneroRPC, RPCWrapper]:
        """
        Usage:


            >>> with self.wallet('XMR') as m:
            ...     m: MoneroRPC
            ...     accounts = m.get_accounts()
            ...     print('Current block:', m.get_height())
            ...


        :param str symbol: The coin symbol to initialise a wallet instance for
        :return MoneroWallet wallet: An instance of MoneroWallet for use with a ``with`` statement.
        """
        # If wallet_opened is True, then this class instance is already being used with ``with``, so we
        # don't need to call open_wallet() for every call - thus we use the simple RPCWrapper scaffolding
        if self.wallet_opened:
            return RPCWrapper(self.rpcs[symbol])
        # Otherwise, the class instance doesn't seem to be in a ``with`` statement, so use MoneroWallet to
        # handle automatically opening the wallet, and calling store() when done.
        s = self.settings[symbol]
        return MoneroWallet(rpc=self.rpcs[symbol], wallet=s['wallet'], walletpass=s['walletpass'])

    def find_account_label(self, label: str, symbol: str = 'XMR') -> dict:
        """
        Find a Monero wallet account by it's label/tag

            >>> acc = self.find_account_label('myaccount','XMR')
            >>> print(a['account_index'])
            3
            >>> print(a['balance'])
            1000000000

        :param str symbol: The coin symbol (for using the correct RPC)
        :param str label: The label/tag of the account to search for
        :raises AccountNotFound: When no account could be found with a tag/label matching ``label``
        :return dict acc: dict(account_index:int, balance:int, base_address, label:str, tag:str, unlocked_balance:int)
        """
        label = label.lower()
        with self.wallet(symbol) as w:  # type: MoneroRPC
            accs = w.get_accounts()
            for a in accs['subaddress_accounts']:
                if a['label'].lower() == label or a['tag'].lower() == label:
                    return a
        raise AccountNotFound(f"No monero account with the label '{label}' could be found.")

    @property
    def xmr_settings(self):
        return self.settings.get('XMR', self.setting_defaults)

    def account_id(self, symbol: str = 'XMR') -> int:
        """Get the default account ID/index for a given coin symbol"""
        # First check if we've cached the account ID for this symbol
        if symbol in self._account_ids:
            return self._account_ids[symbol]

        # Next in priority is the `account_id` setting
        s = self.settings[symbol]
        if not empty(s.get('account_id')):
            a_id = self._account_ids[symbol] = int(s.get('account_id'))
            log.debug("Using setting 'account_id' = '%s' for the monero account ID", a_id)
            return a_id

        # If `account` is set, then we search for an account with the label or tag matching `account`
        aname = s.get('account')
        if not empty(aname):
            log.debug("Looking up account label/tag '%s' to find account ID", aname)
            acc = self.find_account_label(label=aname, symbol=symbol)
            self._account_ids[symbol] = int(acc['account_index'])
            log.debug("Account ID for '%s' was: %s", aname, self._account_ids[symbol])
            return self._account_ids[symbol]

        log.warning("WARNING: Both settings 'account' and 'account_id' are empty. Falling back to account ID 0...")

        self._account_ids[symbol] = 0
        return self._account_ids[symbol]

    def get_address(self, address: str, symbol: str = 'XMR') -> dict:
        with self.wallet(symbol) as w:  # type: MoneroRPC
            account_id = self.account_id(symbol=symbol)
            _addresses = w.get_address(account_index=account_id)
            addresses: List[dict] = _addresses['addresses']
            for a in addresses:
                if a['address'] == address:
                    return a
            raise AccountNotFound(f'The address "{address}" could not be found.')

    def _rpc_settings(self, symbol: str) -> dict:
        """Generate a dict that can be passed via BitcoinRPC's kwargs using the passed symbol's settings"""
        s = self._prep_settings()[symbol]
        rs = {k: v for k, v in s if k in ['port', 'password']}
        rs += dict(username=s['user'], hostname=s['host'])
        return rs

    def _cast_settings(self, s: Dict[str, Any]):
        s['port'] = int(s['port'])

    def _get_rpcs(self) -> Dict[str, MoneroRPC]:
        """Returns a dict mapping coin symbols to their RPC objects"""
        rpcs = {}

        for sym, conn in self._prep_settings().items():
            rpcs[sym] = MoneroRPC(
                hostname=conn['host'],
                port=conn['port'],
                username=conn.get('user'),
                password=conn.get('password')
            )
        return rpcs



