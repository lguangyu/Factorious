#!/usr/bin/env python3

import itertools as _itertools_m_
import numpy as _numpy_m_


class UnweightedDirectedGraph(_numpy_m_.ndarray):
	#@staticmethod
	def __new__(cls,
			adj: int or _numpy_m_.ndarray,
		) -> None:
		"""
		PARAMETERS
		----------
		adj:
			either an boolean 2-d array for initial values, or an int as the
			size (#rows, equals #cols) of the returning matrix; the shape of
			adjacency matrix must be square;

		EXCEPTIONS
		----------
		ValueError: if <adj> looks like an array but not 2-d or square;
		"""
		if isinstance(adj, int):
			# using as shape
			shape = (adj, adj)
			self = super(UnweightedDirectedGraph, cls).__new__(cls,
				shape, dtype = bool)
			self.fill(False)
		else:
			# using as adj matrix
			shape = (len(adj), ) * 2
			self = super(UnweightedDirectedGraph, cls).__new__(cls,
				shape, dtype = bool)
			self[:] = adj
			if (self.ndim != 2) or (self.shape[0] != self.shape[1]):
				raise ValueError("adjacency matrix must be 2-d square-shaped")
		return self


	def get_cyclic_vertex_groups(self) -> list:
		"""
		find all cyclic dependencies in the graph, and return a list of such
		vertex groups which are mutually disconnected (disjoint);

		RETURNS
		-------
		list:
			list of found such subgraphs; each cycle (loop) is represented as
			a <set> of indices of involved vertices;
		"""
		return self._extract_cycles(self)


	#@staticmethod
	#def _trim_leaves_and_roots(
	#		_adj: _numpy_m_.ndarray,
	#		copy: bool = True
	#	) -> _numpy_m_.ndarray:
	#	"""
	#	recursively remove leaves and roots in the provided adjacency matrix;
	#	what remains are only cyclic dependencies;

	#	PARAMETERS
	#	----------
	#	_adj: input original _adjacency matrix;
	#	copy: if False, progress inplace of the input matrix;

	#	RETURNS
	#	-------
	#	modified adjacency matrix;
	#	"""
	#	_size = len(_adj)
	#	adj = _adj.copy().astype(bool) if copy else _adj
	#	# remove in-wards deps
	#	# in-edge points in-wards to node
	#	for d, axis in zip(["in", "out"], [0, 1]):
	#		edge_counts = adj.sum(axis = axis)
	#		_checked = _numpy_m_.zeros(_size, dtype = bool)
	#		while True:
	#			_leaf_bool = _numpy_m_.logical_and(_checked == False, edge_counts == 0)
	#			if _leaf_bool.any():
	#				# mark as checked
	#				_checked[_leaf_bool] = True
	#				# checkout the deps to this node
	#				# remove the count for all its direct edges
	#				_leaf_ids = _leaf_bool.nonzero()[0]
	#				for li in _leaf_ids:
	#					if d == "in":
	#						edge_counts[adj[li, :]] -= 1
	#						adj[li, :] = False
	#					elif d == "out":
	#						edge_counts[adj[:, li]] -= 1
	#						adj[:, li] = False
	#				continue
	#			else:
	#				break
	#	return adj


	#@staticmethod
	#def _remove_orphans(
	#		_adj: _numpy_m_.ndarray,
	#	) -> _numpy_m_.ndarray:
	#	"""
	#	remove all orphan nodes i.e. not connected nodes from the graph

	#	PARAMETERS
	#	----------
	#	_adj: input original _adjacency matrix;

	#	RETURNS
	#	-------
	#	modified adjacency matrix;
	#	each row/col's id that in original matrix
	#	"""
	#	mask = _adj.any(axis = 1)
	#	mask_ids = mask.nonzero()[0]
	#	# ix_ using mask_ids (much smaller) is thought to be friendly
	#	return _adj[_numpy_m_.ix_(mask_ids, mask_ids)], mask_ids


	@staticmethod
	def _extract_cycles(
			_adj: _numpy_m_.ndarray,
		) -> list:
		"""
		extract cycles in given adjacency matrix;

		PARAMETERS
		----------
		_adj:
			input graph represented in adjacency matrix;

		RETURNS
		-------
		list of cycles (loops)
		"""
		# this algorithm is a stack version of recursive call simplified as:
		# -- pseudocode --------------------------------------------------------
		# /* this stack serves as the visit history */
		# visit_stack <- [start node]
		# function travel_next(visit_stack, found_loops&)
		# {
		#     /* visiting node: visit_stack->top() */
		#     node = visit_stack->top()
		#     if (node in visit_stack) /* already visited */
		#     {
		#         found_loops->add_path(
		#             start=visit_stack->first_time(node),
		#             end=visit_stack->current)
		#         )
		#         return
		#     }
		#     else
		#     {
		#         visit_stack->push(node)
		#         for (next_node in node->next())
		#         {
		#             travel_next(next_node)
		#         }
		#         visit_stack->pop() /* pop self, i.e. pop(node) */
		#         return
		#     }
		# }
		# ----------------------------------------------------------------------
		# this algorithm has time complexity O(N * M), space complexity O(N * M)
		# where: N=number of nodes, M=avg edges of all nodes
		cycles = []
		notyet_visited = _numpy_m_.ones(len(_adj), dtype = bool)
		while notyet_visited.any():
			# operate in a small matrix
			nyvis_trues = notyet_visited.nonzero()[0]
			mapback = lambda x: _numpy_m_.take(nyvis_trues, list(x))
			# w_adj is the working adjacency matrix that we only interested in
			# other nodes are masked out
			w_adj = _adj[_numpy_m_.ix_(nyvis_trues, nyvis_trues)]
			_size = len(w_adj)
			# initialize
			# this is used to finally update mask, i.e. nodes are ever visited
			# those nodes are not worthy visited again by the caller
			curr_visited_nodes = set({0})
			# visit path stack trace
			visited_path = [0]
			# candidate nodes to visit in next step
			# list of lists
			to_visit = [w_adj[0].nonzero()[0].tolist()]
			# travel
			while visited_path:
				next_visit = to_visit[-1]
				# visit each node in next_visit
				while next_visit:
					_vid = next_visit.pop()
					if _vid not in visited_path:
						# add _vid to visited list
						curr_visited_nodes.add(_vid)
						# check if this node connects to downstream nodes
						# no downstream connections cannot be in a loop
						ds_conn = w_adj[_vid].nonzero()[0].tolist()
						if ds_conn:
							# append for deep travel
							visited_path.append(_vid)
							to_visit.append(ds_conn)
							break
					else:
						# found cycle
						# find the first occur of _vid, the start of cycle
						_id = visited_path.index(_vid)
						# add to cycle list
						cycle_path = visited_path[_id:]
						cycles.append(set(mapback(cycle_path)))
						continue
				else:
				#if not to_visit[-1]:
					to_visit.pop()
					visited_path.pop()
			# update mask
			notyet_visited[mapback(curr_visited_nodes)] = False
		# combine if two cycles share vertex/edge(s)
		UnweightedDirectedGraph.\
			_union_all_non_disjoint(cycles, inplace = True)
		# debug
		assert all([isinstance(i, set) for i in cycles]),\
			"cycles assumed to be sets"
		return cycles


	@staticmethod
	def _union_all_non_disjoint(
			set_list: list,
			inplace: bool = False
		) -> list:
		"""
		union all non-disjoint sets in a list;

		PARAMETERS
		----------
		set_list:
			list of sets;

		inplace:
			True if changes made inplace on the input list;

		RETURNS
		-------
		list of disjoint sets;
		"""
		# this is the naive algorithm doing this task
		# comparing each set with every others
		# joint if intersecting non-null
		# this algorithm has time complexity O(N * M * P), space complexity O(N)
		# where: N=number of initial sets, M=number of final sets
		# P=avg. time doing check disjoint and make union,
		# which is roughly O(avg n) i.e. average number of elements each set,
		# (since python's set is implimented as hashes)
		wk_list = set_list if inplace else list(set_list)
		while True:
			# NOTE: wk_list is changed within iterations
			for (i, set_i), (j, set_j) in _itertools_m_.\
				combinations(enumerate(wk_list), r = 2):
				if not set_i.isdisjoint(set_j):
					wk_list[i] = set_i.union(set_j)
					# remove the union'd set
					# NOTE: index for set_j starts from i + 1
					del wk_list[j]
					# now need to jump of two nested loops
					# since wk_list has been changed
					break
			# outer loop
			# else -> above break is not called
			# -> nothing special find in past round
			# -> should break
			# otherwise, continue
			else:
				break
			continue
		return wk_list
