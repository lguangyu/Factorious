#!/usr/bin/env python3

import warnings as _warnings_m_
import textwrap as _textwrap_m_


class ItemFlags(object):
	def __init__(self):
		super(ItemFlags, self).__init__()
		# True if one or more source recipe is multi-product
		self.product_of_complex_recipe = False
		# True if is unique product of a set of cyclic recipes
		self.cyclic_product = False
		# True if manually set trivial
		self.trivial = False
		# True if manually set as raw input
		self.forced_raw = False
		return


	def copy(self):
		ret = type(self)()
		vars(ret).update(vars(self))
		return ret


class Item(object):
	"""
	items caches the dependencies between Recipes:
	"""
	def __init__(self,
			name: str,
			input_of: set = set(),
			product_of: set = set(),
			flags: ItemFlags = None,
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
		self.flags = ItemFlags() if flags is None else flags.copy()
		return


	def __str__(self):
		fmt = "<%s '%s', trivial: %s>"
		return fmt % (type(self).__name__, self.name, self.is_trivial())


	def __repr__(self):
		return str(self)


	def is_actual_raw(self) -> bool:
		"""
		return True if no recipes produces this Item;
		"""
		return len(self.product_of) == 0


	def is_raw(self, ignore_trivial = False) -> bool:
		"""
		return True if this item is considered raw material;

		PARAMETERS
		----------
		ignore_trivial:
			if True, <is_trivial> flag is ignored; when only actual raw material
			or forced raw material is reported as raw; if False, also report
			True when <is_trivial> is True;
		"""
		if not ignore_trivial and self.is_trivial():
			return True
		if self.is_forced_raw() or len(self.product_of) == 0:
			return True
		return False


	def is_multifurcation(self) -> bool:
		"""
		return True if Item has multiple source recipes, or if flag
		product_of_complex_recipe is True;
		"""
		return self.flags.product_of_complex_recipe\
			or (len(self.product_of) >= 2)


	def is_product_of_complex_recipe(self):
		"""
		return raw value of product_of_complex_recipe flag;
		"""
		return self.flags.product_of_complex_recipe


	def is_cyclic_product(self):
		"""
		return raw value of cyclic_product flag;
		"""
		return self.cyclic_product


	def is_trivial(self) -> bool:
		"""
		return raw value of trivial flag;
		"""
		return self.flags.trivial


	def is_forced_raw(self) -> bool:
		"""
		return raw value of forced_raw flag;
		"""
		return self.flags.forced_raw


	def set_product_of_complex_recipe(self, value: bool) -> None:
		"""
		set value of product_of_complex_recipe flag;
		"""
		self.flags.product_of_complex_recipe = value
		return


	def set_cyclic_product(self, value: bool) -> None:
		"""
		set value of cyclic_product flag;
		"""
		self.flags.cyclic_product = value
		return


	def set_trivial(self, value: bool) -> None:
		"""
		set value of trivial flag;
		"""
		self.flags.trivial = value
		return


	def set_forced_raw(self, value: bool) -> None:
		"""
		set value of forced_raw flag;
		"""
		self.flags.forced_raw = value
		return
