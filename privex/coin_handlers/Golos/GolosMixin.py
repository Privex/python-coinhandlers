import logging
from abc import ABC
from typing import Dict, Optional

from golos import Api
from privex.helpers import empty
from privex.coin_handlers.base import SettingsMixin

log = logging.getLogger(__name__)


class GolosMixin(SettingsMixin, ABC):
    _rpc: Api
    _rpcs: Dict[str, Api]
    _precision: int
    
    def __init__(self, *args, **kwargs):
        self._rpc = None
        
        # List of Golos instances mapped by symbol
        self._rpcs = {}  # type: Dict[str, Api]
        self._precision = None
        
        super(GolosMixin, self).__init__(*args, **kwargs)

    @property
    def rpc(self) -> Api:
        if not self._rpc:
            # Use the symbol of the first coin for our settings.
            symbol = list(self.all_coins.keys())[0]
            settings = self.all_coins[symbol].settings['json']
            rpcs = settings.get('rpcs')
        
            # If you've specified custom RPC nodes in the custom JSON, make a new instance with those
            # Otherwise, use the default Golos API instance
            rpc_conf = dict(num_retries=10, nodes=rpcs)
            log.info('Getting Golos instance for coin %s - settings: %s', symbol, rpc_conf)
            self._rpc = Api() if empty(rpcs, itr=True) else Api(**rpc_conf)  # type: Api
            self._rpcs[symbol] = self._rpc
        return self._rpc

    @property
    def precision(self) -> Optional[int]:
        if not hasattr(self, 'symbol'):
            return None
        """Easy reference to the precision for our current symbol"""
        if not self._precision:
            self._precision = int(self.rpc.asset_precision[self.symbol])
        return self._precision

    def get_rpc(self, symbol: str) -> Api:
        """
        Returns a Golos instance for querying data and sending TXs.
        
        If a custom RPC list is specified in the Coin "custom json" settings, a new instance will be returned with the
        RPCs specified in the json.
        
        :param symbol: Coin symbol to get Beem RPC instance for
        :return beem.steem.Steem: An instance of :class:`beem.steem.Steem` for querying
        """
        if symbol not in self._rpcs:
            settings = self.settings[symbol]
            rpcs = settings.get('rpcs')
            rpc_conf = dict(num_retries=10, nodes=rpcs)
            log.info('Getting Golos instance for coin %s - settings: %s', symbol, rpc_conf)
            self._rpcs[symbol] = self.rpc if empty(rpcs, itr=True) else Api(**rpc_conf)
        return self._rpcs[symbol]

