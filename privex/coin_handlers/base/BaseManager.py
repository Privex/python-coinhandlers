import logging
from abc import ABC, abstractmethod
from decimal import Decimal
from typing import Tuple, Union, Dict

from privex.coin_handlers.base import exceptions
from privex.coin_handlers.base.objects import Coin


class BaseManager(ABC):
    """
    BaseManager - Base class for coin/token management

    A coin manager handles balance checking, sending, and issuing of one or more cryptocurrencies or tokens,
    generally through a direct connection to a local/remote RPC node such as steemd or bitcoind using connection
    settings set by the user in their Django settings.

    Coin managers must be able to initialise themselves using the following data:

    - The coin symbol ``self.symbol`` passed to the constructor
    - The setting_xxx fields on ``self.coin`` :class:`payments.models.Coin`
    - The Django settings `from django.conf import settings`

    If your class requires anything to be added to the Coin object settings, or the Django ``settings`` file,
    you should write a comment listing which settings are required, which are optional, and their format/type.

    e.g. (Optional) settings.STEEM_NODE - list of steem RPC nodes, or string of individual node, URL format

    They must implement all of the methods in this class, set the `can_issue` boolean for detecting if this manager
    can be used to issue (create/print) tokens/coins, as well as configure the `provides` list to display
    the tokens/coins that this manager handles.
    """

    provides = []
    """
    A list of token/coin symbols in uppercase that this loader supports e.g::

        provides = ["LTC", "BTC", "BCH"]

    """

    can_issue = False
    """If this manager supports issuing (creating/printing) tokens/coins, set this to True"""

    def __init__(self, settings: Dict[str, dict] = None, coin: Coin = None, *args, **kwargs):
        self.log = logging.getLogger(__name__)
        if not coin:
            raise AttributeError('"coin" must be specified to BaseManager.')
        self.coin = coin
        self.symbol = self.coin.symbol_id.upper()
        """The native coin symbol, e.g. BTC, LTC, etc. (non-unique)"""

        self.orig_symbol = self.coin.symbol
        """The original unique database symbol ID"""

        self.allsettings =  {} if not settings else settings
        # super(BaseManager, self).__init__(settings=settings, coin=coin, *args, **kwargs)

    def health(self) -> Tuple[str, tuple, tuple]:
        """
        Return health data for the passed symbol, e.g. current block height, block time, wallet balance
        whether the daemon / API is accessible, etc.

        It should return a tuple containing the manager name, the headings for a health table,
        and the health data for the passed symbol (Should include a ``symbol`` or coin name column)

        You may use basic HTML tags in the health data result list, such as
        ``<b>`` ``<em>`` ``<u>`` and ``<span style=""></span>``

        :return tuple health_data: (manager_name:str, headings:list/tuple, health_data:list/tuple,)
        """

        return type(self).__name__, ('Symbol', 'Status',), (self.symbol, 'Health data not supported')

    def health_test(self) -> bool:
        """
        To reduce the risk of unhandled exceptions by sending code, this method should do some basic checks against
        the API to test whether the coin daemon / API is responding correctly.

        This allows code which calls your send() or issue() method to detect the daemon / API is not working, and
        then delay sending/issuing until later, instead of marking a convert / withdrawal status to an error.

        The method body should be wrapped in a try/except, ensuring there's a non-targeted except which
        returns False

        :return bool: True if the coin daemon / API appears to be working, False if it's not
        """
        return True

    @abstractmethod
    def address_valid(self, address) -> bool:
        """
        A simple boolean method, allowing API requests to validate the destination address/account prior to
        giving the user deposit details.

        :param address: An address or account to send to
        :return bool: Is the `address` valid? True if it is, False if it isn't
        """

        raise NotImplemented("{}.address_valid must be implemented!".format(type(self).__name__))

    @abstractmethod
    def get_deposit(self) -> tuple:
        """
        :return tuple: If the coin uses addresses, this method should return a tuple of ('address', coin_address)
        :return tuple: If the coin uses accounts/memos, this method should return a tuple ('account', receiving_account)
                       The memo will automatically be generated by the calling function.
        """

        raise NotImplemented("{}.get_deposit must be implemented!".format(type(self).__name__))

    @abstractmethod
    def balance(self, address: str = None, memo: str = None, memo_case: bool = False) -> Decimal:
        """
        Return the balance of `self.symbol` for our "wallet", or a given address/account, optionally filtered by memo

        :param address:    The address or account to get the balance for. If None, return our total wallet
                           (or default account) balance.
        :param memo:       If not None (and coin supports memos), return the total balance of a given memo
        :param memo_case:  Whether or not to total memo's case sensitive, or not. False = case-insensitive memo
        :raises AccountNotFound: The requested account/address doesn't exist
        :return Decimal: Decimal() balance of address/account, optionally balance (total received) of a given memo
        """

        raise NotImplemented("{}.balance must be implemented!".format(type(self).__name__))

    def issue(self, amount: Decimal, address: str, memo: str = None, trigger_data: Union[dict, list] = None) -> dict:
        """
        Issue (create/print) tokens to a given address/account, optionally specifying a memo if supported

        :param Decimal amount:      Amount of tokens to issue, as a Decimal()
        :param address:             Address or account to issue the tokens to
        :param memo:                Memo to issue tokens with (if supported)
        :param dict trigger_data:   Metadata related to this issue transaction (e.g. the deposit that triggered this)
        :raises IssuerKeyError:     Cannot issue because we don't have authority to (missing key etc.)
        :raises IssueNotSupported:  Class does not support issuing, or requested symbol cannot be issued.
        :raises AccountNotFound: The requested account/address doesn't exist
        :return dict: Result Information

        Format::

          dict {
              txid:str - Transaction ID - None if not known,
              coin:str - Symbol that was sent,
              amount:Decimal - The amount that was sent (after fees),
              fee:Decimal    - TX Fee that was taken from the amount,
              from:str       - The account/address the coins were issued from.
                               If it's not possible to determine easily, set this to None.
              send_type:str  - Should be statically set to "issue"
          }

        """

        raise exceptions.IssueNotSupported("{} does not support issuing tokens.".format(type(self).__name__))

    @abstractmethod
    def send(self, amount: Decimal, address: str, from_address: str = None, memo: str = None,
             trigger_data: Union[dict, list] = None) -> dict:
        """
        Send tokens to a given address/account, optionally specifying a memo and sender address/account if supported

        Your send method should automatically subtract any blockchain transaction fees from the amount sent.

        :param Decimal amount:      Amount of coins/tokens to send, as a Decimal()
        :param address:             Address or account to send the coins/tokens to
        :param memo:                Memo to send coins/tokens with (if supported)
        :param from_address:        Address or account to send from (if required)
        :param dict trigger_data:   Metadata related to this send transaction (e.g. the deposit that triggered this)
        :raises AuthorityMissing:   Cannot send because we don't have authority to (missing key etc.)
        :raises AccountNotFound:    The requested account/address doesn't exist
        :raises NotEnoughBalance:   Sending account/address does not have enough balance to send
        :return dict:  Result Information

        Format::

          dict {
            txid:str - Transaction ID - None if not known,
            coin:str - Symbol that was sent,
            amount:Decimal - The amount that was sent (after fees),
            fee:Decimal    - TX Fee that was taken from the amount,
            from:str       - The account(s)/address(es) the coins were sent from. if more than one, comma separated.
                             If it's not possible to determine easily, set this to None.
            send_type:str  - Should be statically set to "send"
          }

        """

        raise NotImplemented("{}.send must be implemented!".format(type(self).__name__))

    def send_or_issue(self, amount, address, memo=None, trigger_data: Union[dict, list] = None) -> dict:
        """
        Attempt to send an amount to an address/account, if not enough balance, attempt to issue it instead.
        You may override this method if needed.

        :param Decimal amount:      Amount of coins/tokens to send/issue, as a Decimal()
        :param address:             Address or account to send/issue the coins/tokens to
        :param memo:                Memo to send/issue coins/tokens with (if supported)
        :param dict trigger_data:   Metadata related to this issue transaction (e.g. the deposit that triggered this)
        :raises IssuerKeyError:     Cannot issue because we don't have authority to (missing key etc.)
        :raises IssueNotSupported:  Class does not support issuing, or requested symbol cannot be issued.
        :raises AccountNotFound: The requested account/address doesn't exist
        :return dict: Result Information

        Format::

          dict {
            txid:str       - Transaction ID - None if not known,
            coin:str       - Symbol that was sent,
            amount:Decimal - The amount that was sent (after fees),
            fee:Decimal    - TX Fee that was taken from the amount,
            from:str       - The account(s)/address(es) the coins were sent from. if more than one, comma separated.
                             If it's not possible to determine easily, set this to None.
            send_type:str  - Should be set to "send" if the coins were sent, or "issue" if the coins were issued.
          }

        """

        try:
            return self.send(amount=amount, address=address, memo=memo, trigger_data=trigger_data)
        except exceptions.NotEnoughBalance:
            return self.issue(amount=amount, address=address, memo=memo, trigger_data=trigger_data)

    @abstractmethod
    def __enter__(self):
        return self

    @abstractmethod
    def __exit__(self, exc_type, exc_val, exc_tb):
        return self
