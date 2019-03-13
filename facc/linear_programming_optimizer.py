#!/usr/bin/env python3

import warnings as _warnins_m_
import collections as _collections_m_
from . import abc as _abc_m_
from . import linear_optimizer_base as _linear_optimizer_base_m_
from . import scipy_interface as _scipy_m_


class LinearProgrammingParam(_abc_m_.ProtectedAttributeHolder):
	"""
	attribute holder for linear programming input
	"""
	pass


class LinearProgrammingOptimizer(_linear_optimizer_base_m_.LinearOptimizerBase):
	"""
	optimizer for Items have multiple source recipes, from cyclic recipe paths,
	or recipes have multiple products;
	"""
	def __init__(self, *ka, **kw) -> None:
		super(LinearProgrammingOptimizer, self).__init__(*ka, **kw)
		return


	def optimize(self,
			optim_goals: dict,
			optim_args,
			*,
			_show_warnings = False, # curretly not used
		) -> (dict, dict, dict):
		"""
		optimize over a set of products targets;

		PARAMETERS
		----------
		optim_goals (dict with signature "item": count):
			optimization goal:

		weights (defaultdict with signature "item": <float>):
			defines extra flexible scaling factors applied to correct value
			coefficient of corresponding Items in the objective function;
			default value of defaultdict is forced reset to 1.0;
			NOTE: specify a scale factor for a particular Item overrides its
			<is_trivial> flag even <ignore_trivial> is not set;

		no_cyclic:
			if True, disables cyclic optimization;

		ignore_trivial:
			if True, ignore the <is_trivial> flag in each Item; if False, the
			<is_trivial> flag marks such Items as raw material and disables any
			optimization over them; see Item for more information;

		tol:
			float comparison tolerance;

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
		# pre screening
		# remove zeros
		goals_local = self._remove_zero_counts(optim_goals)
		########################################################################
		# results dicts
		rexe = _collections_m_.Counter()
		rawin = _collections_m_.Counter()
		waste = _collections_m_.Counter()
		# check empty, make explicit
		if not goals_local:
			return rexe, rawin, waste
		########################################################################
		# prepare
		param = None
		max_iter = 1000
		# these are used when infeasible encountered
		#refined_level = 0
		# if still infeasible at refine_max_level, raise error
		#refine_max_level = 1
		########################################################################
		# fetch data
		optim_data = self.fetch_optimization_data(goals_local.keys())
		# update weights, the weights dict is in optim_args
		self._update_weights_in_optim_args(optim_args, optim_data)
		while True:
			# inputs for linear programming
			# generate param if None
			if not param:
				param = self._prepare_linear_programming(
					optim_goals = goals_local,
					optim_data = optim_data,
					**optim_args)
			# linear programming
			res = _scipy_m_.linprog(
				param.c,
				A_ub = param.A_cub,
				b_ub = param.b_cub,
				A_eq = param.A_eq,
				b_eq = param.b_eq,
				bounds = param.x_bounds,
				method = "simplex",
				options = {"maxiter": max_iter, "tol": optim_args["tol"]})
			#print("c_ids", param.c_ids)
			#print([optim_data.item_names[i] for i in param.c_ids])
			#print("eq_ids", param.eq_ids)
			#print([optim_data.item_names[i] for i in param.ub_ids])
			#print("--")
			#print("c", param.c)
			#print(optim_data.A_T)
			#print("in", optim_data.item_names)
			#print("rn", optim_data.recipe_names)
			#print("A_eq\n", param.A_eq)
			#print("b_eq", param.b_eq)
			#print("A_ub\n", param.A_ub)
			#print("b_ub", param.b_ub)
			#print("xb", param.x_bounds)
			#print("x", res.x)
			#print("yield", _scipy_m_.dot(optim_data.A_T, res.x.reshape(-1, 1)))
			#print(res.x)
			# check results
			if res.status == 0:
				# success
				break
			elif res.status == 1:
				# hit maxiter
				if max_iter < 100000:
					max_iter = max_iter * 10
					continue
			elif res.status == 2:
				# infeasible
				# TODO: any redemption when infeasible?
				# potential one solution here, refine the restrictions
				#if refined_level < refine_max_level:
				refine_success, param = self._refine_restrictions(
					old_param = param,
					optim_goals = goals_local,
					optim_data = optim_data,
					**optim_args)
					#ignore_trivial = ignore_trivial,
					#weights = weights,
				if refine_success:
					# use refined parameters for another trial
					continue
			# NOTE: if not hit break or continue, will end up here
			raise _linear_optimizer_base_m_.\
				OptimizationInfeasibleError(res)
		# summary
		# recipe execs
		for k, v in zip(optim_data.recipe_names, res.x):
			if not _scipy_m_.isclose(v, 0):
				rexe.update({k: v})
		y_prod = _scipy_m_.dot(optim_data.A_T, res.x.reshape(-1, 1)).squeeze()
		# raw inputs and wastings
		for i in param.c_ids:
			if not _scipy_m_.isclose(y_prod[i], 0):
				rawin.update({optim_data.item_names[i]: -y_prod[i]})
		for i in param.ub_ids:
			if not _scipy_m_.isclose(y_prod[i], 0):
				waste.update({optim_data.item_names[i]: y_prod[i]})
		return rexe, rawin, waste


	def _update_weights_in_optim_args(self,
			optim_args: dict,
			optim_data: _linear_optimizer_base_m_.LinearOptimizerAttributeSet,
		) -> None:
		"""
		(internal only) determine the weight coefficient for calculating the
		vector c;
		"""
		ignore = optim_args["ignore_trivial"]
		wts = _collections_m_.defaultdict(lambda : 1.0,\
			optim_args.get("weights", None))
		for k in optim_data.item_names:
			# update trivial items with values 0 only if
			# 1) not set yet, and
			# 2) ignore_trivial is False, and
			# 3) this item is marked trivial
			if (k not in wts) and (not ignore) and self.get_item(k).is_trivial():
				wts[k] = 0.0
			# no need to set others
		# replace original wts
		optim_args["weights"] = wts
		return


	def _prepare_linear_programming(self, **kw) -> LinearProgrammingParam:
		"""
		prepare a full set of linear programming parameters
		"""
		ids_set = self._split_restriction_sections(**kw)
		param = self._finalize_linear_programming_params(*ids_set, **kw)
		return param


	def _split_restriction_sections(self,
			optim_goals: dict,
			optim_data: _linear_optimizer_base_m_.LinearOptimizerAttributeSet,
			# below are passed with **optim_args
			ignore_trivial: bool = False,
			**kw, # other unused args passed with **optim_args
		) -> LinearProgrammingParam:
		"""
		(internal only) find sections to determine:
			c_ids, eq_ids, ub_ids;
		used to finally determine the matrices and objective functions in linear
		programming;

		this function serves as the 'front end' of _prepare_linear_programming;
		"""
		_opt = optim_data
		n_recipes = len(_opt.recipe_ids)
		n_items = len(_opt.item_ids)
		# boolean 1-d array to indices array
		bool2index = lambda x: _scipy_m_.nonzero(x)[0]
		########################################################################
		# mask each sub matrix by conditions
		# c: is the raw inputs, including trivial if not ignored
		c_bool = [self.get_item(i).is_raw(ignore_trivial) for i in _opt.item_names]
		# A_eq, b_eq: these are optim_goals
		eq_bool = [i in optim_goals for i in _opt.item_names]
		# A_ub, b_ub
		# ub_ids = ids not in eq_ids nor in c_ids
		ub_bool = _scipy_m_.logical_not(_scipy_m_.logical_or(c_bool, eq_bool))
		########################################################################
		# then bool to ids
		# though boolean array can also be used to slice matrix, in the summary
		# phase after linear programming, we prefer using ids
		c_ids = bool2index(c_bool)
		eq_ids = bool2index(eq_bool)
		ub_ids = bool2index(ub_bool)
		assert len(c_ids) + len(eq_ids) + len(ub_ids) == n_items,\
			"c_ids/ub_ids len:" + str([len(c_ids), len(ub_ids)])
		assert len(eq_ids) == len(optim_goals), "eq_ids shape:" + str(eq_ids.shape)
		return c_ids, eq_ids, ub_ids


	def _finalize_linear_programming_params(self, c_ids, eq_ids, ub_ids, *,
			optim_data: _linear_optimizer_base_m_.LinearOptimizerAttributeSet,
			optim_goals: dict,
			# below are passed with **optim_args
			weights: dict = _collections_m_.defaultdict(lambda : 1.0),
			no_cyclic: False,
			ignore_trivial: bool = False,
			**kw, # other unused args passed with **optim_args
		) -> LinearProgrammingParam:
		"""
		(internal only) by given:
			c_ids, eq_ids, ub_ids;
		do dirty works to prepare the input vectors/matrices for 'linprog',
		namely:
			c, A_eq, b_eq, A_ub, b_ub, x_bounds;

		this function serves as the 'back end' of _prepare_linear_programming;
		"""
		_opt = optim_data
		n_recipes = len(_opt.recipe_ids)
		n_items = len(_opt.item_ids)
		########################################################################
		# then use ids to slice A_T
		A_c, A_eq, A_ub = self._batch_slice(_opt.A_T, c_ids, eq_ids, ub_ids)
		A_ub = -A_ub # lower bound (0) -> upper bound (0)
		assert A_c.shape == (len(c_ids), n_recipes), "A_c shape:" + str(A_c.shape)
		assert A_eq.shape == (len(eq_ids), n_recipes), "A_eq shape:" + str(A_eq.shape)
		assert A_ub.shape == (len(ub_ids), n_recipes), "A_ub shape:" + str(A_ub.shape)
		########################################################################
		# b_eq and b_ub
		b_inames = [_opt.item_names[i] for i in eq_ids]
		b_eq = _scipy_m_.asarray([optim_goals[i] for i in b_inames], dtype = float)
		b_ub = _scipy_m_.zeros(len(ub_ids), dtype = float)
		assert len(b_eq) == len(eq_ids), "b_eq shape:" + str(b_eq.shape)
		########################################################################
		# c, first find weights of each item
		c_coef = [weights[_opt.item_names[i]] for i in c_ids]
		assert len(c_coef) == len(c_ids), "c_coef len:" + str(len(c_coef))
		# c is the matrix product of c_coef.T * A_c, NOTE: change to minimize
		# thus multiply by -1
		c = -_scipy_m_.dot(c_coef, A_c)
		assert c.shape == (_opt.A_T.shape[1], ), "c shape:" + str(c.shape)
		########################################################################
		# now also include c related lines lines into ub, I don't want negative
		# amount of 'inputs'; this does not need to change sign
		A_cub = _scipy_m_.vstack([A_c, A_ub])
		b_cub = _scipy_m_.zeros(n_items - len(eq_ids), dtype = float)
		########################################################################
		# apply cyclic optimization
		if not no_cyclic:
			A_eq, b_eq = self._apply_cyclic_product_optimizing(eq_ids, A_eq, b_eq,
				optim_data = _opt)
		########################################################################
		# build return value
		param = LinearProgrammingParam()
		param.c = c
		param.A_c = A_c
		param.A_eq = A_eq
		param.b_eq = b_eq
		param.A_ub = A_ub
		param.b_ub = b_ub
		param.A_cub = A_cub
		param.b_cub = b_cub
		param.x_bounds = [(0, None)] * n_recipes
		param.c_ids = c_ids
		param.eq_ids = eq_ids
		param.ub_ids = ub_ids
		return param


	@staticmethod
	def _batch_slice(A_T, *ka):
		return tuple([_scipy_m_.take(A_T, i, axis = 0) for i in ka])


	def _apply_cyclic_product_optimizing(self, eq_ids, A_eq, b_eq, *,
			#optim_goals: dict,
			optim_data: _linear_optimizer_base_m_.LinearOptimizerAttributeSet,
		) -> (_scipy_m_.ndarray, _scipy_m_.ndarray):
		"""
		(internal only) the way deal with cyclic products are separate them from
		the A_eq and b_eq, create new lines that count how many executions are
		conducted for those producing recipes;

		this is only done when the products are on the optim_goals list;
		otherwise, this is not needed, reasons are because I have already
		checked no cycles can be perpetual (in RecipeSet class); thus, if they
		are not the final product (which will be recycled to cause cyclic
		dependency), go over another round of the cycle is ensure to be not raw-
		material benefitial;

		return modified A_eq and b_eq;
		"""
		_opt = optim_data
		A_eq = A_eq.copy()
		b_eq = b_eq.copy()
		for eq_id, row_id in enumerate(eq_ids):
			# eq_id: the id in A_eq and b_eq
			# row_id: the id in A_T
			iname = _opt.item_names[row_id]
			if self.get_item(iname).is_cyclic_product():
				# rescue output count
				output = b_eq[eq_id]
				# new line, only concern about producing recipes (> 0)
				# and set all others to zero
				ex_line = [(i if i > 0 else 0) for i in _opt.A_T[row_id]]
				# original b_eq become 0
				b_eq[eq_id] = 0
				# append to A_eq, b_eq
				A_eq = _scipy_m_.vstack([A_eq, ex_line])
				b_eq = _scipy_m_.hstack([b_eq, output])
		assert len(A_eq) == len(b_eq), "len mismatch:" + str([len(A_eq), len(b_eq)])
		return A_eq, b_eq


	def _refine_restrictions(self,
			old_param: LinearProgrammingParam,
			optim_goals: _collections_m_.Counter,
			optim_data: _linear_optimizer_base_m_.LinearOptimizerAttributeSet,
			**optim_args,
		) -> (bool, LinearProgrammingParam):
		"""
		(internal only) dirty codes to refine linear programming parameters
		when a previous trial failed

		the second part of this method also uses
		self._finalize_linear_programming_params
		as back end
		"""
		# removing items that produced by some recipes but are locked as input
		# this potentially cause contradictory restrictions as opposite signs
		# find those items
		# inputs are ub's
		_opt = optim_data
		# in raw A_T, it needs to be < 0
		c_ids = [i for i in old_param.c_ids if any(_opt.A_T[i] < 0)]
		if len(c_ids) == len(old_param.c_ids):
			return False, None # no refine
		# still, ub_ids is all left behind c_ids and eq_ids
		# in this case, eq_ids does not need to change
		ub_ids = [i for i in range(len(_opt.A_T))\
			if (i not in c_ids) and (i not in old_param.eq_ids)]
		refined_param = self._finalize_linear_programming_params(
			c_ids, old_param.eq_ids, ub_ids,
			optim_goals = optim_goals,
			optim_data = optim_data,
			**optim_args)
		return True, refined_param
