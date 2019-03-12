#!/usr/bin/env python3
# these are abstract base classes

import collections as _collections_m_


class ProtectedAtrributeHolder(object):
	"""
	attribute holder; protected from querying non-existing attributes
	"""
	def __init__(self):
		super(ProtectedAtrributeHolder, self).__init__()

	# override this
	# make get attribute does not raise error if not find
	def __getattr__(self, attr):
		return vars(self).get(attr, None)


class DefaultValueDict(_collections_m_.defaultdict):
	"""
	different from collections.defaultdict;
	if key is missing, return default value but not set it;
	"""
	def __missing__(self, key):
		if not self.default_factory:
			super(DefaultValueDict, self).__missing__(key)
		else:
			self[key] = value = self.default_factory(key)
			return value
