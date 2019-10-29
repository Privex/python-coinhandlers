from privex import coin_handlers as ch
from privex.coin_handlers import Coin


def clear_handler(name: str):
    ch.COIN_HANDLERS[name] = dict(enabled=False, coins=[], kwargs={})
    ch.reload_handlers()


def clear_handler_settings(symbol: str = None):
    if not symbol:
        ch.HANDLER_SETTINGS['COIND_RPC'] = dict(BTC={})
        return
    if symbol in ch.HANDLER_SETTINGS['COIND_RPC']:
        ch.HANDLER_SETTINGS['COIND_RPC'][symbol] = {}


def setup_handler(name: str, symbol: str = 'EXTESTCOIN', enabled: bool = True):
    if enabled:
        ch.enable_handler(name)
    else:
        ch.disable_handler(name)
    
    coin = Coin(symbol=symbol)
    ch.add_handler_coin(name, coin)
    ch.reload_handlers()
