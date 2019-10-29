import json
import attr
import logging
from datetime import datetime
from decimal import Decimal
from typing import List

from dateutil.parser import parse
from privex.helpers import is_true

log = logging.getLogger(__name__)


def convert_datetime(d):
    if type(d) in [str, int]:
        d = parse(d)
    if type(d) is not datetime:
        raise ValueError('Timestamp must be either a datetime object, or an ISO8601 string...')
    return d


class DictLike(object):
    """
    Allows child classes to work like ``dict``'s
    """
    dict_keys: List[str]
    
    def get(self, key, default=None):
        try:
            return self[key]
        except KeyError:
            return default
    
    def __iter__(self):
        """Handle casting via ``dict(myclass)``"""
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

    def __setitem__(self, key, value):
        return setattr(self, key, value)


@attr.s
class AttribDictable:
    def get(self, key, default=None):
        try:
            return self[key]
        except KeyError:
            return default
    
    def __iter__(self):
        """Handle casting via ``dict(myclass)``"""
        for k, v in attr.asdict(self).items():
            yield k, v

    def __getitem__(self, key):
        """
        When the instance is accessed like a dict, try returning the matching attribute.
        If the attribute doesn't exist, or the key is an integer, try and pull it from raw_data
        """
        if hasattr(self, key):
            return getattr(self, key)
        raise KeyError(key)

    def __setitem__(self, key, value):
        return setattr(self, key, value)


@attr.s
class Coin(AttribDictable):
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
        'setting_host', 'setting_port', 'setting_user', 'setting_pass', 'setting_json',
        'display_name',
    ]
    
    symbol = attr.ib(type=str)
    symbol_id = attr.ib(type=str)
    coin_type = attr.ib(default=None, type=str)
    our_account = attr.ib(default=None, type=str)
    can_issue = attr.ib(default=False, type=bool)
    display_name = attr.ib(type=str)
    
    setting_host = attr.ib(default=None, type=str)
    setting_port = attr.ib(default=None, type=int)
    
    setting_user = attr.ib(default=None, type=str)
    setting_pass = attr.ib(default=None, type=str)
    setting_json = attr.ib(default='{}', type=str)
    
    @symbol_id.default
    def _default_symbol_id(self):
        return self.symbol
    
    @display_name.default
    def _default_display_name(self):
        return self.symbol
    
    # def __repr__(self):
    #     return str(dict(self))

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


@attr.s
class Deposit(AttribDictable):
    """
    Represents a generic Deposit on any coin
    """

    dict_keys = {'coin', 'tx_timestamp', 'amount', 'txid', 'vout', 'address', 'memo', 'from_account', 'to_account'}

    coin = attr.ib(type=str)
    tx_timestamp = attr.ib(type=datetime, converter=convert_datetime)
    amount = attr.ib(type=Decimal, converter=Decimal)
    txid = attr.ib(default=None, type=str)
    vout = attr.ib(default=0, type=int)
    address = attr.ib(default=None, type=str)
    memo = attr.ib(default=None, type=str)
    from_account = attr.ib(default=None, type=str)
    to_account = attr.ib(default=None, type=str)

    # def __init__(self, coin: str, tx_timestamp: datetime, amount: Decimal, txid=None, vout: int = 0,
    #              address=None, memo=None, from_account=None, to_account=None, **kwargs):
    #     for k, v in kwargs.items():
    #         if not hasattr(self, k):
    #             self.dict_keys.add(k)
    #             setattr(self, k, v)
    #     self.coin = coin
    #     self.tx_timestamp = tx_timestamp
    #     if type(amount) is not Decimal:
    #         amount = Decimal(amount)
    #     self.amount = amount
    #     self.txid, self.vout, self.memo = txid, vout, memo
    #     self.address, self.from_account, self.to_account = address, from_account, to_account

