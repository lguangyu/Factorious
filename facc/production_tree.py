#!/usr/bin/env python3

import math as _math_m_
import warnings as _warning_m_
import itertools as _itertools_m_
import collections as _collections_m_
from . import production_profiler as _production_profiler_m_


class ProductionTreeNodeBase(object):
	# used to allocate uuid to each node at init time
	_uuid_alloc_next = 0

	@classmethod
	def _allocate_uuid(cls) -> int:
		"""
		allocate a uuid for newly created node
		"""
		uuid = int(cls._uuid_alloc_next)
		cls._uuid_alloc_next = int(cls._uuid_alloc_next + 1)
		return uuid

	def __init__(self, type_str: str = None) -> None:
		super(ProductionTreeNodeBase, self).__init__()
		# use the very base class value
		self._uuid = ProductionTreeNodeBase._allocate_uuid()
		self.type = type_str
		return

	def uuid(self) -> int:
		"""
		return the uuid of this node
		"""
		return self._uuid

	def connect_to(self, target) -> None:
		raise NotImplementedError()
		return

	def connect_from(self, source) -> None:
		raise NotImplementedError()
		return


class PTNodeRequestable(ProductionTreeNodeBase):
	def __init__(self, *ka, **kw) -> None:
		super(PTNodeRequestable, self).__init__(*ka, **kw)
		self._out_pool = _collections_m_.Counter()
		self.out_connections = []
		return

	def request(self, item_name, count) -> (bool, float):
		"""
		make request from its <_out_pool>;
		
		RETURNS
		-------
		found_item:
			True if <item_name> found in <_out_pool>, regardless if insufficient;

		provided:
			provided amount;
		"""
		if item_name not in self._out_pool:
			return False, 0.0
		provided = min(self._out_pool[item_name], count)
		self._out_pool[item_name] = self._out_pool[item_name] - provided
		return True, provided

	def connect_to(self, target: "PTNodeDepositable"):
		assert isinstance(target, PTNodeDepositable), type(target)
		if target not in self.out_connections:
			self.out_connections.append(target)
		return

	def connect(self, target: "PTNodeDepositable"):
		"""
		combined method to call connect_to and connect_from on the identical
		self->target edge
		"""
		assert isinstance(target, PTNodeDepositable), type(target)
		self.connect_to(target)
		target.connect_from(self)
		return


class PTNodeDepositable(ProductionTreeNodeBase):
	def __init__(self, *ka, **kw) -> None:
		super(PTNodeDepositable, self).__init__(*ka, **kw)
		self._depo_pit = _collections_m_.Counter()
		self.in_connections = []
		return

	def deposit(self, item_name, count) -> (bool, float):
		"""
		make deposit to its <_depo_pit>;
		
		RETURNS
		-------
		found_item:
			True if <item_name> found in <_depo_pit>, regardless if insufficient;

		deposited:
			deposited amount;
		"""
		if item_name not in self._depo_pit:
			return False, 0.0
		deposited = min(self._depo_pit[item_name], count)
		self._depo_pit[item_name] = self._depo_pit[item_name] - deposited
		return True, deposited

	def connect_from(self, source: "PTNodeRequestable"):
		assert isinstance(source, PTNodeRequestable), type(source)
		if source not in self.in_connections:
			self.in_connections.append(source)
		return


class PTNodeRecipe(PTNodeRequestable,PTNodeDepositable):
	"""
	Recipe node;
	"""
	def __init__(self, name: str, execs: float,
			in_flux: _collections_m_.Counter = {},
			out_flux: _collections_m_.Counter = {},
		) -> None:
		super(PTNodeRecipe, self).__init__("recipe")
		self.name = name
		self.execs = execs
		self.in_flux = _collections_m_.Counter(in_flux)
		self.out_flux = _collections_m_.Counter(out_flux)
		self._out_pool = self.out_flux.copy()
		self._depo_pit = self.in_flux.copy()
		return

	def __str__(self):
		return "<%s uuid=%d name='%s' exec='%f' in_flux='%s' out_flux='%s'>"\
			% (type(self).__name__, self.uuid(), self.name, self.execs,\
				str(self.in_flux), str(self.out_flux))


class PTNodeSource(PTNodeRequestable):
	"""
	requestable node with unlimited source but only provide one Item kind;
	"""
	def __init__(self, item: str, providing: float = 0.0) -> None:
		super(PTNodeSource, self).__init__("item-source")
		self.item = item
		self.providing = providing
		del self.out_connections
		return

	def __str__(self):
		return "<%s uuid=%d item='%s' providing='%f'>"\
			% (type(self).__name__, self.uuid(), self.item, self.providing)

	def request(self, item_name, count) -> (bool, float):
		"""
		make request;
		
		RETURNS
		-------
		match:
			True if matches the providing;

		provided:
			always equal to <count> if <found_item> is True;
		"""
		if item_name != self.item:
			return False, 0.0
		self.providing = self.providing + count
		return True, count


class PTNodeSink(PTNodeDepositable):
	"""
	depositable node with unlimited pit but only accept one Item kind;
	"""
	def __init__(self, item: str, accepting: float = 0.0) -> None:
		super(PTNodeSink, self).__init__("item-sink")
		self.item = item
		self.accepting = accepting
		del self.in_connections
		return

	def __str__(self):
		return "<%s uuid=%d item='%s' accepting='%f'>"\
			% (type(self).__name__, self.uuid(), self.item, self.accepting)

	# overrided function
	def deposit(self, item_name, count) -> (bool, float):
		"""
		make deposite;
		
		RETURNS
		-------
		match:
			True if matches the accepting;

		accepting:
			always equal to <count> if <found_item> is True;
		"""
		if item_name != self.item:
			return False, 0.0
		self.accepting = self.accepting + count
		return True, count


class PTNodeFlux(PTNodeRequestable,PTNodeDepositable):
	"""
	flux node is connectors between nodes;
	"""
	def __init__(self, flux: _collections_m_.Counter = {}) -> None:
		super(PTNodeFlux, self).__init__("flux")
		# ensure type
		self.flux = _collections_m_.Counter(flux)
		self.src_node = None
		self.dest_node = None
		del self.in_connections
		del self.out_connections
		return

	def __str__(self):
		return "<%s uuid=%d flux='%s'>"\
			% (type(self).__name__, self.uuid(), str(self.flux))

	# PTNodeFlux does not actually request/deposit
	# instead it propagates the action to the other end
	# this maybe dangerous to create an infinit loop
	def request(self, item_name, count) -> (bool, float):
		if self.src_node is None:
			return False, 0.0
		return self.src_node.request(item_name, count)

	def deposit(self, item_name, count) -> (bool, float):
		if self.dest_node is None:
			return False, 0.0
		return self.dest_node.deposit(item_name, count)

	def connect_to(self, target: PTNodeDepositable) -> None:
		assert isinstance(target, PTNodeDepositable), type(target)
		if self.dest_node is not None:
			_warning_m_.warn("'%s' relink target node to '%s'" % (self, target))
		self.dest_node = target
		return

	def connect_from(self, source: PTNodeRequestable) -> None:
		assert isinstance(source, PTNodeRequestable), type(source)
		if self.src_node is not None:
			_warning_m_.warn("'%s' relink source node to '%s'" % (self, source))
		self.src_node = source
		return


class GeneralSourceComplex(dict):
	"""
	a collection of sources, with unified interface;
	"""
	def __init__(self, tree_parent, *ka, **kw):
		super(GeneralSourceComplex, self).__init__(*ka, **kw)
		self._tree_parent = tree_parent
		# get all sinks from parent tree
		self.update({s.item: s for s in self._tree_parent.iterate_nodes()\
			if isinstance(s, PTNodeSource)})
		return

	def request(self, item_name, count) -> PTNodeSource:
		"""
		request from this complex, returns the eventually requested source;
		if the node does not exist, create one;
		"""
		if item_name not in self:
			src = self._tree_parent.create_node(PTNodeSource, item_name, 0.0)
			self[item_name] = src
		else:
			src = self[item_name]
		assert src.item == item_name, src.item_name + "|" + item_name
		src.request(item_name, count)
		return src


class GeneralSinkComplex(dict):
	"""
	a collection of sinks, with unified interface;
	"""
	def __init__(self, tree_parent, *ka, **kw):
		super(GeneralSinkComplex, self).__init__(*ka, **kw)
		self._tree_parent = tree_parent
		# get all sinks from parent tree
		self.update({s.item: s for s in self._tree_parent.iterate_nodes()\
			if isinstance(s, PTNodeSink)})
		return

	def deposit(self, item_name, count) -> PTNodeSink:
		"""
		deposit to this complex, returns the eventually deposited sink;
		if the node does not exist, create one;
		"""
		if item_name not in self:
			sink = self._tree_parent.create_node(PTNodeSink, item_name, 0.0)
			self[item_name] = sink
		else:
			sink = self[item_name]
		assert sink.item == item_name, sink.item_name + "|" + item_name
		sink.deposit(item_name, count)
		return sink


class ProductionTree(_production_profiler_m_.ProductionProfiler):
	"""
	tree constructor over production profiling results; this is a closed class,
	means only very few arguments are requested from outside input; thus most
	of the parameters are not type-checked (only used assert which is debug-
	only);
	"""
	def __init__(self, *ka, **kw) -> None:
		"""
		PARAMETERS
		----------
		see production_profiler.ProductionProfiler for detailed information;
		"""
		super(ProductionTree, self).__init__(*ka, **kw)
		# a list of all current nodes
		self._tree_nodes_list = []
		return


	def get_current_tree(self, force_construct: bool = True) -> list:
		"""
		return a list of interconnected nodes as a tree, based on the calculated
		profiling results;

		PARAMETERS
		----------
		force_construct:
			if False, will directly return the previously constructed tree (if
			have) no matter whether changes were made after last construction,
			otherwise construct from scratch; if True, the construction will be
			forced;

		RETURNS
		-------
		node_list:
			a list of tree nodes;
		"""
		if (not len(self._tree_nodes_list)) or force_construct:
			self.clear_current_tree()
			self.construct_tree()
		# only use shallow copy below
		return self._tree_nodes_list.copy()


	def clear_current_tree(self) -> None:
		"""
		clear current constructed tree nodes
		"""
		self._tree_nodes_list.clear()
		return


	def create_node(self,
			node_type: type,
			*ka, **kw,
		) -> ProductionTreeNodeBase:
		"""
		create and return a new node instance of given type, also adding it to
		the tree's nodes tracking list;

		PARAMETERS
		----------
		node_type:
			type of the constructed node (subclass of ProductionTreeNodeBase);

		*ka, **kw:
			extra parameter sent to the node's constructor;
		"""
		assert issubclass(node_type, ProductionTreeNodeBase), node_type
		node = node_type(*ka, **kw)
		self._tree_nodes_list.append(node)
		return node


	def iterate_nodes(self) -> iter:
		"""
		return an iterator to the nodes list in this tree;
		"""
		return iter(self._tree_nodes_list)


	def construct_tree(self) -> None:
		"""
		construct the tree from scratch based on current profile;
		"""
		self._create_recipe_nodes()
		self._resolve_flux()
		pass


	def _create_recipe_nodes(self) -> None:
		"""
		(internal only) create a dict of nodes that represents the calculated
		Recipe profile;
		"""
		_, rexe, _, _ = self.get_current_profile()
		# first, create nodes
		for r, ex in rexe.items():
			# get recipe information
			recipe = self.get_recipe(r)
			# create node, add to tree
			rnode = self.create_node(PTNodeRecipe, name = r, execs = ex,
				in_flux = _collections_m_.Counter({k: v * ex\
					for (k, v) in recipe.inputs.items()}),
				out_flux = _collections_m_.Counter({k: v * ex\
					for (k, v) in recipe.products.items()})
			)
		return


	def _connect_with_flux(self,
			src_node: PTNodeRequestable,
			dest_node: PTNodeDepositable,
		) -> PTNodeFlux:
		"""
		(internal only) connect two nodes, with creating a new flux node in\
		between;
		"""
		assert isinstance(src_node, PTNodeRequestable), type(src_node)
		assert isinstance(dest_node, PTNodeDepositable), type(dest_node)
		fnode = self.create_node(PTNodeFlux)
		src_node.connect(fnode)
		fnode.connect(dest_node)
		return fnode


	def _get_flux(self,
			src_node: PTNodeRequestable,
			dest_node: PTNodeDepositable,
		) -> PTNodeFlux:
		"""
		(internal only) search for the existing flux of src_node->dest_node;
		if so, return the flux; else create one and return that;
		"""
		assert isinstance(src_node, PTNodeRequestable), type(src_node)
		assert isinstance(dest_node, PTNodeDepositable), type(dest_node)
		for flux in src_node.out_connections:
			if isinstance(flux, PTNodeFlux) and (flux.dest_node is dest_node):
				return flux
		# create one
		return self._connect_with_flux(src_node, dest_node)


	def _resolve_flux(self):
		"""
		(internal only) resolve Item flux using constructed Recipe nodes;
		"""
		# terminal item nodes dicts
		src_x = GeneralSourceComplex(tree_parent = self)
		sink_x = GeneralSinkComplex(tree_parent = self)
		recp_nodes = [i for i in self.iterate_nodes()\
			if isinstance(i, PTNodeRecipe)]
		for node in recp_nodes:
			# resolve is done by requesting mode, i.e. downstream nodes
			# request resources from its uptreams
			for fname, fcount in node.in_flux.items():
				# this flag var is necessary
				# for ... break ... else does not work here
				found_src = False
				remain = fcount
				for q_node in recp_nodes:
					#if node is src_node:
					#	continue
					_found, _amount = q_node.request(fname, remain)
					if not _found:
						continue
					found_src = True
					if _amount > 0.0:
						# make succesful request as flux
						fnode = self._get_flux(q_node, node)
						fnode.flux.update({fname: _amount})
						remain = remain - _amount
					if _math_m_.isclose(remain, 0.0):
						break
				else:
					# to here means break not called
					if not found_src:
						# no source recipe, request from general source
						src_x.request(fname, fcount)
					#elif not _math_m_.isclose(remain, 0.0):
					else:
						_warning_m_.warn("'%e' not considered 'isclose' to 0")
			# for out deposits, only need to check sinks,
			# recipe-recipe deposits are repetitive
			for fname, fcount in node.out_flux.items():
				found_acp = [q_node.deposit(fname, fcount)[0]\
					for q_node in recp_nodes]
				if not any(found_acp):
					sink_x.deposit(fname, fcount)
		return
