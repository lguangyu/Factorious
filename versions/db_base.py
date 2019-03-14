#!/usr/bin/env python3

import collections


class _FactorioTunesDatabaseWrapperBase(object):
	"""
	abstract class should be inherited by all tune bases types;
	though user should not inherit it maunally: done by decorating with
	'AsFactorioTunesDatabase'
	"""
	# this helps resolve all databases are using same keys of tuning
	_TUNES_DB_DEFAULT_ATTRS_ = dict(
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
		return vars(self).get(key, _FactorioTunesDatabaseWrapperBase.\
				_TUNES_DB_DEFAULT_ATTRS_[key])


	def _check_attrs(self):
		# this hints missing attributes after db updates
		missings = [k for k in vars(self).keys()\
			if k not in _FactorioTunesDatabaseWrapperBase.\
				_TUNES_DB_DEFAULT_ATTRS_]
		if missings:
			raise AttributeError(("below attribute(s) are used in updated "\
				+ "database (%s) but not recognized by defaults:\n    %s\n\n"\
				+ "for backward compatibility, please add them "\
				+ "and their default values to the base class "\
				+ "'versions.stub.FactorioTunesBase'")\
				% (self.get_stub_keys()[0], (",").join(missings)))
		return


class _FactorioTunesDatabaseWrapperMetaclass(type):
	"""
	this class deals with the inheritance of decorated class by
	'AsFactorioTunesDatabase'; the child class will directly inherit the actual
	parent, not the decorated wrapper;
	"""
	stripping = _FactorioTunesDatabaseWrapperBase


	@classmethod
	def strip_decorator(cls, input_cls):
		"""
		strip the old decorator when the class type is generated;
		"""
		# decorator is the class inherits _FactorioTunesDatabaseWrapperBase,
		# but not exactly is
		if issubclass(input_cls, cls.stripping) and\
			(input_cls is not cls.stripping):
			return input_cls._wrapped_class_original_
		else:
			return input_cls


	def __new__(cls, name, bases, attrs):
		bases = tuple([cls.strip_decorator(i) for i in bases])
		return super(_FactorioTunesDatabaseWrapperMetaclass, cls).\
			__new__(cls, name, bases, attrs)


class AsFactorioTunesDatabase(object):
	"""
	decorator for version tuning databases;
	"""
	def __init__(self, key, *more_keys):
		"""
		PARAMETERS
		key, more_keys:
			the database keys used in the stub; must be hashable;

		EXCEPTIONS
		ValueError: if some key is not hashable;
		"""
		keys = [key] + list(more_keys)
		super(AsFactorioTunesDatabase, self).__init__()
		if not all([isinstance(i, collections.abc.Hashable) for i in keys]):
			raise ValueError("all values of 'keys' must be hashable")
		# OH! sort it
		self.keys = sorted(keys)
		return


	def __call__(self, cls):
		class wrapped_c(cls, _FactorioTunesDatabaseWrapperBase,\
			metaclass = _FactorioTunesDatabaseWrapperMetaclass):
			__doc__ = cls.__doc__
			_stub_keys_ = self.keys.copy()
			_wrapped_class_original_ = cls


			def __init__(_self, *ka, **kw):
				super(wrapped_c, _self).__init__(*ka, **kw)
				_self._check_attrs()
				return


			@classmethod
			def get_stub_keys(_cls):
				"""
				get the keys should be used in the database stub
				"""
				return _cls._stub_keys_.copy()
		return wrapped_c
