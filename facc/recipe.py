#!/usr/bin/env python3

import collections as _collections_m_


class InvalidRecipeError(RuntimeError):
	pass


class Recipe(object):
	pass


class Recipe(object):
	"""
	recipe of crafting items
	"""
	def __init__(self,
			inputs: dict,
			products: dict,
			category: str,
			craft_time: float = 0.5,
			name: str or None = None,
			*,
			net_yield: bool = False,
		) -> None:
		"""
		constructor of Recipe class, defining the crafting process of inputs
		to products;

		PARAMETERS
		----------
		inputs:
			dict with signature of "item_name": count;

		products:
			dict with signature of "item_name": count;

		category:
			str, recipe category (values not checked);

		craft_time:
			required time for each recipe exec;

		name:
			default to be the product name (if only one product), otherwise required;

		net_yield: 
			if True, shared items in inputs/products will be combined into net yield/consumtion;

		EXCEPTIONS
		----------
		ValueError: if name is neither provided nor derivable;
		"""
		super(Recipe, self).__init__()
		# collections.Counter alike dict
		# make values into float
		self.inputs = _collections_m_.Counter(inputs)
		self.products = _collections_m_.Counter(products)
		#
		self.craft_time = float(craft_time)
		self.category = str(category)
		# if name is None, try to derive from the product
		# derive is only valid if products list has only one item
		# else raise ValueError
		if name is None:
			if len(self.products) == 1:
				# this get the name of the only product
				name, = list(self.products.keys())
			else:
				raise ValueError(
					"'name' is required with non-single-product recipe")
		self.name = str(name)
		if net_yield:
			self.update_net_yield()
		# debugs
		assert all([v > 0 for v in self.inputs.values()]), "bad input count"
		assert all([v > 0 for v in self.products.values()]), "bad products count"
		assert self.craft_time > 0, "bad craft time"
		return


	def __str__(self):
		_in = ("+").join(["%.2f%s" % (v, k) for (k, v) in self.inputs.items()])
		_out = ("+").join(["%.2f%s" % (v, k) for (k, v) in self.products.items()])
		if not _in:
			_in = "NULL"
		if not _out:
			_out = "NULL"
		return "<%s object [%s] %s=>%s>" %\
			(type(self).__name__, self.name, _in, _out)


	def __repr__(self):
		return str(self)


	def update_net_yield(self) -> None:
		"""
		update itself inplace to remove any intersections between inputs and products;
		the net yield/consumption is calculated;
		"""
		shared = set(self.inputs).intersection(set(self.products))
		for i in shared:
			net = self.products[i] - self.inputs[i]
			if net == 0:
				# output = input
				del self.inputs[i]
				del self.products[i]
			elif net < 0:
				# net input
				self.inputs[i] = (-net)
				del self.products[i]
			else:
				# net output
				del self.inputs[i]
				self.products[i] = net
		return


	def copy(self, net_yield: bool = False) -> "Recipe":
		"""
		PARAMETERS
		----------
		net_yield:
			see Recipe.__init__() for more information;

		RETURNS
		-------
		a new Recipe instance;
		"""
		new = Recipe(
			inputs = self.inputs,
			products = self.products,
			craft_time = self.craft_time,
			category = self.category,
			name = self.name,
			net_yield = net_yield)
		return new


	def n_inputs(self) -> int:
		"""
		return number of input Items;
		"""
		return len(self.inputs)


	def n_products(self) -> int:
		"""
		return number of product Items;
		"""
		return len(self.products)
