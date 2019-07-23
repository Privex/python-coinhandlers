import json
import logging
from datetime import datetime
from decimal import Decimal

from privex.helpers import is_true

log = logging.getLogger(__name__)


class Coin(object):
    """
    :ivar str symbol:        Unique symbol ID used by implementing application
    :ivar str symbol_id:     Native symbol used on the network where this Coin object is being passed to
    :ivar str coin_type:     This should be a short code such as ``bitcoind` which identifies the matching coin handler
    :ivar str our_account:   If this coin is account based (e.g. Steem/EOS), this will contain the send/receive account.
    :ivar bool can_issue:    True if we're able to issue this coin, False if not.

    **The below setting_ options may have different formats and usages for different handlers:**

    :ivar str setting_host:    *Usually* refers to the hostname/IP of the RPC node to use.
    :ivar int setting_port:    *Usually* refers to the port the RPC is running on
    :ivar str setting_user:    *Usually* refers to the username required to connect to the RPC
    :ivar str setting_pass:    *Usually* refers to the password required to connect to the RPC
    :ivar str setting_json:    Additional custom settings in JSON format to be used by the coin handler.
    """
    base_keys = [
        'symbol', 'symbol_id', 'coin_type', 'our_account', 'can_issue',
        'setting_host', 'setting_port', 'setting_user', 'setting_pass', 'setting_json'
    ]

    def __init__(self, *args, **kwargs):
        base_keys = self.base_keys
        for k in base_keys:
            setattr(self, k, kwargs.get(k))
        self.can_issue = is_true(kwargs.get('can_issue', False))
        self.setting_json = kwargs.get('setting_json', '{}')

        self.dict_keys = set(list(kwargs.keys()) + base_keys)
        for k,v in kwargs.items():
            if not hasattr(self, k):
                setattr(self, k, v)
        self.raw_data = kwargs

    def __iter__(self):
        for k in self.dict_keys: yield (k, getattr(self, k),)

    def __getitem__(self, key):
        """
        When the instance is accessed like a dict, try returning the matching attribute.
        If the attribute doesn't exist, or the key is an integer, try and pull it from raw_data
        """
        if hasattr(self, key): return getattr(self, key)
        raise KeyError(key)

    def __repr__(self):
        return str(dict(self))

    @property
    def settings(self) -> dict:
        """
        Small helper property for quickly accessing the setting_xxxx fields, while also decoding the custom json
        field into a dictionary/list

        :return: dict(host:str, port:str, user:str, password:str, json:dict/list)
        """
        try:
            j = json.loads(self.setting_json)
        except:
            log.exception("Couldn't decode JSON for coin %s, falling back to {}", str(self))
            j = {}

        return dict(
            host=self.setting_host,
            port=self.setting_port,
            user=self.setting_user,
            password=self.setting_pass,
            json=j
        )


class Deposit(object):
    """

    """

    dict_keys = {'coin', 'tx_timestamp', 'amount', 'txid', 'vout', 'address', 'memo'}

    def __init__(self, coin: str, tx_timestamp: datetime, amount: Decimal, txid=None, vout: int = 0,
                 address=None, memo=None, **kwargs):
        for k, v in kwargs.items():
            if not hasattr(self, k):
                self.dict_keys.add(k)
                setattr(self, k, v)
        self.coin = coin
        self.tx_timestamp = tx_timestamp
        if type(amount) is not Decimal:
            amount = Decimal(amount)
        self.amount = amount
        self.txid = txid
        self.vout = vout
        self.address = address
        self.memo = memo

    def __iter__(self):
        for k in self.dict_keys:
            yield (k, getattr(self, k),)

    def __getitem__(self, key):
        """
        When the instance is accessed like a dict, try returning the matching attribute.
        If the attribute doesn't exist, or the key is an integer, try and pull it from raw_data
        """
        if hasattr(self, key):
            return getattr(self, key)
        raise KeyError(key)

    def __repr__(self):
        return f"<Deposit coin='{self.coin}' amount='{self.amount}' address='{self.address}'>"

    def __str__(self):
        return self.__repr__()
