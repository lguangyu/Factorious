#!/usr/bin/env python3

import collections as _collections_m_
from . import recipe_set as _recipe_set_m_
from . import linear_optimizer as _linear_optimizer_m_


class TargetItemNotFoundError(LookupError):
	pass


@_recipe_set_m_.RecipeSetEmbed()
class ProductionTree(object):
	"""
	solve the production tree using given recipe set;
	"""
	def __init__(self,
			recipe_set: _recipe_set_m_.RecipeSet,
			copy: bool = False,
			force_net: bool = False,
		) -> None:
		"""
		PARAMETERS
		----------
		recipe_set:
			Recipes dataset;

		copy:
			if True, RecipeSet is copied locally;
			if False, RecipeSet is not copied but a verify() check is enforced;

		force_net:
			enforce all Recipes are net; if False, keep unchanged; if True, a
			local copy of Recipes are enforced (i.e. overrides <copy>);
			see Recipe.copy() for more information;

		EXCEPTIONS
		----------
		TypeError: if recipe_set is not of type RecipeSet;
		"""
		# OK, below line:
		#super(ProductionTree, self).__init__()
		# causes error with class decorator
		# due to now ProductionTree -> implicitly changed to wrapper class
		# thus super(ProductionTree, self)__init__()
		# actually calls (real)ProductionTree.__init__(),
		# which require arguments and caused error
		# super(ProductionTree).__init__() will work but don't understand yet
		# the solution used below is by passing the original class
		# from the decorator, as a class attribute
		super(self._wrapped_class_original_, self).__init__()
		if not isinstance(recipe_set, _recipe_set_m_.RecipeSet):
			raise TypeError("'recipe_set' must be of type 'RecipeSet'")
		# construct a new recipe set, with each recipe squeezed
		if force_net or copy:
			self.set_recipe_set(recipe_set.copy(force_net))
		else:
			self.set_recipe_set(recipe_set)
			self.get_recipe_set().verify()
		# below is the targets stub
		self._targets = _collections_m_.Counter()
		# below is calculated as the execution times for each enrolled recipe
		# format signature is "recipe": exec_count
		self._recipe_execs = _collections_m_.Counter()
		# below is the dict of items that must be solved using optimizations
		# format signature is "item": count
		# these items are optimized in final step
		self._optim_items = _collections_m_.Counter()
		# below is the raw material input for target
		# format signature is "item": count
		self._raw_inputs = _collections_m_.Counter()
		# below is the wated material
		# format signature is "item": count
		self._wastings = _collections_m_.Counter()
		self.clear_current_tree()
		return


	def clear_current_tree(self) -> None:
		"""
		clear all cached results for a clean new calculation;
		"""
		self._targets.clear()
		self._recipe_execs.clear()
		self._optim_items.clear()
		self._raw_inputs.clear()
		self._wastings.clear()
		return


	def _recursion_add_targe(self,
			item_name: str,
			count: float,
		) -> None:
		"""
		(internal only) recusively add an Item production target,
		and all uptream dependencies;

		PARAMETERS
		----------
		item_name:
			item_name of the production target;

		count:
			count to produce;
		"""
		# initialize
		stack = [(item_name, count)]
		# stack recursion
		while len(stack):
			_iname, _icount = stack.pop()
			# get item instance
			_item = self.get_item(_iname)
			if _item.is_raw():
				# raw material is added to _raw_inputs
				self._raw_inputs.update({_iname: _icount})
				continue
			elif _item.has_multiple_source() or _item.need_optimize:
				# add to _optim_items for later optimization
				self._optim_items.update({_iname: _icount})
				continue
			else:
				# the item can only be produced in one source
				# get recipe
				_rname, = _item.product_of # only one element, safe
				_recipe = self.get_recipe(_rname)
				# update the recipe execution
				_rexec = _icount / _recipe.products[_iname]
				self._recipe_execs.update({_rname: _rexec})
				# update all recipe inputs
				for i, v in _recipe.inputs.items():
					stack.append((i, v * _rexec))
				# update all recipe products
				for i, v in _recipe.products.items():
					# critical to check the product name
					# only push to stack if not same to _iname
					if i != _iname:
						# NOTE: the count is negative here
						stack.append((i, -v * _rexec))
		return


	def add_target(self,
			item_name: str,
			count: float,
		) -> None:
		"""
		recusively add an Item production target and all its dependencies to
		currently cached calculation results;

		PARAMETERS
		----------
		item_name:
			item_name of the production target;

		count:
			count to produce;

		EXCEPTIONS
		----------
		TargetItemNotFoundError: if target item is not found in known recipes;
		"""
		if not self.has_item(item_name):
			raise TargetItemNotFoundError("bad item: '%s'" % item_name)
		# add to targets stub
		self._targets.update({item_name: count})
		self._recursion_add_targe(item_name, count)
		return


	def resolve_optimization_items(self, optim_args = {}) -> None:
		"""
		flush current cache of multi-srouce Items and run optimization; results
		are automatically updated to cache;
		"""
		linopt = _linear_optimizer_m_.LinearOptimizer(self.get_recipe_set(),
			copy = False)
		op_exec, op_raw, op_wst = linopt.optimize(self._optim_items,
			**optim_args)
		for src, dest in zip([op_exec, op_raw, op_wst],
			[self._recipe_execs, self._raw_inputs, self._wastings]):
			for k, v in src.items():
				dest.update({k: v})
		self._optim_items.clear()
		return


	def calculate_targets(self,
			targets: dict,
			clean: bool = True,
			*,
			optim_args = {},
		) -> tuple:
		"""
		set the production targets and construct the production tree; multi-
		source Items are optimized and flushed; return the calculated results in
		list of dicts;

		PARAMETERS
		----------
		targets:
			dict of targets in signature "product": count;

		clean:
			start a new calculation by clear old results;

		optim_args:
			extra parameters passed to LinearOptimizer.optimize();

		RETURNS
		-------
		see ProductionTree.get_current_tree()
		"""
		if clean:
			self.clear_current_tree()
		for p, c in targets.items():
			self.add_target(str(p), float(c))
		self.resolve_optimization_items(optim_args)
		return self.get_current_tree()


	def get_current_tree(self) -> (dict, dict, dict, dict):
		"""
		return all current calculation results;

		RETURNS
		-------
		targets (dict in signature "item": count):
			original targets input for these results;

		recipe_execs (dict of signature "recipe": exec):
			Recipe executions with optimized by minimize sum of all raw inputs;

		raw_inputs (dict in signature "item": count):
			summary of raw input Items;

		wasting (dict in signature "item": count):
			summary of wasted items; wasting is innevitable in some cases when
			intermediates/side products cannot be balanced;
		"""
		return (self._targets.copy(), self._recipe_execs.copy(),
			self._raw_inputs.copy(), self._wastings.copy())


	def get_item_summary(self) -> (dict, dict):
		"""
		summary Item produced/consumed according to current recipe executions;

		RETURNS
		-------
		sum_consumption (dict in signature "item": count):
			all consumed Items, including intermediates;

		sum_production (dict in signature "item": count):
			all produced Items, including intermediates;
		"""
		sum_cons = _collections_m_.Counter()
		sum_prod = _collections_m_.Counter()
		for rname, rexec in self._recipe_execs.items():
			recipe = self.get_recipe(rname)
			for iname, count in recipe.inputs.items():
				sum_cons.update({iname: count * rexec})
			for iname, count in recipe.products.items():
				sum_prod.update({iname: count * rexec})
		return sum_cons, sum_prod
