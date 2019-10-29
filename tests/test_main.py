import unittest
import privex.coin_handlers as ch
from privex.coin_handlers.base.objects import Coin
from tests.base import clear_handler, clear_handler_settings, setup_handler


class TestHandlerMain(unittest.TestCase):
    @classmethod
    def setUpClass(cls) -> None:
        """In-case this TestCase has been ran after another which modified the handlers, reset the handlers."""
        clear_handler_settings()
        clear_handler('Bitcoin')

    @classmethod
    def tearDownClass(cls) -> None:
        """Reset Bitcoin in :py:attr:`.ch.COIN_HANDLERS` back to defaults after entire testcase is done."""
        clear_handler_settings()
        clear_handler('Bitcoin')
    
    def setUp(self) -> None:
        """Enable ``Bitcoin`` handler and add example coin ``EXTESTCOIN``"""
        setup_handler('Bitcoin')
    
    def tearDown(self) -> None:
        """Reset Bitcoin in :py:attr:`.ch.COIN_HANDLERS` back to defaults for the next test method"""
        clear_handler_settings()
        clear_handler('Bitcoin')
    
    def test_enable_handler(self):
        ch.disable_handler('Bitcoin')
        self.assertFalse(ch.COIN_HANDLERS['Bitcoin']['enabled'])
        ch.enable_handler('Bitcoin')
        self.assertTrue(ch.COIN_HANDLERS['Bitcoin']['enabled'])

    def test_configure_coin(self):
        """Test configure_coin with the pre-existing BTC coin key"""
        crpc = ch.HANDLER_SETTINGS['COIND_RPC']
        self.assertIn('BTC', crpc)
        self.assertNotIn('user', crpc['BTC'])
        ch.configure_coin('BTC', user='bitcoinrpc')
        self.assertEqual(crpc['BTC']['user'], 'bitcoinrpc')

    def test_configure_coin_create(self):
        """Test that configure_coin creates a coin key if it doesn't exist"""
        crpc = ch.HANDLER_SETTINGS['COIND_RPC']
        self.assertNotIn('TESTCOIN', crpc)
        ch.configure_coin('TESTCOIN', hello='world')
        self.assertIn('TESTCOIN', crpc)
        self.assertEqual(crpc['TESTCOIN']['hello'], 'world')
    
    def test_configure_handler(self):
        self.assertIn('Bitcoin', ch.COIN_HANDLERS)
        ch.configure_handler('Bitcoin', testing=1, kwargs={'example': 'hello'})
        c_btc = ch.COIN_HANDLERS['Bitcoin']
        self.assertIn('testing', c_btc)
        self.assertIn('kwargs', c_btc)
        self.assertDictEqual(c_btc['kwargs'], {'example': 'hello'})
        self.assertEqual(c_btc['testing'], 1)

    def test_configure_handler_nonexistent(self):
        with self.assertRaises(KeyError):
            ch.configure_handler('ThisDoesNotExist', hello='world')
    
    def test_add_coin(self):
        c_btc = ch.COIN_HANDLERS['Bitcoin']
        self.assertFalse(ch.handler_has_coin('Bitcoin', 'TESTCOIN'))
        
        coin = Coin(symbol='TESTCOIN')
        ch.add_handler_coin('Bitcoin', coin)

        self.assertTrue(ch.handler_has_coin('Bitcoin', 'TESTCOIN'))
        self.assertIn(coin, c_btc['coins'])
    
    def test_has_manager_loader(self):
        coin = Coin(symbol='TESTCOIN')
        ch.add_handler_coin('Bitcoin', coin)
        ch.enable_handler('Bitcoin')
        ch.reload_handlers()
        self.assertTrue(ch.has_loader('TESTCOIN'))
        self.assertTrue(ch.has_manager('TESTCOIN'))

    def test_has_manager_loader_nonexistent(self):
        self.assertFalse(ch.has_loader('NoExistCoin'))
        self.assertFalse(ch.has_manager('NoExistCoin'))
    
    def test_get_loader(self):
        coin = Coin(symbol='TESTCOIN')
        ch.add_handler_coin('Bitcoin', coin)
        ch.enable_handler('Bitcoin')
        ch.reload_handlers()
        



