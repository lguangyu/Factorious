#!/usr/bin/env python3

from .stub import FactorioTunesDBKeyExistsError,\
	FactorioTunesBase, FactorioTunesStub

from .v015_base import FactorioTunesDB_v015


# initialize
_STUB = FactorioTunesStub()
_STUB.register(FactorioTunesDB_v015)
# set default version
default = "0.15"


# interface function
def register(*ka, **kw):
	_STUB.register(*ka, **kw)

def get(*ka, **kw):
	return _STUB.get(*ka, **kw)

def list_registered():
	return _STUB.list_registered()

def get_num_registered():
	return _STUB.get_num_registered()
