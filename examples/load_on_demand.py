"""
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
from importlib import import_module
from privex.coin_handlers import BaseManager, BaseLoader, Coin

handlers = {}
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

ch_base = 'privex.coin_handlers'
"""Base module path to where the coin handler modules are located. E.g. payments.coin_handlers"""

HANDLER_SETTINGS = {
    'COIND_RPC': {
        'BTC': dict(confirms_needed=6)
    }
}

COIN_HANDLERS = {
    'Bitcoin': {
        'coins': [
            Coin(setting_user='bitcoinrpc', setting_pass='SomeSecurePass', symbol='BTC', symbol_id='BTC'),
            Coin(setting_user='litecoinrpc', setting_pass='SomeSecurePass', symbol='LTC', symbol_id='LTC'),
        ]
    },
    'Steem': {
        'coins': [
            Coin(symbol='STEEM', symbol_id='STEEM'),
            Coin(symbol='SBD', symbol_id='SBD'),
        ]
    }
}


log = logging.getLogger(__name__)


def get_loaders(symbol: str = None) -> list:
    """
    Get all loader's, or all loader's for a certain coin

    :param symbol: The coin symbol to get all loaders for (uppercase)
    :return list: If symbol not specified, a list of tuples (symbol, list<BaseLoader>,)
    :return list: If symbol IS specified, a list of instantiated :class:`base.BaseLoader`'s
    """
    if not handlers_loaded: reload_handlers()
    return [(s, data['loaders'],) for s, data in handlers] if symbol is None else handlers[symbol]['loaders']


def has_manager(symbol: str) -> bool:
    """Helper function - does this symbol have a manager class?"""
    if not handlers_loaded: reload_handlers()
    return symbol.upper() in handlers and len(handlers[symbol].get('managers', [])) > 0


def has_loader(symbol: str) -> bool:
    """Helper function - does this symbol have a loader class?"""
    if not handlers_loaded: reload_handlers()
    return symbol.upper() in handlers and len(handlers[symbol].get('loaders', [])) > 0


def get_managers(symbol: str = None) -> list:
    """
    Get all manager's, or all manager's for a certain coin

    :param symbol: The coin symbol to get all managers for (uppercase)
    :return list: If symbol not specified, a list of tuples (symbol, list<BaseManager>,)
    :return list: If symbol IS specified, a list of instantiated :class:`base.BaseManager`'s
    """
    if not handlers_loaded: reload_handlers()
    return [(s, data['managers'],) for s, data in handlers] if symbol is None else handlers[symbol]['managers']


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
    global handlers
    # `handler` is an un-instantiated class extending BaseLoader / BaseManager
    for coin in COIN_HANDLERS[handler_name]['coins']:
        sym = coin.symbol_id
        if sym not in handlers:
            handlers[sym] = dict(loaders=[], managers=[])
        kwargs = dict(coin=coin) if handler_type == 'managers' else dict(coins=[coin])
        h = handler(settings=HANDLER_SETTINGS, **kwargs)
        handlers[sym][handler_type].append(h)


def reload_handlers():
    """
    Resets `handler` to an empty dict, then loads all ``COIN_HANDLER`` classes into the dictionary ``handlers``
    using ``ch_base`` as the base module path to load from
    """
    global handlers, handlers_loaded
    handlers = {}
    log.debug('--- Starting reload_handlers() ---')

    for ch, ch_data in COIN_HANDLERS.items():
        try:
            mod_path = '.'.join([ch_base, ch])
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
