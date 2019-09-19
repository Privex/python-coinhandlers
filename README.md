[![PyPi Version](https://img.shields.io/pypi/v/privex-coinhandlers.svg)](https://pypi.org/project/privex-coinhandlers/)
![License Button](https://img.shields.io/pypi/l/privex-coinhandlers) ![PyPI - Downloads](https://img.shields.io/pypi/dm/privex-coinhandlers)
![PyPI - Python Version](https://img.shields.io/pypi/pyversions/privex-coinhandlers) 
![GitHub last commit](https://img.shields.io/github/last-commit/Privex/python-coinhandlers)

# Privex's Python Coin Handlers

Work-in-progress. Coin handlers were originally written for one of our open source projects:
[privex/cryptotoken-converter](https://github.com/Privex/cryptotoken-converter)

This project contains independent versions of our coin handlers that can be used with any python project, regardless
of framework. Coin handlers can be used for handling receiving, sending, and issuing of coins.

**Official Repo:** https://github.com/privex/python-coinhandlers

# Installation

Minimum Python version is **Python 3.6** - but we recommend **Python 3.7** for best compatibility.

```sh
pip3 install privex-coinhandlers
```



# License

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


This project is licensed under the **X11 / MIT** license. See the file **LICENSE** for full details.

Here's the important bits:

 - You must include/display the license & copyright notice (`LICENSE`) if you modify/distribute/copy
   some or all of this project.
 - You can't use our name to promote / endorse your product without asking us for permission.
   You can however, state that your product uses some/all of this project.


# Example usage:

### Note on Context Managers

As of Version 1.1.0 - context management was added to some coin handlers, as well as dummy context
management for handlers that don't need it.

It's recommended to use context management (`with` statements) when using a loader/manager
to ensure connections, database sessions etc. are opened and closed cleanly.

```python
from privex.coin_handlers import MoneroLoader, get_loader, Coin

###
# Context management when using on-the-fly programmatic loading
###

with get_loader('XMR') as m:
    m.load()
    txs = m.list_txs()

###
# Context management when directly using loader/manager classes
###

settings = dict(
    COIND_RPC=dict(XMR=dict(user='monero', password='SomeRPCPassword', port=18100))
)

xmrcoin = Coin(symbol='XMR', symbol_id='XMR')

with MoneroLoader(settings=settings, coins=[xmrcoin]) as m:
    m.load()
    txs = m.list_txs()

```

### Using a loader/manager directly

```python
from privex.coin_handlers import BitcoinLoader, BitcoinManager, Coin

settings = dict(
    COIND_RPC=dict(
        BTC={}
    )
)

# A Coin object generally only needs ``symbol`` and ``symbol_id``
# Account-based coins such as Steem and EOS will also need ``our_account`` (your sending/receiving account)
# Most coins should work without any ``setting_`` options, unless they depend on authentication with local daemon
# e.g. the Bitcoin handler depends on a user/pass to connect to bitcoind 
c = Coin(
    setting_user='bitcoinrpc', 
    setting_pass='SomeSecureRPCPassword',
    setting_json='{"confirms_needed": 1}',
    symbol='BTC',     # A unique symbol or ID that you use to identify this coin in your app (returned by list_txs())
    symbol_id='BTC'   # The ``symbol_id`` **MUST** match the native coin symbol for the network you use it on.
)


######
#
# Coin Handler Loaders
#
######

# Loaders expect both ``settings`` (a dict containing symbols mapped to dicts containing settings),
# as well as a ``List[Coin]`` containing :class:`privex.coin_handlers.base.objects.Coin` objects they should handle.
# A loader's sole purpose is handling incoming deposit transactions, something which could easily be done through
# a third party service such as a block explorer.
bl = BitcoinLoader(settings=settings, coins=[c])

# list_txs() is a generator which outputs Deposit objects (which can also be converted to dict's)
txs = bl.list_txs()
next(txs)
# <Deposit coin='BTC' amount='0.00177883' address='3xxxxxKYQLH24Aa3xxxxtL3mggxxx'>

x = next(txs)
print(dict(x))
# {
# 'coin': 'BTC', 'txid': '8xxxx5a1xxxxxxxxxxxxxxxxxxxx2dd81xxxxxx5973', 
# 'vout': 0, 'address': '3xxxxxxxxxxxxxxxxxxxxxxxxx', 
# 'amount': Decimal('0.00012434'), 'tx_timestamp': datetime.datetime(2019, 4, 5, 4, 34, 45, tzinfo=<UTC>)
# }

print(x.address)
# 3xxxxxxxxxxxxxxxxxxxxxxxxx

######
#
# Coin Handler Managers
#
######

# Managers expect ``settings`` and ``coin`` (that's ONE coin, not a list).
# A manager handles everything other than deposits, it generally handles functions such as address generation,
# sending/issuing coins, and running health checks on a coin.
bm = BitcoinManager(settings=settings, coin=c)

# health_test() returns True (dependant service e.g. bitcoind is working fine), or False (service is broken)
# This can be used to detect whether there's a problem with the RPC node *before* running any sending code.
bm.health_test()
# True


bm.health()
# (
#   'BitcoinManager', 
#   ('Symbol', 'Status', 'Current Block', 'Version', 'Wallet Balance', 'P2P Connections'), 
#   (
#      'BTC', '<b style="color: green">Online</b>', '586,662 (Headers: 586,662)', 
#      '170100 (/Satoshi:0.17.1/)', '0.1234567', '8'
#   )
# )

bm.get_deposit()

# ('address', '3GnzkkGHZSdBFRYXhhk34xFTuN4cpm1M6W')

```

### Programmatic loading of handlers

Using the coin handler helper functions in ``privex/coin_handlers/__init__.py`` it's possible to load handlers 
on-the-fly using user specified handler names, and lookup the correct handler just using the coin symbol.


```python
import privex.coin_handlers as ch
from privex.coin_handlers import Coin

# In the example code, there are three coin handlers entered by default: Steem, Monero and Bitcoin
print(ch.COIN_HANDLERS.keys())
# dict_keys(['Bitcoin', 'Steem', 'Monero'])

# To ensure the coin handlers you want to use, are actually loaded, you should call enable_handler
# It won't hurt if they're already enabled.
ch.enable_handler('Bitcoin', 'Monero')

# Add Dogecoin to the coins handled by the ``Bitcoin`` coin handler.
ch.add_handler_coin('Bitcoin', Coin(symbol='DOGE', symbol_id='DOGE'))

# Add connection settings for DOGE's handler instances
ch.configure_coin('DOGE', user='dogerpc', password='SomeSecret', port=22555)

# Some handlers such as Monero come with their native coin pre-added. You can check if a handler has
# a certain coin with `handler_has_coin`
ch.handler_has_coin('Monero', 'XMR')
# True

# Add connection and wallet configuration settings for Monero (XMR)
# wallet = Monero wallet filename, walletpass = Wallet encryption password, account = Wallet account
ch.configure_coin(
    'XMR',
    user='monero', password='SomeRPCPassword', port=18100, confirms_needed=0,
    wallet='mnrwallet', walletpass='SomeWalletPassword', account='mywalletaccount'
)

# Force reload the handlers
ch.reload_handlers()

# As we can see, if we pass the symbol DOGE to get_loader we get a BitcoinLoader object  
doge = ch.get_loader('DOGE')
# <privex.coin_handlers.Bitcoin.BitcoinLoader.BitcoinLoader object at 0x10ac0f160>

# We cam also see in the loader object that our coin options were injected into the Loader settings, with the password
# 'SecurePass' and username 'dogerpc'.
print(doge.settings['DOGE'])
# {
#   'host': '127.0.0.1', 'port': 8332, 'user': 'dogerpc', 'password': 'SecurePass', 
#   'confirms_needed': 0, 'use_trusted': True, 'string_amt': True
# }

```

# Contributing

We're very happy to accept pull requests, and work on any issues reported to us. 

Here's some important information:

**Reporting Issues:**

 - For bug reports, you should include the following information:
     - Version of `privex-coinhelpers` and `requests` tested on - use `pip3 freeze`
        - If not installed via a PyPi release, git revision number that the issue was tested on - `git log -n1`
     - Your python3 version - `python3 -V`
     - Your operating system and OS version (e.g. Ubuntu 18.04, Debian 7)
 - For feature requests / changes
     - Please avoid suggestions that require new dependencies. This tool is designed to be lightweight, not filled with
       external dependencies.
     - Clearly explain the feature/change that you would like to be added
     - Explain why the feature/change would be useful to us, or other users of the tool
     - Be aware that features/changes that are complicated to add, or we simply find un-necessary for our use of the 
       tool may not be added (but we may accept PRs)
    
**Pull Requests:**

 - We'll happily accept PRs that only add code comments or README changes
 - Use 4 spaces, not tabs when contributing to the code
 - You can use features from Python 3.6+ (we run Python 3.7+ for our projects)
    - Features that require a Python version that has not yet been released for the latest stable release
      of Ubuntu Server LTS (at this time, Ubuntu 18.04 Bionic) will not be accepted. 
 - Clearly explain the purpose of your pull request in the title and description
     - What changes have you made?
     - Why have you made these changes?
 - Please make sure that code contributions are appropriately commented - we won't accept changes that involve 
   uncommented, highly terse one-liners.

**Legal Disclaimer for Contributions**

Nobody wants to read a long document filled with legal text, so we've summed up the important parts here.

If you contribute content that you've created/own to projects that are created/owned by Privex, such as code or 
documentation, then you might automatically grant us unrestricted usage of your content, regardless of the open 
source license that applies to our project.

If you don't want to grant us unlimited usage of your content, you should make sure to place your content
in a separate file, making sure that the license of your content is clearly displayed at the start of the 
file (e.g. code comments), or inside of it's containing folder (e.g. a file named LICENSE). 

You should let us know in your pull request or issue that you've included files which are licensed
separately, so that we can make sure there's no license conflicts that might stop us being able
to accept your contribution.

If you'd rather read the whole legal text, it should be included as `privex_contribution_agreement.txt`.

### (Alternative) Manual install from Git

If you don't want to PyPi (e.g. for development versions not on PyPi yet), you can install the 
project directly from our Git repo.

Unless you have a specific reason to manually install it, you **should install it using pip3 normally**
as shown above.

**Option 1 - Use pip to install straight from Github**

```sh
pip3 install git+https://github.com/Privex/python-coinhandlers
```

**Option 2 - Clone and install manually**

```bash
# Clone the repository from Github
git clone https://github.com/Privex/python-coinhandlers
cd python-coinhandlers

# RECOMMENDED MANUAL INSTALL METHOD
# Use pip to install the source code
pip3 install .

# ALTERNATIVE INSTALL METHOD
# If you don't have pip, or have issues with installing using it, then you can use setuptools instead.
python3 setup.py install
```

# Thanks for reading!

**If this project has helped you, consider [grabbing a VPS or Dedicated Server from Privex](https://www.privex.io) - 
prices start at as little as US$8/mo (we take cryptocurrency!)**