#!/usr/bin/env python3

import collections as _collections_m_
import warnings as _warnins_m_
import itertools as _itertools_m_
from . import recipe as _recipe_m_
from . import item as _item_m_
from . import text_label_encoder as _text_label_encoder_m_
from . import graph_util as _graph_util_m_
from . import coef_matrix as _coef_matrix_m_
from . import scipy_interface as _scipy_m_


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
		if self.has_recipe(recipe.name):
			warnins.warn("overwriting: %s" % str(recipe))
		if copy:
			self._recipes[recipe.name] = recipe.copy(net_yield)
		else:
			self._recipes[recipe.name] = recipe
		return


	def _setup_recipe_item_search_cache(self) -> None:
		"""
		(internal only) setup search database between Recipe/Item queries;
		in (4) ways:
		0) summarize Item collection appear in all Recipes;
		1) Recipes products -> Item collection;
		2) Item collection -> Recipe inputs;
		3) Recipe -> Recipe down/upstream dependencies;
		4) Item flags;
		5) check cyclic group; mark the unique products of the cyclic groups;

		results are stored in:
		self._items
		self._recipe_upstr
		self._recipe_dwstr
		"""
		self._items.clear()
		self._recipe_upstr.clear()
		self._recipe_dwstr.clear()
		# goal 0, 1, 2
		for recp in self.iterate_recipes(True):
			# put recipe name to the correct input_of/product_of list
			# based on the recipe inputs/products
			for i in recp.inputs.keys():
				self.get_item(i).input_of.add(recp.name)
			for i in recp.products.keys():
				self.get_item(i).product_of.add(recp.name)
		# goal 3, 4
		# link recipe upstream/downstream using Item
		# update Item product_of_complex_recipe flag
		for i in self.iterate_items(True):
			for _dw, _up in _itertools_m_.product(i.input_of, i.product_of):
				self._recipe_upstr.setdefault(_dw, set()).add(_up)
				self._recipe_dwstr.setdefault(_up, set()).add(_dw)
			_flag = any([(self.get_recipe(r).n_products() >= 2)
				for r in i.product_of])
			i.setflag_product_of_complex_recipe(_flag)
		# refresh encoders
		self.recipe_encoder.train(self.iterate_recipes())
		self.item_encoder.train(self.iterate_items())
		# for correctness, clear these data
		# since these are calculated upon linkages
		self._graph = None
		self._coef_mat = None
		# now deal with cyclic recipes
		self._cache_cyclic_recipe_groups()
		return


	# TODO: need a good name of this function
	def _cache_cyclic_recipe_groups(self):
		"""
		(internal only) resolve cyclic groups:
		1) identify all cyclic groups;
		2) check if all groups are bounded;
		3) identify unique products in these cyclic groups
		4) mark these Items' cyclic_product flag
		"""
		#print(len(self._recipes))
		cyclic_groups = self.get_graph().get_cyclic_vertex_groups()
		#print(cyclic_groups)
		#print(self.has_recipe("uranium-fuel-consumption"))
		for cyc in cyclic_groups:
			recps = self.recipe_encoder.decode(cyc)
			if self._is_cyclic_group_valid(recps):
				# now get all products of these recipes
				all_prods = self.extract_items_from_recipes(recps,\
					"product_only")
				# find these prods which are unique to the cycle
				# i.e. all recipes in prod.product_of is in the cycle
				for p in all_prods:
					p_obj = self.get_item(p)
					if all([r in recps for r in p_obj.product_of]):
						p_obj.setflag_cyclic_product(True)
						#print(p)
			else:
				_warnins_m_.warn("cyclic group '%s' detected, however, it seems\
					perpetual; cyclic optimization on this group is disabled"\
					% (",".join(recps)), UserWarning)
		return


	def _is_cyclic_group_valid(self, recipe_list: list) -> bool:
		"""
		(internal only) check cyclic group if is valid;
		the cyclic group is valid only if there is no trivial operation of some
		recipes (i.e. all zeros), such that all Items have non-positive output;
		i.e. the group must be "consuming" something, or, not perpetual;
		this can be checked with UNBOUNDED linear programming;
		"""
		recipe_list = sorted(recipe_list)
		n_recipes = len(recipe_list)
		assert n_recipes >= 2
		all_items = self.extract_items_from_recipes(recipe_list)
		all_items = sorted(all_items)
		n_items = len(all_items)
		coef_matrix = _coef_matrix_m_.\
			CoefficientMatrix((len(recipe_list), len(all_items)))
		for ir, rname in enumerate(recipe_list):
			recipe = self.get_recipe(rname)
			#print(rname)
			for iname, count in recipe.inputs.items():
				#print(iname)
				coef_matrix[ir, all_items.index(iname)] = -count
			for iname, count in recipe.products.items():
				#print(iname)
				coef_matrix[ir, all_items.index(iname)] = count
		# test using linprog
		A_T = -coef_matrix.T
		b_ub = _scipy_m_.zeros(n_items, dtype = float)
		c = _scipy_m_.ones(n_recipes, dtype = float)
		x_bounds = [(0, None)] * n_recipes
		# check linear programming
		res = _scipy_m_.linprog(c = c, A_ub = A_T, b_ub = b_ub, bounds = x_bounds)
		assert res.status in [0, 2, 3], res
		if (res.status == 0) and all(_scipy_m_.isclose(res.x, 0)):
			# good results; the only solution is trivial (all zeros)
			return True
		elif res.status == 2:
			# though not know how it is possible, but we still check
			raise RuntimeError(res)
		elif res.status == 3:
			# unbounded is failure
			return False
		return


	def refresh(self) -> None:
		"""
		refresh caches by recalculating from local Recipes data;
		necessary to ensure correctness after updating Recipes;
		"""
		# rescue manual flags since self._items will be refreshed
		forced_raws = self.query_items(lambda x: x.is_forced_raw())
		trivials = self.query_items(lambda x: x.is_trivial())
		# refresh
		self._setup_recipe_item_search_cache()
		# lazy load now
		#self._graph = self.to_graph()
		#self._coef_mat = self.to_coef_matrix()
		# reset rescued manual flags
		self.set_items_flag(forced_raws, lambda x: x.setflag_forced_raw(True))
		self.set_items_flag(trivials, lambda x: x.setflag_trivial(True))
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
		new = RecipeSet(self.iterate_recipes(True), net_yield = net_yield)
		# copy item manual falgs
		for query_expr, set_expr in [
				(lambda x: x.is_forced_raw(), lambda x: x.setflag_forced_raw(True)),
				(lambda x: x.is_trivial(), lambda x: x.setflag_trivial(True)),
			]:
			item_list = self.query_items(query_expr)
			new.set_items_flag(item_list, set_expr)
		assert len(self.item_encoder) != 0
		assert len(self.recipe_encoder) != 0
		#print(len(self.item_encoder))
		#print(len(self.recipe_encoder))
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


	def iterate_recipes(self, return_object = False) -> iter:
		"""
		return a iterator traversing all current Recipes
		"""
		if return_object:
			return self._recipes.values()
		else:
			return self._recipes.keys()


	def iterate_items(self, return_object = False) -> iter:
		"""
		return a iterator traversing all current Items
		"""
		if return_object:
			return self._items.values()
		else:
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


	def query_items(self,
			expr: callable
		) -> list:
		"""
		get a list of names of Items that evaluate True with <expr>;

		PARAMETERS
		----------
		expr:
			callable with signature Item -> bool;

		RETURNS
		-------
		list of Item names;
		"""
		return [i.name for i in filter(expr, self.iterate_items(True))]


	def set_items_flag(self,
			item_names: list,
			action: callable,
		) -> None:
		"""
		mark a given list of Items with flag <trivial>;

		PARAMETERS
		----------
		item_names:
			list of Item names;

		action:
			callable action to be applied, must with Item as only input
			argument;
		"""
		for i in item_names:
			action(self.get_item(i))
		return


	def verify(self) -> None:
		"""
		verify if Recipe/Items search db is complete and correct;

		EXCEPTIONS
		----------
		InvalidRecipeSetError: if failed check
		"""
		_item = lambda x: self.get_item(x)
		_recp = lambda x: self.get_recipe(x)
		# check for recipes-item connection
		for r, i in _itertools_m_.product(
			self.iterate_recipes(True), self.iterate_items(True)):
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
		assert len(self.item_encoder) != 0
		assert len(self.recipe_encoder) != 0
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


	def fetch_recipes_in_dependency(self,
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


	def extract_items_from_recipes(self,
			recipe_names: list,
			subset: str = "both",
		) -> set:
		"""
		return the set of all involved Items given a list of Recipe names;

		PARAMETERS
		----------
		recipe_names:
			a list of names of Recipes that to be processed;

		subset:
			the subset (inputs and/or products) to extract; acceptable values
			are 'input_only', 'product_only' and 'both'

		RETURNS
		-------
		a list of Item names that are extracted
		"""
		if subset == "both":
			subsetting = lambda x: (x.inputs.keys(), x.products.keys())
		elif subset == "input_only":
			subsetting = lambda x: (x.inputs.keys(), )
		elif subset == "product_only":
			subsetting = lambda x: (x.products.keys(), )
		else:
			raise ValueError("'subset' can only be one of: 'input_only', "\
				+ "'product_only' and 'both'")
		ret = set()
		for rn in recipe_names:
			ret.update(*subsetting(self.get_recipe(rn)))
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

			def fetch_recipes_in_dependency(self, *ka, **kw) -> dict:
				return self._rset_emb_recipe_set.\
					fetch_recipes_in_dependency(*ka, **kw)

			def extract_items_from_recipes(self, *ka, **kw) -> set:
				return self._rset_emb_recipe_set.\
					extract_items_from_recipes(*ka, **kw)
		return embed_c
