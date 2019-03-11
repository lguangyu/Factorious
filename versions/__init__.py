#!/usr/bin/env python3

from .stub import FactorioTunesDBKeyExistsError,\
	FactorioTunesBase, FactorioTunesStub

from .v015_base import FactorioTunesDB_v015


# initialize
_STUB = FactorioTunesStub()
_STUB.register(FactorioTunesDB_v015, "0.15", "0.15.base", "015")
# set default version
default = "0.15"


# interface function
def register(*ka, **kw):
	_STUB.register(*ka, **kw)

def get(*ka, **kw):
	return _STUB.get(*ka, **kw)
