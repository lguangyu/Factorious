#!/usr/bin/env python3
# these are abstract base classes


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
