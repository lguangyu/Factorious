#!/usr/bin/env python3

import warnings as _warnins_m_
import collections as _collections_m_
import numpy as _numpy_m_
import scipy as _scipy_m_
import scipy.optimize
del scipy # remove from name space, go with _scipy_m_
from . import recipe_set as _recipe_set_m_


class OptimizationInfeasibleError(RuntimeError):
	pass


@_recipe_set_m_.RecipeSetEmbed()
class LinearOptimizer(object):
	def __init__(self,
			recipe_set: _recipe_set_m_.RecipeSet,
			copy: bool = False,
			force_net: bool = False,
		) -> None:
		"""
		linear optimizer over a set of recipes;

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


	def optimize(self,
			optim_goals: dict,
			ignore_trivial: bool = False,
			scales: dict = {},
			*,
			tol: float = 1e-6,
			_show_warnings = False,
		) -> (dict, dict, dict):
		"""
		optimize over a set of products targets;

		PARAMETERS
		----------
		optim_goals (dict with signature "item": count):
			optimization goal:

		ignore_trivial:
			if True, ignore the <is_trivial> flag in each Item; if False, the
			<is_trivial> flag marks such Items as raw material and disables any
			optimization over them; see Item for more information;

		scales (dict with signature "item": <float>):
			defines extra flexible scaling
			factors applied to correct value coefficient of corresponding Items
			in the objective function; default value is 1.0 globally;
			NOTE: specify a scale factor for a particular Item overrides its
			<is_trivial> flag even <ignore_trivial> is not set;

		tol:
			float comparison tolerance;

		RETURNS
		-------
		recp_exec (dict in signature "recipe": execs):
			Recipe executions optimized by minimize sum of all raw inputs;

		raw (dict in signature "item": count):
			summary of raw input Items;

		wasting (dict in signature "item": count):
			summary of wasted items; wasting is innevitable in some cases when
			intermediates/side products cannot be balanced;
		"""
		# TODO:  break this function into two more easily testable ones
		# pre screening
		# remove zeros
		local_prods = optim_goals.copy()
		zeros_key = [k for k, v in local_prods.items()\
			if _numpy_m_.isclose(v, 0)]
		for k in zeros_key:
			del local_prods[k] # dict shape change
		########################################################################
		# results dicts
		rexe = _collections_m_.Counter()
		rawin = _collections_m_.Counter()
		waste = _collections_m_.Counter()
		# check empty, make explicit
		if not local_prods:
			return rexe, rawin, waste
		# prepare
		max_iter = 1000
		while True:
			# prepare
			recipe_names, recipe_ids, item_names, item_ids, coef_matrix\
				= self._get_optimizing_coef_matrix(local_prods.keys())
			A_T = coef_matrix.T
			# inputs for linear programming
			c, A_eq, b_eq, A_ub, b_ub, x_bounds, c_ids, eq_ids, ub_ids\
				= self._prepare_linear_programming(
					optim_goals = local_prods,
					ignore_trivial = ignore_trivial,
					scales = scales,
					recipe_names = recipe_names,
					recipe_ids = recipe_ids,
					item_names = item_names,
					item_ids = item_ids,
					A_T = A_T)
			# linear programming
			res = _scipy_m_.optimize.linprog(c,
				A_ub = A_ub, b_ub = b_ub,
				A_eq = A_eq, b_eq = b_eq,
				bounds = x_bounds, method = "simplex",
				options = {"maxiter": max_iter, "tol": tol})
			# check results
			if res.status == 0:
				break
			elif res.status == 1:
				if max_iter < 100000:
					max_iter = max_iter * 10
					continue
				else:
					raise OptimizationInfeasibleError(res.message)
			elif res.status == 2:
				# TODO: any solutions when infeasible?
				raise OptimizationInfeasibleError(res.message)
			else:
				raise OptimizationInfeasibleError(res.message)
		# summary
		# recipe execs
		for k, v in zip(recipe_names, res.x):
			if not _numpy_m_.isclose(v, 0):
				rexe.update({k: v})
		y_prod = _numpy_m_.dot(A_T, res.x.reshape(-1, 1)).squeeze()
		# raw inputs and wastings
		for i in c_ids:
			if not _numpy_m_.isclose(y_prod[i], 0):
				rawin.update({item_names[i]: -y_prod[i]})
		for i in ub_ids:
			if not _numpy_m_.isclose(y_prod[i], 0):
				waste.update({item_names[i]: y_prod[i]})
		return rexe, rawin, waste


	def _get_optimizing_coef_matrix(self,
			items: _collections_m_.Iterable,
		) -> (list, list, list, list, _numpy_m_.ndarray):
		"""
		(internal only) slice a smaller coefficient matrix from that in original
		RecipeSet, yet still contains all related Recipes/Items; this helps
		reduce the equations set during optimization;

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
		recipe_names = list(all_recipes.keys())
		recipe_names.sort() # sort is optional
		#   2. encode into ids
		recipe_ids = self.get_recipe_encoder().encode(recipe_names)
		# third, items
		#   1. get names
		item_names = list(self.extract_all_items(all_recipes.values()))
		item_names.sort() # sort is optional
		#   2. encode into ids
		item_ids = self.get_item_encoder().encode(list(item_names))
		# slice matrix
		mesh = _numpy_m_.ix_(recipe_ids, item_ids)
		coef_matrix = self.get_recipe_set().get_coef_matrix()[mesh]
		return recipe_names, recipe_ids, item_names, item_ids, coef_matrix


	def _prepare_linear_programming(self, *,
			optim_goals: dict,
			ignore_trivial: bool,
			scales: dict,
			# below are identical to _get_optimizing_coef_matrix output
			recipe_names: list,
			recipe_ids: list,
			item_names: list,
			item_ids: list,
			A_T: _numpy_m_.ndarray,
		) -> "...":
		"""
		(internal only) preparing the input vectors/matrices for 'linprog';
		namely:
			c, A_eq, b_eq, A_ub, b_ub, x_bounds;
		also:
			c_ids, eq_ids, ub_ids;
		"""
		n_recipes = len(recipe_ids)
		n_items = len(item_ids)
		########################################################################
		# A_eq, b_eq: these are optim_goals
		cond = [i in optim_goals for i in item_names]
		eq_ids = _numpy_m_.nonzero(list(cond))[0]
		A_eq = A_T[eq_ids]
		assert A_eq.shape == (len(eq_ids), A_T.shape[1]), A_eq.shape
		b_eq = map(lambda x: optim_goals[item_names[x]], eq_ids)
		b_eq = _numpy_m_.asarray(list(b_eq), dtype = float)
		assert b_eq.shape == (len(eq_ids), )
		########################################################################
		# c: is the raw inputs, including trivial if not ignored
		cond = [self.get_item(i).is_raw(ignore_trivial) for i in item_names]
		c_ids = _numpy_m_.nonzero(list(cond))[0]
		#assert 
		# coef, a.k.a. weight of each input
		def lookup_coef(cid):
			w = scales.get(item_names[cid], None)
			if w is not None:
				return w
			if (not ignore_trivial)\
				and (self.get_item(item_names[cid]).is_trivial):
				return 0.0
			return 1.0
		c_coef = _numpy_m_.asarray(list(map(lookup_coef, c_ids)), dtype = float)
		assert c_coef.shape == (len(c_ids), ), c_coef.shape
		# combine multiple inputs
		c = _numpy_m_.dot(c_coef, A_T[c_ids, :])
		assert c.shape == (A_T.shape[1], ), "bad c shape"
		# 'linprog' only minimizes, however inputs are negative
		# inverse so let 'linprog' maximize 'postitive' values
		c = -c
		########################################################################
		# A_ub, b_ub
		# ub_ids = ids not in eq_ids nor in c_ids
		all_ids = range(n_items)
		ub_ids = filter(lambda x: (x not in eq_ids) and (x not in c_ids), all_ids)
		ub_ids = _numpy_m_.asarray(list(ub_ids))
		assert len(ub_ids) + len(eq_ids) + len(c_ids) == n_items, "bad ub_ids"
		b_ub = _numpy_m_.zeros(len(ub_ids), dtype = float)
		# b_ub are 'upper bound', which value are 0's
		# here we need 0's as 'lower bound'
		# inverse A_ub again to make this happed
		A_ub = -A_T[ub_ids, :]
		# linear programming
		x_bounds = [(0, None)] * n_recipes
		#print(c_ids, [item_names[i] for i in c_ids])
		#print(eq_ids, [item_names[i] for i in eq_ids])
		#print(ub_ids, [item_names[i] for i in ub_ids])
		#print("--")
		#print(A_T)
		#print(item_names)
		#print(recipe_names)
		#print(A_eq)
		#print(b_ub)
		#print(x_bounds)
		return c, A_eq, b_eq, A_ub, b_ub, x_bounds, c_ids, eq_ids, ub_ids


	@staticmethod
	def extract_all_items(recipes: list) -> None:
		"""
		return the set of all involved Items given a list of Recipes
		"""
		ret = set()
		for r in recipes:
			ret.update(r.inputs.keys(), r.products.keys())
		return ret
