#!/usr/bin/env python3

import collections as _collections_m_
import warnings as _warnins_m_
import itertools as _itertools_m_
from . import recipe as _recipe_m_
from . import item as _item_m_
from . import text_label_encoder as _text_label_encoder_m_
from . import graph_util as _graph_util_m_
from . import coef_matrix as _coef_matrix_m_


class InvalidRecipeSetError(ValueError):
	pass


class _UserDefaultDict(_collections_m_.defaultdict):
	def __missing__(self, key):
		if not self.default_factory:
			super(_UserDefaultDict, self).__missing__(key)
		else:
			self[key] = value = self.default_factory(key)
			return value


class RecipeSet(object):
	"""
	collection of Recipes and involved Items for organizing and searching;
	"""
	def __init__(self,
			recipe_list: list or "iterator",
			copy: bool = True,
			net_yield: bool = False,
		) -> None:
		"""
		PARAMETERS
		----------
		recipe_list:
			list of Recipe's;

		copy:
			make local copies of recipes;

		net_yield:
			if True, make all recipes in the list are net;
			see Recipe.__init__() for more information;
			this parameter only affects when copy=True;
		"""
		# self._recipes is a dict of "recipe_name": Recipe()
		self._recipes = {}
		# self._items is a dict of "item_name": Item()
		self._items = _UserDefaultDict(lambda x: _item_m_.Item(x))
		# self._recipe_upstr/dwstr are dicts of "recipe_name": "recipe_name"
		self._recipe_upstr = _collections_m_.defaultdict(set)
		self._recipe_dwstr = _collections_m_.defaultdict(set)
		# recipe/item name encoders
		self.recipe_encoder = _text_label_encoder_m_.TextLabelEncoder()
		self.item_encoder = _text_label_encoder_m_.TextLabelEncoder()
		# matrix representations, lazy load
		self._graph = None
		self._coef_mat = None
		# data filling in
		self.is_net_yield = net_yield
		for r in recipe_list:
			self._add_recipe(r, copy, net_yield)
		# init caches
		self.refresh()
		return


	def _add_recipe(self,
			recipe: _recipe_m_.Recipe,
			copy: bool = True,
			net_yield: bool = False,
		) -> None:
		"""
		(internal only) add a Recipe to the collection;

		PARAMETERS
		----------
		see RecipeSet.__init__() for more information;
		"""
		if not isinstance(recipe, _recipe_m_.Recipe):
			raise TypeError("'recipe' must be type of 'Recipe'")
		# dict key overwrite warning
		if recipe.name in self._recipes:
			warnins.warn("overwriting: %s" % str(recipe))
		if copy:
			self._recipes[recipe.name] = recipe.copy(net_yield)
		else:
			self._recipes[recipe.name] = recipe
		return


	def _link_recipes(self) -> None:
		"""
		(internal only) link recipes in (3) ways:
		0) summarize item collection appear in all recipes;
		1) recipes products -> item collection;
		2) item collection -> recipe inputs;
		3) recipe -> recipe down/upstream dependencies;

		results are stored in:
		self._items
		self._recipe_upstr
		self._recipe_dwstr
		"""
		self._items.clear()
		self._recipe_upstr.clear()
		self._recipe_dwstr.clear()
		# goal 0, 1, 2
		for recp in self._recipes.values():
			# force products of multi-product recipes to be optimized
			is_multiprod_recipe = len(recp.products) >= 2
			# put recipe name to the correct input_of/product_of list
			# based on the recipe inputs/products
			for i in recp.inputs.keys():
				self.get_item(i).input_of.add(recp.name)
			for i in recp.products.keys():
				self.get_item(i).product_of.add(recp.name)
				if is_multiprod_recipe:
					# NOTE: do NOT do i.need_optimize = is_multiprod_recipe
					self.get_item(i).need_optimize = True
		# goal 3
		for i in self._items.values():
			for _dw, _up in _itertools_m_.product(i.input_of, i.product_of):
				self._recipe_upstr.setdefault(_dw, set()).add(_up)
				self._recipe_dwstr.setdefault(_up, set()).add(_dw)
		# for correctness, clear these data
		# since these are calculated upon linkages
		self._graph = None
		self._coef_mat = None
		return


	def refresh(self) -> None:
		"""
		refresh caches by recalculating from local Recipes data;
		necessary to ensure correctness after updating Recipes;
		"""
		# rescue trivial flags since self._items will be refreshed
		trivials = self.get_trivials()
		# refresh
		self._link_recipes()
		self.recipe_encoder.train(self._recipes.keys())
		self.item_encoder.train(self._items.keys())
		# lazy load now
		#self._graph = self.to_graph()
		#self._coef_mat = self.to_coef_matrix()
		self.set_trivials(trivials)
		return


	def copy(self, net_yield: bool = None) -> "RecipeSet":
		"""
		reconstruct a RecipeSet with identical Recipes to caller;
		all Recipes in collection are copied from their original;

		PARAMETERS
		----------
		net_yield:
			if None, use inherited value; override otherwise;
		"""
		if net_yield is None:
			net_yield = self.is_net_yield
		new = type(self)(self._recipes.values(), net_yield = net_yield)
		# copy item trivial falgs
		new.set_trivials(self.get_trivials())
		return new


	def get_recipe(self,
			recipe_name: str,
		) -> _recipe_m_.Recipe:
		"""
		get the Recipe instance by name;
		"""
		return self._recipes[recipe_name]


	def get_item(self,
			item_name: str,
		) -> _item_m_.Item:
		"""
		get the Item instance by name;
		"""
		return self._items[item_name]


	def iterate_recipes(self) -> iter:
		"""
		return a iterator traversing names of all current Recipes
		"""
		return self._recipes.keys()


	def iterate_items(self) -> iter:
		"""
		return a iterator traversing names of all current Items
		"""
		return self._items.keys()


	def has_recipe(self,
			recipe_name: str,
		) -> bool:
		"""
		return True if <recipe_name> exists;
		"""
		return recipe_name in self._recipes


	def has_item(self,
			item_name: str,
		) -> bool:
		"""
		return True if <item_names> exists;
		"""
		return item_name in self._items


	def set_trivials(self,
			item_names: list,
			is_trivial: bool = True,
		) -> None:
		"""
		mark a given Item to be with flag <is_trivial>;

		PARAMETERS
		----------
		item_names:
			list of Item names;

		is_trivial:
			if True, these Items are marked as raw input;
		"""
		for i in item_names:
			self.get_item(i).is_trivial = is_trivial
		return


	def get_trivials(self) -> list:
		"""
		get a list of Item names that are marked as <is_trivial>

		RETURNS
		-------
		list of Item names
		"""
		return [i.name for i in self._items.values() if i.is_trivial]


	def remova_all_trivial_flags(self) -> None:
		"""
		set all Items' <is_trivial> flag to be False;
		"""
		for i in self._items.values():
			i.is_trivial = False
		return


	def verify(self) -> None:
		"""
		verify if Recipe and Items linkage is complete and correct;

		EXCEPTIONS
		----------
		InvalidRecipeSetError: if failed check
		"""
		_item = lambda x: self.get_item(x)
		_recp = lambda x: self.get_recipe(x)
		# check for recipes-item connection
		for r, i in _itertools_m_.product(
			self._recipes.values(), self._items.values()):
			if (i.name in r.products) != (r.name in i.product_of):
				break
			if (i.name in r.inputs) != (r.name in i.input_of):
				break
		else:
			return
		raise InvalidRecipeSetError("broken integrity: r'%s' : i'%s'" %\
			(r.name, i.name))
		return


	def to_graph(self) -> _graph_util_m_.UnweightedDirectedGraph:
		"""
		construct an UnweightedDirectedGraph representing recipe structure base
		on the input/output dependencies; returned graph is represent in an N by
		N boolean array, where A_ij = True if <Recipe i> has any product that is
		input of <Recipe j>, False otherwise;

		RETURNS
		-------
		construced graph (bool 2-d);
		"""
		n_recipes = len(self._recipes)
		# create an all-zero graph
		graph = _graph_util_m_.UnweightedDirectedGraph(n_recipes)
		# put data in
		for rid, rname in enumerate(self.recipe_encoder):
			# fetch connected recipe names from self._recipe_dwstr
			conns = list(self._recipe_dwstr[rname])
			# encode recipe names to ids then update
			graph[rid, self.recipe_encoder.encode(conns)] = True
		return graph


	def to_coef_matrix(self) -> _coef_matrix_m_.CoefficientMatrix:
		"""
		construct a coefficient matrix representing the Recipes input and yield;
		each row is a Recipe, encoding for columns as coefficiets of different
		Items;

		RETURNS
		-------
		constructed matrix (float 2-d);
		"""
		n_recipes = len(self._recipes)
		n_items = len(self._items)
		coef_mat = _coef_matrix_m_.CoefficientMatrix((n_recipes, n_items))
		for rname, recp in self._recipes.items():
			i, = self.recipe_encoder.encode([rname])
			for iname, count in recp.inputs.items():
				j, = self.item_encoder.encode([iname])
				coef_mat[i, j] = -count
			for iname, count in recp.products.items():
				j, = self.item_encoder.encode([iname])
				coef_mat[i, j] = count
		return coef_mat


	def get_graph(self) -> _graph_util_m_.UnweightedDirectedGraph:
		"""
		return the graph representation of this RecipeSet (lazy load);
		"""
		if self._graph is None:
			self._graph = self.to_graph()
		return self._graph


	def get_coef_matrix(self) -> _coef_matrix_m_.CoefficientMatrix:
		"""
		return the coefficient matrix of this RecipeSet (lazy load);
		"""
		if self._coef_mat is None:
			self._coef_mat = self.to_coef_matrix()
		return self._coef_mat


	def fetch_recipe_dependency(self,
			item_name: str,
			direction: "up" or "down",
		) -> dict:
		"""
		fetch all Recipes with dependency to given Item, both directly and
		indirectly;

		PARAMETERS
		----------
		item:
			name of the start item to traverse;
		
		direction:
			direction to traverse; "up" fetches all prerequites, while "down"
			fetches towards consumers;

		RETURNS
		-------
		a dict in signature "recipe": Recipe
		"""
		if direction == "up":
			# in stack_init, copy() is necessary
			stack_init = lambda x: self.get_item(x).product_of.copy()
			traverse = lambda x: self._recipe_upstr[x]
		elif direction == "down":
			stack_init = lambda x: self.get_item(x).input_of.copy()
			traverse = lambda x: self._recipe_dwstr[x]
		else:
			raise ValueError("unrecognized 'direction' value '%s'"\
				% direction)
		ret = dict()
		# here using the set as stack
		stack = stack_init(item_name)
		while stack:
			rname = stack.pop()
			if rname in ret:
				continue
			else:
				ret[rname] = self.get_recipe(rname)
				stack.update(traverse(rname))
		return ret


class RecipeSetEmbed(object):
	"""
	class decorator;
	embed a RecipeSet instance as attribute to the decorated class, providing
	basic Recipe/Item access interface short-cuts;
	"""
	def __init__(self):
		super(RecipeSetEmbed, self).__init__()
		return


	def __call__(self, cls):
		class embed_c(cls):
			_wrapped_class_original_ = cls

			def set_recipe_set(self, recipe_set: RecipeSet) -> None:
				"""
				set embeded RecipeSet object
				"""
				self._rset_emb_recipe_set = recipe_set
				return

			def get_recipe_set(self) -> RecipeSet:
				"""
				get embeded RecipeSet object
				"""
				return self._rset_emb_recipe_set

			def get_recipe_encoder(self) -> _text_label_encoder_m_.TextLabelEncoder:
				return self._rset_emb_recipe_set.recipe_encoder

			def get_item_encoder(self) -> _text_label_encoder_m_.TextLabelEncoder:
				return self._rset_emb_recipe_set.item_encoder

			####################################################################
			# below are wrapped short-cut interface to RecipeSet object
			def get_recipe(self, *ka, **kw) -> _recipe_m_.Recipe:
				return self._rset_emb_recipe_set.get_recipe(*ka, **kw)

			def get_item(self, *ka, **kw) -> _item_m_.Item:
				return self._rset_emb_recipe_set.get_item(*ka, **kw)

			def has_recipe(self, *ka, **kw) -> bool:
				return self._rset_emb_recipe_set.has_recipe(*ka, **kw)

			def has_item(self, *ka, **kw) -> bool:
				return self._rset_emb_recipe_set.has_item(*ka, **kw)

			def iterate_recipes(self, *ka, **kw) -> iter:
				return self._rset_emb_recipe_set.iterate_recipes(*ka, **kw)

			def iterate_items(self, *ka, **kw) -> iter:
				return self._rset_emb_recipe_set.iterate_items(*ka, **kw)

			def set_trivials(self, *ka, **kw) -> None:
				self._rset_emb_recipe_set.set_trivials(*ka, **kw)
				return

			def get_trivials(self, *ka, **kw) -> list:
				return self._rset_emb_recipe_set.get_trivials(*ka, **kw)

			def remova_all_trivial_flags(self, *ka, **kw) -> None:
				self._rset_emb_recipe_set.remova_all_trivial_flags(*ka, **kw)
				return

			def fetch_recipe_dependency(self, *ka, **kw) -> dict:
				return self._rset_emb_recipe_set.fetch_recipe_dependency(*ka, **kw)
		return embed_c
