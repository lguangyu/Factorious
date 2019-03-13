#!/usr/bin/env python3

#import os
import collections as _collections_m_


class FactorioTunesBase(object):
	"""
	abstract class should be inherited by all tune bases types;
	"""
	# this helps resolve all databases are using same keys of tuning
	_TUNE_DB_DEFAULT_ATTRS_ = dict(
		COMMON_TRIVIALS = [],
		#COMMON_TRIVIALS_STR = "",
		CRAFTERS = {},
		DEFAULT_FLUID_WEIGHT = 0.0,
		DEFAULT_YIELD_LEVEL = "normal",
		FLUIDS = [],
		RECIPE_CATEGORIES = {},
		RECIPE_JSON = None,
		MADEUP_RECIPES = [],
	)

	def __getattr__(self, key):
		return vars(self).get(key,
			default = FactorioTunesBase._TUNE_DB_DEFAULT_ATTRS_[key])

	def _check_attrs(self):
		# this hints missing attributes after db updates
		missings = [k for k in vars(self).keys()\
			if k not in FactorioTunesBase._TUNE_DB_DEFAULT_ATTRS_]
		if missings:
			raise AttributeError(("below attributes are used in updated "\
				+ "database (%s) but not recognized by defaults:\n    %s\n\n"\
				+ "for backward compatibility, please add them "\
				+ "and their default values to the base class "\
				+ "'versions.stub.FactorioTunesBase'")\
				% (self.get_stub_keys()[0], (",").join(missings)))
		return


class FactorioTunesDatabase(object):
	"""
	decorator for version tuning databases;
	"""
	def __init__(self, key, *more_keys):
		"""
		PARAMETERS
		----------
		key, more_keys:
			the database keys used in the stub; must be hashable;

		EXCEPTIONS
		----------
		ValueError: if some key is not hashable;
		"""
		keys = [key] + list(more_keys)
		super(FactorioTunesDatabase, self).__init__()
		if not all([isinstance(i, _collections_m_.abc.Hashable) for i in keys]):
			raise ValueError("all values of 'keys' must be hashable")
		# OH! sort it
		self.keys = sorted(keys)
		return

	def __call__(self, cls):
		class wrapped_db(cls,FactorioTunesBase):
			__doc__ = cls.__doc__
			_stub_keys_ = self.keys.copy()
			_wrapped_class_original_ = cls

			def __init__(_self, *ka, **kw):
				super(wrapped_db, _self).__init__(*ka, **kw)
				_self._check_attrs()
				return

			@classmethod
			def get_stub_keys(_cls):
				"""
				get the keys should be used in the database stub
				"""
				return _cls._stub_keys_.copy()
		return wrapped_db


class FactorioTunesDBKeyExistsError(RuntimeError):
	pass


class FactorioTunesStub(object):
	def __init__(self):
		super(FactorioTunesStub, self).__init__()
		self._db_typelist = list()
		self._db_keyref = dict()
		return


	def register(self,
			tunedb_t: FactorioTunesBase,
		) -> None:
		"""
		register a <tunedb_t> with its search key;

		PARAMETERS
		----------
		tunedb_t:
			a derived FactorioTunesBase type class tuned for the Factorio
			version;

		EXCEPTIONS
		----------
		TypeError: if tunedb_t is not a <class> of FactorioTunesBase;
		FactorioTunesDBKeyExistsError: if try to register a database with
			existing key;
		"""
		if not issubclass(tunedb_t, FactorioTunesBase):
			raise TypeError("'tunedb_t' must be a subclass of FactorioTunesBase")
		_keys = tunedb_t.get_stub_keys()
		if any([k in self._db_keyref for k in _keys]):
			raise FactorioTunesDBKeyExistsError("key '%s' already exists" % k)
		# add to type list
		if tunedb_t not in self._db_typelist:
			self._db_typelist.append(tunedb_t)
		# add key search dict
		for k in _keys:
			self._db_keyref[k] = tunedb_t
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
		if version_key not in self._db_keyref:
			raise LookupError("version '%s' is not found in database"\
				% version_key)
		return self._db_keyref[version_key](*ka, **kw)


	def get_num_registered(self) -> int:
		"""
		get number of registered tune databases;
		"""
		return len(self._db_typelist)


	def list_registered(self) -> list:
		"""
		return a list of keys to registered tune databases;
		"""
		rkeys = [db_t.get_stub_keys() for db_t in self._db_typelist]
		rkeys.sort(key = lambda x: x[0])
		return rkeys
