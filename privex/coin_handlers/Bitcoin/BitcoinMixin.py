"""
**Copyright**::

    +===================================================+
    |                 © 2019 Privex Inc.                |
    |               https://www.privex.io               |
    +===================================================+
    |                                                   |
    |        CryptoToken Converter                      |
    |                                                   |
    |        Core Developer(s):                         |
    |                                                   |
    |          (+)  Chris (@someguy123) [Privex]        |
    |                                                   |
    +===================================================+

"""
import logging
from typing import List, Dict

# from django.conf import settings
from privex.jsonrpc import BitcoinRPC

from privex.coin_handlers.base.BaseHandler import BaseHandler
from privex.coin_handlers.base.objects import Coin
from privex.helpers import empty

log = logging.getLogger(__name__)


class BitcoinMixin(BaseHandler):
    """
    BitcoinMixin - shared code used by both :class:`Bitcoin.BitcoinLoader` and :class:`Bitcoin.BitcoinManager`

    **Copyright**::

        +===================================================+
        |                 © 2019 Privex Inc.                |
        |               https://www.privex.io               |
        +===================================================+
        |                                                   |
        |        CryptoToken Converter                      |
        |                                                   |
        |        Core Developer(s):                         |
        |                                                   |
        |          (+)  Chris (@someguy123) [Privex]        |
        |                                                   |
        +===================================================+

    """

    _settings = {}  # type: Dict[str, dict]

    # If a setting isn't specified, use these.
    _bc_defaults = dict(
        host='127.0.0.1', port=8332, user=None, password=None,
        confirms_needed=0, use_trusted=True, string_amt=True
    )

    @property
    def all_coins(self) -> Dict[str, Coin]:
        """
        Since this is a Mixin, it may be self.coin: Coin, or self.coins: List[Coin].
        This property detects whether we have a single coin, or multiple, and returns them as a dict.

        :return dict coins: A dict<str,Coin> of supported coins, mapped by symbol
        """
        if hasattr(self, 'coins'):
            return dict(self.coins)
        elif hasattr(self, 'coin'):
            return {self.coin.symbol_id: self.coin}
        raise Exception('Cannot load settings as neither self.coin nor self.coins exists...')

    def _prep_settings(self, reset: bool =False) -> Dict[str, dict]:
        """
        Loads and caches coin daemon settings from both :class:`payments.models.Coin` objects, and from
        ``settings.COIND_RPC`` (if it's defined).

        :param bool reset:  Default: False; if true - force refresh coin settings into self._settings
        :return dict _settings: {host:str, port:int, user:str, password:str, confirms_needed:int, use_trusted:bool}
        """
        # If _settings isn't empty, and we aren't forcing a refresh, don't bother re-loading the coin settings
        if len(self._settings) > 0 and not reset:
            return self._settings

        s = {}   # Temporary settings dict

        # Load handler settings from Coin objects, combine the JSON dict into our settings dict
        # log.debug('Loading Bitcoind handler settings from Coin objects')
        for sym, c in self.all_coins.items():
            sc = c.settings     # {host,port,user,password,json}
            s[sym] = {k: v for k, v in sc.items() if k != 'json'}    # Don't include the 'json' key
            s[sym] = {**s[sym], **sc['json']}                        # Merge contents of 'json' into our settings

        # log.debug('Loading Bitcoind handler settings from settings.COIND_RPC (if it exists)')
        # If COIND_RPC has been set in settings.py, they take precedence over database-level settings.
        settings = self.allsettings
        if 'COIND_RPC' in settings:
            for symbol, conn in settings['COIND_RPC'].items():
                s[symbol] = dict(conn)

        # Finally, fill in any gaps with the default settings, and cast non-string settings to their correct type.
        self._clean_settings(s)

        # Store settings to the class attribute, and return them.
        self._settings = s
        return self._settings

    def _clean_settings(self, d_settings: Dict[str, dict]) -> Dict[str, dict]:
        """
        Clean up ``d_settings`` by setting any missing/empty settings to default values, and cast non-string settings
        to the correct types.

        :param dict d_settings: The dict<str,dict> mapping symbol->settings to clean up
        :return dict d_settings: The cleaned dictionary. Only needed if you passed a deep-copy for d_settings, as the
                                 passed dict will be altered in-place unless it's a copy.
        """

        defs = self._bc_defaults
        # Loop over each symbol and settings dict we were passed
        for sym, conn in d_settings.items():  # coin symbol : str, settings: dict
            # log.debug("Cleaning settings for symbol %s", sym)
            z = d_settings[sym]   # Pointer to the settings dict for this symbol
            # Loop over our default settings, compare to the user's settings
            for def_key, def_val in defs.items():  # settings key : str, settings value : any
                # Check if required setting key exists in user's settings
                if def_key in z and not empty(z[def_key]):
                    continue
                # Setting doesn't exist, or was empty. Update user's setting to our default.
                z[def_key] = def_val
            # Cast settings keys to avoid casting errors
            z['confirms_needed'] = int(z['confirms_needed'])
            z['port'] = int(z['port'])
            z['use_trusted'] = z['use_trusted'] in [True, 'true', 'True', 'TRUE', 1, 'yes']
            z['string_amt'] = z['string_amt'] in [True, 'true', 'True', 'TRUE', 1, 'yes']
        return d_settings

    def _rpc_settings(self, symbol: str) -> dict:
        """Generate a dict that can be passed via BitcoinRPC's kwargs using the passed symbol's settings"""
        s = self._prep_settings()[symbol]
        rs = {k:v for k,v in s if k in ['port','password']}
        rs += dict(username=s['user'], hostname=s['host'])
        return rs

    def _get_rpcs(self) -> Dict[str, BitcoinRPC]:
        """Returns a dict mapping coin symbols to their RPC objects"""
        rpcs = {}

        for sym, conn in self._prep_settings().items():
            rpcs[sym] = BitcoinRPC(
                hostname=conn['host'],
                port=conn['port'],
                username=conn.get('user'),
                password=conn.get('password')
            )
        return rpcs
