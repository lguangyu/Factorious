#!/usr/bin/env python3

import warnings as _warnings_m_
import textwrap as _textwrap_m_


class Item(object):
	"""
	items caches the dependencies between Recipes:
	"""
	def __init__(self,
			name: str,
			input_of: set = set(),
			product_of: set = set(),
			is_trivial = False,
			need_optimize = False,
		) -> None:
		"""
		PARAMETERS
		----------
		name:
			name of the Item;

		input_of:
			list of names of Recipes uses this Item as input;

		product_of:
			list of names of Recipes produces this Item;

		is_trivial:
			if True, this Item is marked as raw input;

		need_optimize:
			if True, this Item needs optimization;

		EXCEPTIONS
		----------
		TypeError: if name is not instance of str;
		"""
		super(Item, self).__init__()
		if not isinstance(name, str):
			raise TypeError("'name' must be of type 'str'")
		self.name = name
		self.input_of = set(input_of)
		self.product_of = set(product_of)
		self.is_trivial = bool(is_trivial)
		self.need_optimize = need_optimize
		return


	def __str__(self):
		fmt = "<%s '%s', trivial: %s>"
		return fmt % (type(self).__name__, self.name, self.is_trivial)


	def __repr__(self):
		return str(self)


	def copy(self) -> "Item":
		_warnings_m_.warn(_textwrap_m_.wrap(
			"use of Item.copy() is deprecated and not correct-garanteed; should use RecipeSet.__init__() or RecipeSet.refresh() to regenerate links between Items/Recipes;",
			80), DeprecationWarning)
		new = type(self)(
			name = self.name,
			input_of = self.input_of,
			product_of = self.product_of,
			is_trivial = self.is_trivial,
			need_optimize = need_optimize)
		return new


	def is_raw(self, ignore_trivial = False) -> bool:
		"""
		return True if this item is considered raw material;

		PARAMETERS
		----------
		ignore_trivial:
			if True, <is_trivial> flag is ignored, and only actual raw material
			is reported as raw (i.e. with empty <product_of> set); if False,
			also report raw when <is_trivial> is True;
		"""
		return ((not ignore_trivial) and self.is_trivial) \
			or len(self.product_of) == 0


	def has_multiple_source(self) -> bool:
		"""
		return True if this Item has more than one source Recipes;
		"""
		return len(self.product_of) > 1
