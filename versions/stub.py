#!/usr/bin/env python3

import collections
from . import db_base


class FactorioTunesDBKeyExistsError(RuntimeError):
	pass


class FactorioTunesStub(object):
	"""
	stub database of version databases;
	"""
	def __init__(self):
		super(FactorioTunesStub, self).__init__()
		self._db_keyref = dict()
		return


	def register(self,
			tunedb_t: db_base._FactorioTunesDatabaseWrapperBase,
		) -> None:
		"""
		register a <tunedb_t> with its search key;

		PARAMETERS
		tunedb_t:
			a derived FactorioTunesBase type class tuned for the Factorio
			version;

		EXCEPTIONS
		TypeError: if tunedb_t is not a <class> of FactorioTunesBase;
		FactorioTunesDBKeyExistsError: if try to register a database with
			existing key;
		"""
		if not issubclass(tunedb_t, db_base._FactorioTunesDatabaseWrapperBase):
			raise TypeError("'tunedb_t' must be a decorated by\
				'AsFactorioTunesDatabase'")
		_keys = tunedb_t.get_stub_keys()
		for k in _keys:
			if k in self._db_keyref:
				raise FactorioTunesDBKeyExistsError("key '%s' already in use" % k)
		# add key search dict
		for k in _keys:
			self._db_keyref[k] = tunedb_t
		return


	def get(self, version_key, *ka, **kw):
		"""
		fetch an instance of the tune database class associated with given key

		PARAMETERS
		version_key:
			the searching key;
		*ka, **kw:
			other arguments passed to the tunes db initializer;
		"""
		if version_key not in self._db_keyref:
			raise LookupError("version '%s' is not found in database"\
				% version_key)
		return self._db_keyref[version_key](*ka, **kw)


	def get_num_registered(self) -> int:
		"""
		get number of registered tune databases;
		"""
		return len(set(self._db_keyref.values()))


	def list_registered(self) -> list:
		"""
		return a list of keys to registered tune databases;
		"""
		rkeys = [db_t.get_stub_keys() for db_t in set(self._db_keyref.values())]
		rkeys.sort(key = lambda x: x[0])
		return rkeys
