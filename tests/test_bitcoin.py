import unittest
from datetime import datetime
from decimal import Decimal
from time import sleep

import privex.coin_handlers as ch
from privex.rpcemulator.bitcoin import BitcoinEmulator

from privex.coin_handlers.base import AccountNotFound, NotEnoughBalance
from tests.base import clear_handler, clear_handler_settings, setup_handler


class TestBitcoinHandlerEmulated(unittest.TestCase):
    emulator: BitcoinEmulator
    """Stores the :class:`.BitcoinEmulator` instance"""
    
    @classmethod
    def setUpClass(cls) -> None:
        """Launch the Bitcoin RPC emulator in the background on default port 8332"""
        cls.emulator = BitcoinEmulator()
        sleep(1)
        clear_handler_settings()
        clear_handler('Bitcoin')

        setup_handler('Bitcoin', 'BTC')

    @classmethod
    def tearDownClass(cls) -> None:
        """Shutdown the Bitcoin RPC emulator process"""
        cls.emulator.terminate()
        sleep(1)
        clear_handler_settings()
        clear_handler('Bitcoin')
    
    def test_bitcoin_loader(self):
        """Test BitcoinLoader returns valid Deposit objects"""
        loader = ch.get_loader('BTC')
        loader.load()
        
        txs = list(loader.list_txs())
        
        self.assertGreater(len(txs), 0)
        
        for t in txs:
            self.assertIs(type(t.amount), Decimal)
            self.assertIs(type(t.tx_timestamp), datetime)
            self.assertIs(type(t.address), str)
            self.assertGreater(len(t.txid), 20)
            self.assertGreater(t.amount, Decimal('0.0000001'))
            self.assertEqual(t.coin, 'BTC')

    def test_bitcoin_get_deposit(self):
        """Test BitcoinManager get_deposit returns the correct deposit type and a valid looking address"""
        mgr = ch.get_manager('BTC')
        dep_type, addr = mgr.get_deposit()
        self.assertEqual(dep_type, 'address')
        self.assertEqual(addr[0], '1')
        self.assertGreater(len(addr), 20)

    def test_bitcoin_validate(self):
        """Test BitcoinManager address_valid returns True for valid addr and False for invalid"""
        mgr = ch.get_manager('BTC')
        self.assertTrue(mgr.address_valid('1Br7KPLQJFuS2naqidyzdciWUYhnMZAzKA'))
        self.assertFalse(mgr.address_valid('NotAnAddress'))

    def test_bitcoin_send(self):
        """Test a valid send call works as expected"""
        mgr = ch.get_manager('BTC')
        dep_type, addr = mgr.get_deposit()

        tx = mgr.send(Decimal('0.001'), address=addr)
        self.assertEqual(tx['coin'], 'BTC')
        self.assertEqual(tx['amount'], Decimal('0.001'))
        self.assertEqual(tx['send_type'], 'send')
        self.assertEqual(tx['fee'], Decimal('0'))

    def test_bitcoin_send_invalid_addr(self):
        """Test :class:`.AccountNotFound` is raised when sending to non-existent address"""
        mgr = ch.get_manager('BTC')
        
        with self.assertRaises(AccountNotFound):
            mgr.send(Decimal('0.001'), address='NotAnAddress')

    def test_bitcoin_send_low_balance(self):
        """Test :class:`.NotEnoughBalance` is raised when sending too much"""
        mgr = ch.get_manager('BTC')
        
        bal = mgr.balance()
        with self.assertRaises(NotEnoughBalance):
            mgr.send(bal * Decimal('2'), '1Br7KPLQJFuS2naqidyzdciWUYhnMZAzKA')

