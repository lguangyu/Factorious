#!/usr/bin/env python3

import os
import collections as _collections_m_


class FactorioTunesBase(object):
	# namespace use
	# an attribute-index safe
	def __init__(self, *ka, **kw):
		super(FactorioTunesBase, self).__init__()
		return

	@staticmethod
	def dirname(self, path):
		return os.path.dirname(path)



class FactorioTunesDBKeyExistsError(RuntimeError):
	pass


class FactorioTunesStub(object):
	def __init__(self):
		super(FactorioTunesStub, self).__init__()
		self._tune_dbs = dict()
		return


	def register(self,
			tune_db: FactorioTunesBase,
			*version_keys: str,
		) -> None:
		"""
		register a <tune_db> with its search key;

		PARAMETERS
		----------
		tune_db:
			a derived FactorioTunesBase type class tuned for the Factorio
			versions;

		version_keys:
			string (and aliases) associated with this db;

		EXCEPTIONS
		----------
		TypeError: if tune_db is not a <class> of FactorioTunesBase
		FactorioTunesDBKeyExistsError: if try to register a database with
			existing key;
		"""
		if not issubclass(tune_db, FactorioTunesBase):
			raise TypeError("'tune_db' must be a subclass of FactorioTunesBase")
		for k in version_keys:
			if k in self._tune_dbs:
				raise FactorioTunesDBKeyExistsError("key '%s' already exists"\
					% k)
			self._tune_dbs[k] = tune_db
		return


	def get(self, version_key, *ka, **kw):
		"""
		fetch an instance of the tune database class associated with given key

		PARAMETERS
		----------
		version_key:
			the searching key;

		*ka, **kw:
			other arguments passed to the tunes db initializer;
		"""
		if version_key not in self._tune_dbs:
			raise LookupError("version '%s' is not found in database"\
				% version_key)
		return self._tune_dbs[version_key](*ka, **kw)
