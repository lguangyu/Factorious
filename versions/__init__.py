#!/usr/bin/env python3

from .stub import FactorioTunesDBKeyExistsError, FactorioTunesStub

from . import v015_base
from . import v016_base
from . import v017_base


# initialize
_STUB = FactorioTunesStub()
_STUB.register(v015_base.FactorioTunesDB_v015)
_STUB.register(v016_base.FactorioTunesDB_v016)
_STUB.register(v017_base.FactorioTunesDB_v017)
# set default version
default = "0.17"


# interface function
def register(*ka, **kw):
	_STUB.register(*ka, **kw)

def get(*ka, **kw):
	return _STUB.get(*ka, **kw)

def list_registered():
	return _STUB.list_registered()

def get_num_registered():
	return _STUB.get_num_registered()
