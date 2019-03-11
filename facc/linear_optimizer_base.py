#!/usr/bin/env python3

import collections as _collections_m_
import numpy as _numpy_m_
from . import recipe_set as _recipe_set_m_


class OptimizationInfeasibleError(RuntimeError):
	pass


@_recipe_set_m_.RecipeSetEmbed()
class LinearOptimizerBase(object):
	_status_dict_ = {
		"success": "success",
		"trivial": "trivial",
		"fail": "fail",
	}

	"""
	basic helper functions and methods shared by all linear optimizer classes;
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
			Recipes dataset for optimization calculation;

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
		# see ProductionTree for info of this commenting out
		super(self._wrapped_class_original_, self).__init__()
		if not isinstance(recipe_set, _recipe_set_m_.RecipeSet):
			raise TypeError("'recipe_set' must be of type 'RecipeSet'")
		# override copy if force_net is set
		if force_net or copy:
			self.set_recipe_set(recipe_set.copy(force_net))
		else:
			self.set_recipe_set(recipe_set)
			self.get_recipe_set().verify()
		return


	def optimize(self, optim_goals: dict, *ka, **kw) -> (dict, dict, dict):
		"""
		optimizing over a dict of optimization goals;
		this is an interface function which should be overridden in subclasses;

		RETUNRS
		-------
		recipe_execs (dict in signature "recipe": execs):
			Recipe executions optimized by minimize sum of all raw inputs;

		raw_inputs (dict in signature "item": count):
			summary of raw input Items;

		wastings (dict in signature "item": count):
			summary of wasted items; wasting is innevitable in some cases when
			intermediates/side products cannot be balanced;
		"""
		raise NotImplementedError("not implemented base class method")


	def get_optimizing_coef_matrix(self,
			items: _collections_m_.Iterable,
		) -> (list, list, list, list, _numpy_m_.ndarray):
		"""
		slice a smaller coefficient matrix from that in original RecipeSet, yet
		still contains all related Recipes/Items; this helps reduce the
		equations set during optimization;

		PARAMETERS
		----------
		items:
			Item names, iterable;

		RETURNS
		-------
		recipe_names (list):
			sorted Recipe names corresponding to recipe_ids;

		recipe_ids (list):
			sliced Recipe indices compatible with bound RecipeSet.recipe_encoder;

		item_names (list):
			sorted Item names corresponding to item_ids;

		item_ids (list):
			sliced Item indices compatible with bound RecipeSet.item_encoder;

		coef_matrix (numpy.ndarray):
			sliced matrix;
		"""
		# input as a list of Items
		# first, retrieve all related recipes of this Item
		all_recipes = _collections_m_.ChainMap(\
			*[self.fetch_recipe_dependency(i, "up") for i in items])
		# second, recipes
		#   1. get names
		recipe_names = sorted(all_recipes.keys()) # sort is optional
		#   2. encode into ids
		recipe_ids = self.get_recipe_encoder().encode(recipe_names)
		# third, items
		#   1. get names
		item_names = self.extract_items_from_recipes(all_recipes.keys(),
			subset = "both")
		item_names = sorted(item_names) # sort is optional
		#   2. encode into ids
		item_ids = self.get_item_encoder().encode(item_names)
		# slice matrix
		mesh = _numpy_m_.ix_(recipe_ids, item_ids)
		coef_matrix = self.get_recipe_set().get_coef_matrix()[mesh]
		return recipe_names, recipe_ids, item_names, item_ids, coef_matrix


	@staticmethod
	def _remove_zero_counts(goals):
		"""
		(internal only) filter count zero targets in the dict; return a copy;
		"""
		assert isinstance(goals, dict)
		return {k: v for k, v in goals.items() if not _numpy_m_.isclose(v, 0)}
