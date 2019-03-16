#!/usr/bin/env python3

import math as _math_m_
import warnings as _warning_m_
import itertools as _itertools_m_
import collections as _collections_m_
from . import production_profiler as _production_profiler_m_


class ProductionNetworkNodeBase(object):
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
		super(ProductionNetworkNodeBase, self).__init__()
		# use the very base class value
		self._uuid = ProductionNetworkNodeBase._allocate_uuid()
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


class PNNodeRequestable(ProductionNetworkNodeBase):
	def __init__(self, *ka, output_total = {}, **kw) -> None:
		super(PNNodeRequestable, self).__init__(*ka, **kw)
		self._out_pool = _collections_m_.Counter(output_total)
		self.out_connections = []
		return

	def request(self, item_name, count) -> (bool, float):
		"""
		make request from its <_out_pool>;
		
		RETURNS
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

	def connect_to(self, target: "PNNodeDepositable"):
		assert isinstance(target, PNNodeDepositable), type(target)
		if target not in self.out_connections:
			self.out_connections.append(target)
		return

	def connect(self, target: "PNNodeDepositable"):
		"""
		combined method to call connect_to and connect_from on the identical
		self->target edge
		"""
		assert isinstance(target, PNNodeDepositable), type(target)
		self.connect_to(target)
		target.connect_from(self)
		return


class PNNodeDepositable(ProductionNetworkNodeBase):
	def __init__(self, *ka, input_total = {}, **kw) -> None:
		super(PNNodeDepositable, self).__init__(*ka, **kw)
		self._depo_pit = _collections_m_.Counter(input_total)
		self.in_connections = []
		return

	def deposit(self, item_name, count) -> (bool, float):
		"""
		make deposit to its <_depo_pit>;
		
		RETURNS
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

	def connect_from(self, source: "PNNodeRequestable"):
		assert isinstance(source, PNNodeRequestable), type(source)
		if source not in self.in_connections:
			self.in_connections.append(source)
		return


class PNNodeRecipe(PNNodeRequestable,PNNodeDepositable):
	"""
	Recipe node;
	"""
	def __init__(self, name: str, execs: float,
			in_flux: _collections_m_.Counter = {},
			out_flux: _collections_m_.Counter = {},
		) -> None:
		super(PNNodeRecipe, self).__init__("recipe",\
			input_total = in_flux,
			output_total = out_flux)
		self.name = name
		self.execs = execs
		self.in_flux = _collections_m_.Counter(in_flux)
		self.out_flux = _collections_m_.Counter(out_flux)
		return

	def __str__(self):
		return "<%s uuid=%d name='%s' exec='%f' in_flux='%s' out_flux='%s'>"\
			% (type(self).__name__, self.uuid(), self.name, self.execs,\
				str(self.in_flux), str(self.out_flux))


class PNNodeSource(PNNodeRequestable):
	"""
	requestable node with unlimited source but only provide one Item kind;
	"""
	def __init__(self, item: str, providing: float = 0.0) -> None:
		super(PNNodeSource, self).__init__("item-source")
		self.item = item
		self.providing = providing
		return

	def __str__(self):
		return "<%s uuid=%d item='%s' providing='%f'>"\
			% (type(self).__name__, self.uuid(), self.item, self.providing)

	def request(self, item_name, count) -> (bool, float):
		"""
		make request;
		
		RETURNS
		match:
			True if matches the providing;
		provided:
			always equal to <count> if <found_item> is True;
		"""
		if item_name != self.item:
			return False, 0.0
		self.providing = self.providing + count
		return True, count


class PNNodeSink(PNNodeDepositable):
	"""
	depositable node with unlimited pit but only accept one Item kind;
	"""
	def __init__(self, item: str, accepting: float = 0.0) -> None:
		super(PNNodeSink, self).__init__("item-sink")
		self.item = item
		self.accepting = accepting
		return

	def __str__(self):
		return "<%s uuid=%d item='%s' accepting='%f'>"\
			% (type(self).__name__, self.uuid(), self.item, self.accepting)

	# overrided function
	def deposit(self, item_name, count) -> (bool, float):
		"""
		make deposite;
		
		RETURNS
		match:
			True if matches the accepting;
		accepting:
			always equal to <count> if <found_item> is True;
		"""
		if item_name != self.item:
			return False, 0.0
		self.accepting = self.accepting + count
		return True, count


class PNNodeFlux(PNNodeRequestable,PNNodeDepositable):
	"""
	flux node is connectors between nodes;
	"""
	def __init__(self, flux: _collections_m_.Counter = {}) -> None:
		super(PNNodeFlux, self).__init__("flux")
		# ensure type
		self.flux = _collections_m_.Counter(flux)
		self.src_node = None
		self.dest_node = None
		# flux class does not need them
		del self._out_pool
		del self._depo_pit
		del self.in_connections
		del self.out_connections
		return

	def __str__(self):
		return "<%s uuid=%d flux='%s'>"\
			% (type(self).__name__, self.uuid(), str(self.flux))

	def update(self, *ka, **kw):
		"""
		update flux content, propagates to the attribute Counter;
		"""
		return self.flux.update(*ka, **kw)

	# PNNodeFlux does not actually request/deposit
	# instead it propagates the action to the other end
	# this maybe dangerous to create an infinit loop
	def request(self, item_name, count) -> (bool, float):
		if self.src_node is None:
			return False, 0.0
		success, amount = self.src_node.request(item_name, count)
		if success and (amount > 0):
			self.update({item_name, amount})
		return success, amount

	def deposit(self, item_name, count) -> (bool, float):
		if self.dest_node is None:
			return False, 0.0
		success, amount = self.dest_node.deposit(item_name, count)
		if success and (amount > 0):
			self.update({item_name, amount})
		return success, amount

	def connect_to(self, target: PNNodeDepositable) -> None:
		assert isinstance(target, PNNodeDepositable), type(target)
		if self.dest_node is not None:
			_warning_m_.warn("'%s' relink target node to '%s'" % (self, target))
		self.dest_node = target
		return

	def connect_from(self, source: PNNodeRequestable) -> None:
		assert isinstance(source, PNNodeRequestable), type(source)
		if self.src_node is not None:
			_warning_m_.warn("'%s' relink source node to '%s'" % (self, source))
		self.src_node = source
		return


class GeneralSourceSinkComplexBase(dict):
	"""
	manage over a collection of sources/sink, with unified interface;
	"""
	_node_type_ = None

	def __init__(self, parent, *ka, **kw):
		assert issubclass(self._node_type_, PNNodeSource)\
			or issubclass(self._node_type_, PNNodeSink)
		self._parent = parent
		# get all sources/sink from parent network
		self.update({n.item: s for s in self._parent.iterate_nodes()\
			if isinstance(s, self._node_type_)})
		return

	def get_node(self, item_name) -> PNNodeSource or PNNodeSink:
		"""
		check this complex, returns the found source/sink node;
		if the node does not exist, create new and return;
		"""
		if item_name not in self:
			node = self._parent.create_node(self._node_type_, item_name, 0.0)
			self[item_name] = node
		else:
			node = self[item_name]
		assert node.item == item_name, node.item_name + "|" + item_name
		return node


class GeneralSourceComplex(GeneralSourceSinkComplexBase):
	"""
	a collection of sources;
	"""
	_node_type_ = PNNodeSource
	pass


class GeneralSinkComplex(GeneralSourceSinkComplexBase):
	"""
	a collection of sinks;
	"""
	_node_type_ = PNNodeSink
	pass


class ProductionNetwork(_production_profiler_m_.ProductionProfiler):
	"""
	network constructor over production profiling results; this is a closed class,
	means only very few arguments are requested from outside input; thus most
	of the parameters are not type-checked (only used assert which is debug-
	only);
	"""
	def __init__(self, *ka, **kw) -> None:
		"""
		PARAMETERS
		see production_profiler.ProductionProfiler for detailed information;
		"""
		super(ProductionNetwork, self).__init__(*ka, **kw)
		# a list of all current nodes
		self._nodes_recruited = []
		return


	def get_current_network(self, force_construct: bool = True) -> list:
		"""
		return a list of interconnected nodes as a network, based on the calculated
		profiling results;

		PARAMETERS
		force_construct:
			if False, will directly return the previously constructed network (if
			have) no matter whether changes were made after last construction,
			otherwise construct from scratch; if True, the construction will be
			forced;

		RETURNS
		node_list:
			a list of network nodes;
		"""
		if (not len(self._nodes_recruited)) or force_construct:
			self.clear_current_network()
			self.construct_network()
		# only use shallow copy below
		return self._nodes_recruited.copy()


	def clear_current_network(self) -> None:
		"""
		clear current constructed network nodes
		"""
		self._nodes_recruited.clear()
		return


	def create_node(self,
			node_type: type,
			*ka, **kw,
		) -> ProductionNetworkNodeBase:
		"""
		create and return a new node instance of given type, also adding it to
		the network's nodes tracking list;

		PARAMETERS
		node_type:
			type of the constructed node (subclass of ProductionNetworkNodeBase);
		*ka, **kw:
			extra parameter sent to the node's constructor;
		"""
		assert issubclass(node_type, ProductionNetworkNodeBase), node_type
		node = node_type(*ka, **kw)
		self._nodes_recruited.append(node)
		return node


	def iterate_nodes(self) -> iter:
		"""
		return an iterator to the nodes list in this network;
		"""
		return iter(self._nodes_recruited)


	def construct_network(self) -> None:
		"""
		construct the network from scratch based on current profile;
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
			# create node, add to network
			rnode = self.create_node(PNNodeRecipe, name = r, execs = ex,
				in_flux = _collections_m_.Counter({k: v * ex\
					for (k, v) in recipe.inputs.items()}),
				out_flux = _collections_m_.Counter({k: v * ex\
					for (k, v) in recipe.products.items()})
			)
		return


	def _connect_with_flux(self,
			src_node: PNNodeRequestable,
			dest_node: PNNodeDepositable,
		) -> PNNodeFlux:
		"""
		(internal only) connect two nodes, with creating a new flux node in\
		between;
		"""
		assert isinstance(src_node, PNNodeRequestable), type(src_node)
		assert isinstance(dest_node, PNNodeDepositable), type(dest_node)
		fnode = self.create_node(PNNodeFlux)
		src_node.connect(fnode)
		fnode.connect(dest_node)
		return fnode


	def _get_flux(self,
			src_node: PNNodeRequestable,
			dest_node: PNNodeDepositable,
		) -> PNNodeFlux:
		"""
		(internal only) search for the existing flux of src_node->dest_node;
		if so, return the flux; else create one and return that;
		"""
		assert isinstance(src_node, PNNodeRequestable), type(src_node)
		assert isinstance(dest_node, PNNodeDepositable), type(dest_node)
		for flux in src_node.out_connections:
			if isinstance(flux, PNNodeFlux) and (flux.dest_node is dest_node):
				return flux
		# create one
		return self._connect_with_flux(src_node, dest_node)


	def _resolve_flux(self):
		"""
		(internal only) resolve Item flux using constructed Recipe nodes;
		"""
		# terminal item nodes dicts
		src_x = GeneralSourceComplex(parent = self)
		sink_x = GeneralSinkComplex(parent = self)
		recp_nodes = [i for i in self.iterate_nodes()\
			if isinstance(i, PNNodeRecipe)]
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
						self._get_flux(q_node, node).update({fname: _amount})
						remain = remain - _amount
					if _math_m_.isclose(remain, 0.0, abs_tol = 1e-6):
						break
				else:
					# to here means break not called
					if not found_src:
						# no source recipe, request from general source
						src_node = src_x.get_node(fname)
						src_node.request(fname, fcount)
						# make sure to add a node flux
						self._get_flux(src_node, node).update({fname: fcount})
					#elif not _math_m_.isclose(remain, 0.0):
					else:
						_warning_m_.warn("'%e' not considered 'isclose' to 0"\
						% remain)
			# for out deposits, only need to check sinks,
			# recipe-recipe deposits are repetitive
			for fname, fcount in node.out_flux.items():
				found_acp = [q_node.deposit(fname, fcount)[0]\
					for q_node in recp_nodes]
				if not any(found_acp):
					sink_node = sink_x.get_node(fname)
					sink_node.deposit(fname, fcount)
					# make sure to add a node flux
					self._get_flux(node, sink_node).update({fname: fcount})
		return
