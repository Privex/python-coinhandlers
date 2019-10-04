"""
The KeyStore system is used by certain coin handlers that don't have integrated wallets, such as :py:mod:`.Golos`

The most basic form of KeyStore is the :class:`.MemoryKeyStore` - which simply stores the keys in memory.

Here's an example of configuring the global Key Store to use MemoryKeyStore, and adding a key to the store:

    >>> from privex.coin_handlers import MemoryKeyStore, get_key_store, set_key_store
    >>> # Set the global keystore to use the MemoryKeyStore.
    >>> set_key_store(MemoryKeyStore())
    >>> # Obtain the global key store instance
    >>> store = get_key_store()
    >>> # Add a key to the global key store, for use by the Golos handler
    >>> store.set(
    ...     network='golos', account='someguy123', private_key='5Jq19TeeVmGrBFnu32oxfxQMiipnSCKmwW7fZGUVLAoqsKJ9JwP',
    ...     key_type='active',
    ... )

You can make your own custom key store simply by extending :class:`.KeyStore` and implementing the ``get`` method.

You may also add your own ``__init__`` constructor and take any initialisation arguments you need, since you'll be
passing an already instantiated class to ``set_key_store``.

    >>> class MyStore(KeyStore):
    ...     # You can adjust the method signature to your liking, but don't remove **kwargs !
    ...     def get(self, network=None, private_key=None, account=None, key_type=None, **kwargs) -> Optional[KeyPair]:
    ...         # Do whatever lookup operation(s) you need to do to find the matching key
    ...         # Then simply return either a KeyPair object if it's found, or ``None`` if it's not
    ...         if 'a' == 'b':
    ...             return KeyPair(network='eos', private_key='5xxxxxxx')
    ...         else:
    ...             return None
    ...
    >>> set_key_store(MyStore())

"""
import logging

from abc import ABC, abstractmethod
from decimal import Decimal
from typing import List, Optional, Type

from privex.helpers import is_true

log = logging.getLogger(__name__)

__STORE = {}


class KeyPair:
    id: int
    network: str
    private_key: str
    public_key: str
    account: str
    key_type: str
    balance: Decimal
    used: bool
    
    def __init__(self, network, private_key, public_key=None, account=None, key_type=None, **kwargs):
        self.network, self.private_key, self.public_key = network, private_key, public_key
        self.account, self.key_type = account, key_type
        self.balance = Decimal(kwargs.get('balance', '0'))
        self.used = is_true(kwargs.get('used', False))
        self.id = kwargs.get('id')

    def __iter__(self):
        for k in self.__class__.__dict__:
            if k[:2] == '__':
                continue
            yield (k, getattr(self, k),)

    def __getitem__(self, key):
        """
        When the instance is accessed like a dict, try returning the matching attribute.
        If the attribute doesn't exist, or the key is an integer, try and pull it from raw_data
        """
        if hasattr(self, key):
            return getattr(self, key)
        raise KeyError(key)


class KeyStore(ABC):
    @abstractmethod
    def get(self, network=None, private_key=None, public_key=None, account=None, key_type=None,
            key_type__in=None, used=None, id=None, **kwargs) -> Optional[KeyPair]:
        pass
    
    def set(self, **kwargs):
        pass


class MemoryKeyStore(KeyStore):
    store: List[KeyPair]
    
    def __init__(self):
        self.store = []
    
    def get(self, network=None, private_key=None, public_key=None, account=None, key_type=None, key_type__in=None,
            used=None, id=None, **kwargs) -> Optional[KeyPair]:
        for i, s in enumerate(self.store):
            if network is not None and s.network != network:
                continue
            if private_key is not None and s.private_key != private_key:
                continue
            if public_key is not None and s.public_key != public_key:
                continue
            if account is not None and s.account != account:
                continue
            if key_type is not None and s.key_type != key_type:
                continue
            if used is not None and s.used is not used:
                continue
            if key_type__in is not None and s.key_type not in key_type__in:
                continue
            if id is not None and i != int(id):
                continue
            return s
        return None

    def set(self, **kwargs):
        if 'id' in kwargs:
            s = self.get(id=kwargs['id'])
            for k, v in kwargs.items():
                if hasattr(s, k):
                    setattr(s, k, v)
            return s
        
        s = KeyPair(**kwargs, id=len(self.store) + 1)
        self.store.append(s)
        return s


try:
    from django.db import models
    from privex.helpers.django import model_to_dict
    
    class DjangoKeyStore(KeyStore):
        model: Type[models.Model]
        
        def __init__(self, model: Type[models.Model]):
            self.model = model
        
        def get(self, **kwargs) -> Optional[KeyPair]:
            obj = self.model.objects.filter(**kwargs)
            if len(obj) < 1:
                return None
            return KeyPair(**model_to_dict(obj[0]))

except ImportError as e:
    log.debug('privex.coin_handlers.KeyStore failed to initialise DjangoKeyStore: %s', str(e))
        

def get_key_store() -> KeyStore:
    """Get the current KeyStore singleton instance"""
    return __STORE['keystore']


def set_key_store(keystore: KeyStore):
    """
    Set the current KeyStore singleton
    
    Example:
        
        >>> mk = MemoryKeyStore()
        >>> set_key_store(mk)
    
    """
    __STORE['keystore'] = keystore
