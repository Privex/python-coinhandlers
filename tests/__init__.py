import logging
import unittest
from privex.loghelper import LogHelper
from privex.helpers import env_bool
from privex.rpcemulator.base import Emulator
from tests.test_bitcoin import *
from tests.test_main import *


if env_bool('DEBUG', False) is True:
    LogHelper('privex.coin_handlers', level=logging.DEBUG).add_console_handler(logging.DEBUG)
else:
    LogHelper('privex.coin_handlers', level=logging.CRITICAL)  # Silence non-critical log messages
    Emulator.quiet = True  # Disable HTTP logging

if __name__ == '__main__':
    unittest.main()
