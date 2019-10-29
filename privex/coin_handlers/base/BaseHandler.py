from os import getenv as env
from abc import ABC, abstractmethod
from typing import Dict, Any

from privex.coin_handlers.base.objects import Coin


class BaseHandler(ABC):
    allsettings: Dict[str, Any]
    
    def __init__(self, *args, settings: Dict[str, dict] = None, **kwargs):
        self.allsettings = {} if not settings else settings
    
    @classmethod
    def find_obj_key(cls, key: str, obj: Any):
        """
        Attempts to find a key / attribute on an object in various forms:
        
          * Scan ``obj`` for the original/upper/lower cased attribute ``key``
          * Scan ``obj`` for the original/upper/lower cased key ``key``
          * If ``obj`` is a :class:`.Coin` instance:
              * Scan ``obj.settings`` for the original/upper/lower cased attribute / key ``key``
              * Scan ``obj.settings['json']`` for the original/upper/lower cased attribute / key ``key``

        Example::
            
            >>> x = {'hello': 'world'}
            >>> class Y:
            ...     EXAMPLE = 'hello'
            ...
            >>> BaseHandler.find_obj_key('HEllO', x)
            'world'
            >>> BaseHandler.find_obj_key('example', Y)
            'hello'

        :param str key: A key / attribute to attempt to find on ``obj``
        :param Any obj: Any object which supports querying by attribute or item (key)
        :return Any value: The value of the located key/attribute
        """
        if hasattr(obj, key): return getattr(obj, key)
        if hasattr(obj, key.lower()): return getattr(obj, key.lower())
        if hasattr(obj, key.upper()): return getattr(obj, key.upper())
        
        if key in obj: return obj[key]
        if key.upper() in obj: return obj[key.upper()]
        if key.lower() in obj: return obj[key.lower()]

        if isinstance(obj, Coin):
            try:
                val = cls.find_obj_key(key=key, obj=obj.settings)
                return val
            except KeyError:
                val = cls.find_obj_key(key=key, obj=obj.settings['json'])
                return val

        raise KeyError(f'Could not find key {key} in object: {obj}')
    
    def get_setting(self, symbol: str, key: str, default=None):
        # First, environment variable settings take precedence if they exist.
        setting_key = f'COIN_{symbol.upper()}_{key.upper()}'
        _env = env(setting_key)
        if _env is not None:
            return _env

        # Next, check the settings dictionary that was passed to the constructor
        s = self.allsettings.get(symbol.upper(), {})
        if key in s:
            return s[key]

        # If all else fails, check self.coin if it's set on the class calling this method
        if hasattr(self, 'coin'):
            try:
                val = self.find_obj_key(key, self.coin)
                return val
            except (KeyError, AttributeError):
                pass

        # And finally, check self.coins[symbol] if we actually have .coins on this instance.
        if hasattr(self, 'coins'):
            c = self.coins.get(symbol, {})
            try:
                val = self.find_obj_key(key, c)
                return val
            except (KeyError, AttributeError):
                pass
        
        # Otherwise, we give up and return the ``default``.
        return default

    @property
    def provides(self) -> list:
        """
        A list of token/coin symbols in uppercase that this loader supports e.g::

            provides = ["LTC", "BTC", "BCH"]
        
        """
        return []

