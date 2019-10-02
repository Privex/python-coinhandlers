"""
**Golos Coin Handler**

This python module is a **Coin Handler** for Privex's CryptoToken Converter, designed to handle all required
functionality for both receiving and sending tokens on the **Golos** network.

It will automatically handle any :class:`payments.models.Coin` which has it's type set to ``golos``

**Key Store**:

This coin handler requires a Key Store to be configured.

See :py:mod:`privex.coin_handlers.KeyStore` for full details.

Basic setup:

    >>> from privex.coin_handlers import MemoryKeyStore, set_key_store, get_key_store
    >>> set_key_store(MemoryKeyStore()) # Set the global keystore to use the MemoryKeyStore.
    >>> store = get_key_store()         # Obtain the global key store instance
    >>> store.set(                      # Add a key to the global key store, for use by the Golos handler
    ...     network='golos', account='someguy123', private_key='5Jq19TeeVmGrBFnu32oxfxQMiipnSCKmwW7fZGUVLAoqsKJ9JwP',
    ...     key_type='active',
    ... )


**Coin object settings**:

    For each :class:`payments.models.Coin` you intend to use with this handler, you should configure it as such:

    =============   ==================================================================================================
    Coin Key        Description
    =============   ==================================================================================================
    coin_type       This should be set to ``Golos Network (or compatible fork)`` (db value: golos)
    our_account     This should be set to the username of the account you want to use for receiving/sending
    setting_json    A JSON string for optional extra config (see below)
    =============   ==================================================================================================

    Extra JSON (Handler Custom) config options:

    - ``rpcs`` - A JSON list<str> of RPC nodes to use, with a full HTTP/HTTPS URL. If this is not specified, Beem
      will automatically try to use the best available RPC node for the Steem network.

    Example JSON custom config::

        {
            "rpcs": [
                "https://steemd.privex.io",
                "https://api.steemit.com",
                "https://api.steem.house"
            ]
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

from privex.coin_handlers.Golos.GolosLoader import GolosLoader
from privex.coin_handlers.Golos.GolosManager import GolosManager
from privex.coin_handlers.Golos.GolosMixin import GolosMixin

from privex.coin_handlers.base import Coin

log = logging.getLogger(__name__)

loaded = False

COIN_TYPE = 'golos'
HANDLER_DESC = 'Golos Network (or compatible fork)'

HANDLER_TYPES = ((COIN_TYPE, HANDLER_DESC,),)

handler_settings = {}  # type: Dict[str, dict]
handler_coins = [
    Coin(symbol='GOLOS', symbol_id='GOLOS'),
    Coin(symbol='GBG', symbol_id='GBG'),
]  # type: List[Coin]


def setup(settings: Dict[str, dict], coins: List[Coin]):
    global handler_settings, handler_coins
    handler_settings = settings
    handler_coins = coins


def reload():
    """
    Reload's the ``provides`` property for the loader and manager from the DB.

    By default, as there are many coins that use a direct fork of monero, our classes can provide for any
    :class:`models.Coin` by scanning for coins with the type ``monero``. This saves us from hard coding
    specific coin symbols.
    """
    
    # Set loaded to True, so we aren't constantly reloading the ``provides``, only when we need to.
    global loaded
    loaded = True
    
    # Grab a simple list of coin symbols with the type COIN_TYPE to populate the provides lists.
    # provides = Coin.objects.filter(coin_type=COIN_TYPE).values_list('symbol', flat=True)
    provides = [coin.symbol for coin in handler_coins]
    GolosLoader.provides = provides
    GolosManager.provides = provides
    # Since the handler is re-loading, we wipe the settings cache to ensure stale connection details aren't used.
    GolosMixin._settings = {}


# Only run the initialisation code once.
# After the first run, reload() will be called only when there's a change by the coin handler system
if not loaded:
    reload()

exports = {
    "loader":  GolosLoader,
    "manager": GolosManager,
}
