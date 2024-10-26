"""
Initialisation module for Privex's Cryptocurrency Handlers.

To use the functions in this file such as :py:func:`get_manager` , :py:func:`has_loader` etc. you'll first need to
configure the module from your application, like so:

    >>> import privex.coin_handlers as ch
    >>> from privex.coin_handlers import Coin
    >>>
    >>> # Select the coin handlers you would like to use, and add Coin objects to their dict key ``coins``
    >>> ch.COIN_HANDLERS['Steem'] = {
    ...    'coins': [
    ...         Coin(symbol='STEEM', symbol_id='STEEM'),
    ...         Coin(symbol='SBD', symbol_id='SBD'),
    ...     ]
    ... }
    >>> # Add any settings required for the coin handlers you're using
    >>> ch.HANDLER_SETTINGS['COIND_RPC']['BTC'] = {'user': 'bitcoinrpc', 'pass': 'SomeSecret', 'port': 8332}
    >>> ch.reload_handlers()   # After making changes to the settings, it's best to force a reload of the handlers.


Now that you've configured your handlers appropriately, you can easily access managers/loaders simply by querying
a coin symbol, like so:

    >>> from privex.coin_handlers import get_loader, get_manager
    >>> loader = get_loader('SBD')
    # <privex.coin_handlers.Steem.SteemLoader.SteemLoader object at 0x10ac0f160>
    >>> manager = get_manager('STEEM')
    # <privex.coin_handlers.Steem.SteemLoader.SteemLoader object at 0x10ac0f160>
    >>> manager.get_deposit()
    ('account', 'privex',)

If the coin handlers aren't yet loaded, ``get_loader``(s) / ``get_manager`` will automatically call ``reload_handlers``


**Copyright**::

    +===================================================+
    |                 © 2019 Privex Inc.                |
    |               https://www.privex.io               |
    +===================================================+
    |                                                   |
    |        Python Cryptocurrency Handlers             |
    |        License: X11/MIT                           |
    |                                                   |
    |        Core Developer(s):                         |
    |                                                   |
    |          (+)  Chris (@someguy123) [Privex]        |
    |                                                   |
    +===================================================+


Python Cryptocurrency Handlers - Various classes for handling sending/receiving cryptocurrencies
Copyright (c) 2019    Privex Inc. ( https://www.privex.io )

Permission is hereby granted, free of charge, to any person obtaining a copy of this software and associated documentation 
files (the "Software"), to deal in the Software without restriction, including without limitation the rights to use, copy, 
modify, merge, publish, distribute, sublicense, and/or sell copies of the Software, and to permit persons to whom the 
Software is furnished to do so, subject to the following conditions:

The above copyright notice and this permission notice shall be included in all copies or substantial portions of 
the Software.

THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR IMPLIED, INCLUDING BUT NOT LIMITED TO THE 
WARRANTIES OF MERCHANTABILITY, FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE AUTHORS 
OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR 
OTHERWISE, ARISING FROM, OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE SOFTWARE.

Except as contained in this notice, the name(s) of the above copyright holders shall not be used in advertising or 
otherwise to promote the sale, use or other dealings in this Software without prior written authorization.
"""
import logging
import sys
from typing import Dict, List, Union, Any, Tuple
from importlib import import_module
from privex.helpers import is_false
from privex.coin_handlers.base import BaseLoader, BaseManager, BatchLoader, Coin, Deposit, decorators, \
    exceptions, retry_on_err, SettingsMixin
from privex.coin_handlers.KeyStore import KeyStore, KeyPair, MemoryKeyStore, get_key_store, set_key_store
from privex.coin_handlers.Bitcoin import BitcoinLoader, BitcoinManager, BitcoinMixin
from privex.coin_handlers.Monero import MoneroLoader, MoneroManager, MoneroMixin

name = 'coin_handlers'

VERSION = '1.4.2'

# If the privex.coin_handlers logger has no handlers, assume it hasn't been configured and set up a console logger
# for any logs >=WARNING
log = _l = logging.getLogger(__name__)
if len(_l.handlers) == 0:
    _handler = logging.StreamHandler(sys.stdout)
    _handler.setFormatter(logging.Formatter('%(asctime)s %(name)-12s %(levelname)-8s %(message)s'))
    _handler.setLevel(logging.WARNING)
    _l.setLevel(logging.WARNING)
    _l.addHandler(_handler)

try:
    from privex.coin_handlers.KeyStore import DjangoKeyStore
except ImportError as e:
    log.debug('privex.coin_handlers __init__ failed to import DjangoKeyStore: %s', str(e))


handlers = {}    # type: Dict[ str, Dict[str, List[Union[BaseLoader, BaseManager]] ] ]
"""
A dictionary of coin symbols, containing instantiated managers (BaseManager) and loaders (BaseLoader)

Example layout::

    handlers = {
        'ENG': {
            'loaders':  [ SteemEngineLoader, ],
            'managers': [ SteemEngineLoader, ],
        },
        'SGTK': {
            'loaders':  [ SteemEngineLoader, ],
            'managers': [ SteemEngineLoader, ],
        },
    }

"""

handlers_loaded = False
"""Used to track whether the Coin Handlers have been initialized, so reload_handlers can be auto-called."""

CH_BASE = 'privex.coin_handlers'
"""Base module path to where the coin handler modules are located. E.g. payments.coin_handlers"""

HANDLER_SETTINGS = {
    'COIND_RPC': {
        'BTC': {    # Per-coin dict settings. Note: some opts may only work via COIN_HANDLERS[x]['kwargs']
            # 'host': '127.0.0.1', 'port': 8332
        }
    }
}    # type: Dict[str, Dict[str, dict]]
"""
The ``HANDLER_SETTINGS`` dictionary is passed to all handler Loader's and Manager's as the first argument.

It's recommended to use :py:func:`.configure_coin` instead of manipulating this by hand.

Generally it should be a dictionary containing ``COIND_RPC`` , which then contains keys for each coin symbol, mapped
to a dict with settings for that coin.

Example::

    >>> HANDLER_SETTINGS = dict(
    ...     COIND_RPC=dict(
    ...         BTC=dict(user='bitcoinrpc', host='127.0.0.1')
    ...     )
    ... )


"""

COIN_MAP = {
    'STEEM': Coin(symbol='STEEM', symbol_id='STEEM'),
    'SBD': Coin(symbol='SBD', symbol_id='SBD'),
    'BTC': Coin(symbol='BTC', symbol_id='BTC'),
    'XMR': Coin(symbol='XMR', symbol_id='XMR'),
    'GOLOS': Coin(symbol='GOLOS', symbol_id='GOLOS'),
    'GBG': Coin(symbol='GBG', symbol_id='GBG'),
}


COIN_HANDLERS = {
    'Bitcoin': {
        'enabled': False,
        'coins': [        # A list of :class:`base.objects.Coin` instances that this handler is responsible for.
            # Coin(setting_user='bitcoinrpc', setting_pass='SomeSecurePass', symbol='BTC', symbol_id='BTC'),
        ],
        'kwargs': {}      # A dictionary of additional keyword arguments to pass to the handler
    },
    'Steem': {
        'enabled': False,
        'coins': [
            COIN_MAP['STEEM'], COIN_MAP['SBD'],
        ],
        'kwargs': {}
    },
    'Monero': {
        'enabled': False,
        'coins': [
            COIN_MAP['XMR'],
        ],
        'kwargs': {}
    },
    'Golos': {
        'enabled': False,
        'coins':   [
            COIN_MAP['GOLOS'],
            COIN_MAP['GBG'],
        ],
        'kwargs':  {}
    }
}   # type: Dict[str, Dict[str, Any]]
"""
The ``COIN_HANDLERS`` dictionary represents a key:value map, where the keys are the exact folder names of the
coin handler modules, and the values are a ``dict`` containing configuration for the coin handler, such as:
 
 - ``enabled`` (bool) whether the handler should be loaded (default: True if not specified)
 - ``coins`` (List[Coin]) What :class:`objects.Coin` 's this handler is responsible for
 - ``kwargs`` Any additional keyword args to pass to the handler when it's constructed.

Example for :py:mod:`.Bitcoin` :

.. code-block:: python

    COIN_HANDLERS = {
        'Bitcoin': {
            'enabled': True,
            'coins': [Coin(setting_user='bitcoinrpc', setting_pass='SomeSecurePass', symbol='BTC', symbol_id='BTC')],
            'kwargs': {}
        }
    }


"""

log = logging.getLogger(__name__)


def _handler(handler: str) -> dict:
    """
    Returns a handler config from ``COIN_HANDLERS``.

    Automatically creates non-existent handler keys, as well as ensuring that the ``coins`` sub-key exists.
    """
    if handler not in COIN_HANDLERS:
        COIN_HANDLERS[handler] = dict(enabled=True, coins=[])
    ch = COIN_HANDLERS[handler]
    if 'coins' not in ch:
        ch['coins'] = []
    return ch


def disable_handler(*handler: str):
    """
    Disable one or more Coin Handlers with given names (CASE SenSITiVE)
    """
    for h in handler:
        if h in COIN_HANDLERS:
            COIN_HANDLERS[h]['enabled'] = False


def enable_handler(*handler: str):
    """
    Enable one or more Coin Handlers with given names (CASE SenSITiVE)

    :raises exceptions.HandlerNotFound: When a given handler name doesn't exist.
    """
    for h in handler:
        if h not in COIN_HANDLERS:
            raise exceptions.HandlerNotFound(f"The handler '{h}' does not exist! Cannot enable it.")
        COIN_HANDLERS[h]['enabled'] = True


def configure_coin(symbol: str, **config_opts):
    """
    Set configuration options for a given coin symbol - only overwrites the specific keys passed, so can be
    called multiple times for a coin.

    If the coin doesn't exist in ``HANDLER_SETTINGS['COIND_RPC']`` then it will be created.

    Example:

        >>> configure_coin('BTC', host='127.0.0.1', user='bitcoinrpc', password='mypassword')
        >>> configure_coin('BTC', confirms_needed=1)


    :param str symbol: The coin symbol to configure, e.g. ``BTC``
    :param Any config_opts: Keyword args for each setting you want to adjust
    :return dict coin_settings: A ``dict`` containing the current settings for the coin
    """
    symbol = symbol.upper()

    c_rpc = HANDLER_SETTINGS['COIND_RPC']
    if symbol not in c_rpc:
        c_rpc[symbol] = {}
    c_rpc[symbol] = {**c_rpc[symbol], **config_opts}
    
    if symbol in COIN_MAP:
        for k, v in config_opts.items():
            if hasattr(COIN_MAP[symbol], k):
                setattr(COIN_MAP[symbol], k, v)
    
    return c_rpc[symbol]


def configure_handler(handler: str, **config_opts):
    """
    Set configuration options on a handler

    Example:

        >>> configure_handler('Steem', enabled=True, coins=[], kwargs=dict(some='extra_kwargs'))


    :param str handler: A handler name as a string, e.g. ``Bitcoin``
    :param config_opts: Configuration options to set, as keyword args
    """
    COIN_HANDLERS[handler] = {**COIN_HANDLERS[handler], **config_opts}


def handler_has_coin(handler: str, symbol: str) -> bool:
    """Returns ``True`` if the given ``symbol`` is in a handler's coin list"""
    chc = _handler(handler)['coins']
    for coin in chc:
        if coin.symbol.upper() == symbol.upper():
            return True
    return False


def add_handler_coin(handler: str, coin: Union[Coin, str]):
    """
    Add a :class:`.Coin` to a handler's enabled coin list if it's not already there.

    Example:

        >>> add_handler_coin('Bitcoin', Coin(symbol='DOGE', symbol_id='DOGE'))
        >>> # Or if the coin exists in the COIN_MAP
        >>> add_handler_coin('Bitcoin', 'BTC')

    :param str handler:   The name of a handler, e.g. ``Bitcoin``
    :param Coin|str coin: Either a :class:`.Coin` object, or a string symbol which exists in :py:attr:`.COIN_MAP`
    :return:
    """
    if type(coin) is str:
        coin = coin.upper()
        if coin not in COIN_MAP:
            raise exceptions.TokenNotFound(f'Requested symbol "{coin}" not found in COIN_MAP')
        coin = COIN_MAP[coin]
    sym = coin.symbol
    if handler_has_coin(handler, sym):
        return False

    ch = _handler(handler)
    ch['coins'].append(coin)
    if coin.symbol not in COIN_MAP:
        COIN_MAP[coin.symbol] = coin
    return True


def get_loaders(symbol: str = None) -> Union[Tuple[str, List[BaseLoader]], List[BaseLoader]]:
    """
    Get all loader's, or all loader's for a certain coin

    :param symbol: The coin symbol to get all loaders for (uppercase)
    :return list: If symbol not specified, a list of tuples (symbol, list<BaseLoader>,)
    :return list: If symbol IS specified, a list of instantiated :class:`base.BaseLoader`'s
    """
    if not handlers_loaded: reload_handlers()
    return [(s, data['loaders'],) for s, data in handlers.items()] if symbol is None else handlers[symbol]['loaders']


def has_manager(symbol: str) -> bool:
    """Helper function - does this symbol have a manager class?"""
    if not handlers_loaded: reload_handlers()
    return symbol.upper() in handlers and len(handlers[symbol].get('managers', [])) > 0


def has_loader(symbol: str) -> bool:
    """Helper function - does this symbol have a loader class?"""
    if not handlers_loaded: reload_handlers()
    return symbol.upper() in handlers and len(handlers[symbol].get('loaders', [])) > 0


def get_managers(symbol: str = None) -> Union[Tuple[str, List[BaseManager]], List[BaseManager]]:
    """
    Get all manager's, or all manager's for a certain coin

    :param symbol: The coin symbol to get all managers for (uppercase)
    :return list: If symbol not specified, a list of tuples (symbol, list<BaseManager>,)
    :return list: If symbol IS specified, a list of instantiated :class:`base.BaseManager`'s
    """
    if not handlers_loaded: reload_handlers()
    return [(s, data['managers'],) for s, data in handlers.items()] if symbol is None else handlers[symbol]['managers']


def get_manager(symbol: str) -> BaseManager:
    """
    For some use-cases, you may want to just grab the first manager that supports this coin.

        >>> m = get_manager('ENG')
        >>> m.send(amount=Decimal(1), from_address='someguy123', address='privex')

    :param symbol:         The coin symbol to get the manager for (uppercase)
    :return BaseManager:   An instance implementing :class:`base.BaseManager`
    """
    if not handlers_loaded: reload_handlers()
    return handlers[symbol]['managers'][0]


def get_loader(symbol: str) -> BaseLoader:
    """
    For some use-cases, you may want to just grab the first loader that supports this coin.

        >>> m = get_loader('ENG')
        >>> m.send(amount=Decimal(1), from_address='someguy123', address='privex')

    :param symbol:        The coin symbol to get the loader for (uppercase)
    :return BaseLoader:   An instance implementing :class:`base.BaseLoader`
    """
    if not handlers_loaded: reload_handlers()
    return handlers[symbol]['loaders'][0]


def add_handler(handler, handler_name, handler_type):
    """
    Internal function. Used by :py:func:`.reload_handlers` to initialise handlers for usage.

    :param handler: An un-instantiated handler class based on :class:`.BaseLoader` / :class:`.BaseManager`
    :param str handler_name: The unique name of the handler, e.g. ``Bitcoin``
    :param str handler_type: The type of handler class it is, either ``managers`` or ``loaders``
    """
    global handlers
    # `handler` is an un-instantiated class extending BaseLoader / BaseManager
    for coin in COIN_HANDLERS[handler_name]['coins']:
        sym = coin.symbol
        if sym not in handlers:
            handlers[sym] = dict(loaders=[], managers=[])
        kwargs = dict(coin=coin) if handler_type == 'managers' else dict(coins=[coin])
        kwargs = {**kwargs, **COIN_HANDLERS[handler_name].get('kwargs', {})}
        h = handler(settings=HANDLER_SETTINGS, **kwargs)
        handlers[sym][handler_type].append(h)


def reload_handlers():
    """
    Resets `handler` to an empty dict, then loads all ``COIN_HANDLER`` classes into the dictionary ``handlers``
    using ``CH_BASE`` as the base module path to load from
    """
    global handlers, handlers_loaded
    handlers = {}
    log.debug('--- Starting reload_handlers() ---')

    for ch, ch_data in COIN_HANDLERS.items():
        if is_false(ch_data.get('enabled', True)):
            log.debug("Skipping coin handler %s as it's disabled.", ch)
            continue
        try:
            mod_path = '.'.join([CH_BASE, ch])
            log.debug('Loading coin handler %s', mod_path)
            i = import_module(mod_path)
            # To avoid a handler's initialising code being ran every time the module is imported, a handler's init file
            # can define a reload() function, which is only ran the first time the module is loaded.
            # If reload_handlers() has been called, then we need to make sure we force reload those with a reload func.
            if handlers_loaded and hasattr(i, 'reload'):
                i.reload()
            ex = i.exports
            if 'loader' in ex:
                log.debug('Adding loader class for %s', ch)
                add_handler(ex['loader'], ch, 'loaders')
            if 'manager' in ex:
                log.debug('Adding manager class for %s', ch)
                add_handler(ex['manager'], ch, 'managers')
        except:
            log.debug('COIN_HANDLERS %s', COIN_HANDLERS)
            log.debug('COIN_MAP %s', COIN_MAP)
            log.debug('HANDLER_SETTINGS %s', HANDLER_SETTINGS)
            log.exception("Something went wrong loading the handler %s", ch)
            log.error("Skipping this handler...")

    handlers_loaded = True
    log.debug('All handlers:')
    for sym, hdic in handlers.items():
        for l in hdic.get('loaders', []):
            log.debug('Symbol %s - Loader: %s', sym, type(l).__name__)
        for l in hdic.get('managers', []):
            log.debug('Symbol %s - Manager: %s', sym, type(l).__name__)
    log.debug('--- End of reload_handlers() ---')
