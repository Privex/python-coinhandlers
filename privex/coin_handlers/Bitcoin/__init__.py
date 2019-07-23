"""
**Bitcoind-based Coin Handler**

This python module is a **Coin Handler** for Privex's CryptoToken Converter, designed to handle all required
functionality for both receiving and sending any cryptocurrency which has a coin daemon that has a JSONRPC API
backwards compatible with `bitcoind`.

It will automatically handle any :class:`payments.models.Coin` which has it's type set to ``bitcoind``

**Coin object settings**:

    For each coin you intend to use with this handler, you should configure it as such:

    =============   ==================================================================================================
    Coin Key        Description
    =============   ==================================================================================================
    coin_type       This should be set to ``Bitcoind RPC compatible crypto`` (db value: bitcoind)
    setting_host    The IP or hostname for the daemon. If not specified, defaults to 127.0.0.1 / localhost
    setting_port    The RPC port for the daemon. If not specified, defaults to 8332
    setting_user    The rpcuser for the daemon. Generally MUST be specified.
    setting_pass    The rpcpassword for the daemon. Generally MUST be specified
    setting_json    A JSON string for optional extra config (see below)
    =============   ==================================================================================================


    Extra JSON (Handler Custom) config options:

    - ``confirms_needed`` Default 0; Amount of confirmations needed before loading a TX
    - ``use_trusted`` Default: True; If enabled, TXs returned from the daemon with 'trusted':true will always be
      accepted at 0 confs regardless of ``confirms_needed``
    - ``string_amt`` Default: True; If true, when sending coins, a ``Decimal`` will be used (as a string). This can
      cause problems with older coins such as Dogecoin, so for older coins that need floats, set this to False.

**Django Settings**:

    If you'd rather not store the RPC details in the database, you may specify them in Django's settings.py.

    If a coin symbol is specified in ``settings.COIND_RPC`` they will be used exclusively, and any handler settings
    on the Coin object will be ignored.

    If a settings key isn't specified, the default is the same as shown for coin object settings.

    Example COIND_RPC Setting::

        COIND_RPC = {
          "BTC": {
              'user': 'bitcoinrpc',
              'password': 'SuperSecurePass',
              'host':     '127.0.0.1',
              'port':     8332,
              'confirms_needed': 0,
              'string_amt': True,
              'use_trusted': True
          }
        }


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
from typing import Dict, List
from privex.coin_handlers.Bitcoin.BitcoinLoader import BitcoinLoader
from privex.coin_handlers.Bitcoin.BitcoinManager import BitcoinManager
# from django.conf import settings

from privex.coin_handlers.Bitcoin.BitcoinMixin import BitcoinMixin
from privex.coin_handlers.base import Coin

log = logging.getLogger(__name__)

loaded = False

COIN_TYPE = 'bitcoind'
HANDLER_DESC = 'Bitcoind RPC compatible crypto'

HANDLER_TYPES = ((COIN_TYPE, HANDLER_DESC,),)

handler_settings = {}   # type: Dict[str, dict]
handler_coins = []      # type: List[Coin]


def setup(settings: Dict[str, dict], coins: List[Coin]):
    global handler_settings, handler_coins
    handler_settings = settings
    handler_coins = coins


def reload():
    """
    Reload's the ``provides`` property for the loader and manager from the DB.

    By default, as there are many coins that use a direct fork of bitcoind, our classes can provide for any
    :class:`models.Coin` by scanning for coins with the type ``bitcoind``. This saves us from hard coding
    specific coin symbols.
    """

    # Set loaded to True, so we aren't constantly reloading the ``provides``, only when we need to.
    global loaded
    loaded = True

    # Grab a simple list of coin symbols with the type COIN_TYPE to populate the provides lists.
    # provides = Coin.objects.filter(coin_type=COIN_TYPE).values_list('symbol', flat=True)
    provides = [coin.symbol for coin in handler_coins]
    BitcoinLoader.provides = provides
    BitcoinManager.provides = provides
    # Since the handler is re-loading, we wipe the settings cache to ensure stale connection details aren't used.
    BitcoinMixin._settings = {}


# Only run the initialisation code once.
# After the first run, reload() will be called only when there's a change by the coin handler system
if not loaded:
    reload()

exports = {
    "loader": BitcoinLoader,
    "manager": BitcoinManager
}
