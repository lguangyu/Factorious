#!/usr/bin/env python3

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
		self._uuid = self._allocate_uuid()
		self.type = type_str
		self.in_connections = []
		self.out_connections = []
		return


	def __str__(self):
		return "<%s type='%s'>" % type(self).__name__


	def __repr__(self):
		return str(self)


	def uuid(self) -> int:
		"""
		return the uuid of this node
		"""
		return self._uuid


	def connect(self, target: "ProductionTreeNodeBase") -> None:
		"""
		connect to another node;

		PARAMETERS
		----------
		target:
			a target node;

		EXCEPTIONS
		----------
		TypeError if 'target' is not of type 'ProductionTreeNodeBase'
		"""
		if not isinstance(self, ProductionTreeNodeBase):
			raise TypeError("'target' must be of type 'ProductionTree'")
		if target in self.out_connections:
			return
		self.out_connections.append(target)
		target.in_connections.append(self)
		return


class PT_RecipeNode(ProductionTreeNodeBase):
	def __init__(self, name: str, execs: float,
			in_flux: _collections_m_.Counter = {},
			out_flux: _collections_m_.Counter = {},
		) -> None:
		super(PT_RecipeNode, self).__init__("recipe")
		self.name = name
		self.execs = execs
		self.in_flux = _collections_m_.Counter(in_flux)
		self.out_flux = _collections_m_.Counter(out_flux)
		return

	def __str__(self):
		return "<%s name='%s' exec='%f' in_flux='%s' out_flux='%s'>"\
			% (type(self).__name__, self.name, self.execs,\
				str(self.in_flux), str(self.out_flux))

	def has_in_flux(self, item_name: str) -> bool:
		"""
		return True if this node has an in flux named 'item_name'
		"""
		return item_name in self.in_flux

	def has_out_flux(self, item_name: str) -> bool:
		"""
		return True if this node has an out flux named 'item_name'
		"""
		return item_name in self.out_flux


class PT_ItemSourceNode(ProductionTreeNodeBase):
	def __init__(self, item: str, count: float = 0.0) -> None:
		super(PT_ItemSourceNode, self).__init__("item-source")
		self.item = item
		self.count = count
		return

	def __str__(self):
		return "<%s item='%s' count='%f'>"\
			% (type(self).__name__, self.item, self.count)


class PT_ItemSinkNode(ProductionTreeNodeBase):
	def __init__(self, item: str, count: float = 0.0) -> None:
		super(PT_ItemSinkNode, self).__init__("item-sink")
		self.item = item
		self.count = count
		return

	def __str__(self):
		return "<%s item='%s' count='%f'>"\
			% (type(self).__name__, self.item, self.count)


class PT_FluxNode(ProductionTreeNodeBase):
	def __init__(self,
			flux: _collections_m_.Counter = {},
		) -> None:
		super(PT_FluxNode, self).__init__("flux")
		# ensure type
		self.flux = _collections_m_.Counter(flux)
		return

	def __str__(self):
		return "<%s flux='%s'>"\
			% (type(self).__name__, str(self.flux))

	# now since flux node has only one source and destination,
	# below two methods makes sence
	def get_src_node(self) -> bool:
		return self.in_connections[0]

	def get_dest_node(self) -> bool:
		return self.out_connections[0]


class ProductionTree(_production_profiler_m_.ProductionProfiler):
	"""
	tree constructor over production profiling results;
	"""
	def __init__(self, *ka, **kw) -> None:
		"""
		PARAMETERS
		----------
		see production_profiler.ProductionProfiler for detailed information;
		"""
		super(ProductionTree, self).__init__(*ka, **kw)
		# a list of all current nodes
		self._uuid_alloc_next = int(0)
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


	def _new_node(self,
			node_type: type,
			*ka, **kw,
		) -> ProductionTreeNodeBase:
		"""
		(internal only) return a new node of given note type, also adding it to
		the tree's tracking node list;

		EXCEPTIONS
		----------
		ValueError: if 'node_type' is not a subclass of 'ProductionTreeNodeBase'
		"""
		if not issubclass(node_type, ProductionTreeNodeBase):
			raise ValueError("'node_type' must be a subclass of\
				'ProductionTreeNodeBase'")
		node = node_type(*ka, **kw)
		self._tree_nodes_list.append(node)
		return node


	def construct_tree(self) -> None:
		"""
		construct the tree from scratch based on current profile;
		"""
		recp_nodes = self._create_and_link_recipe_nodes()
		self._resolve_flux(recp_nodes)
		pass


	def _create_and_link_recipe_nodes(self) -> dict:
		"""
		(internal only) create a dict of nodes that represents the calculated
		Recipe profile, including all the dependencies;

		RETURNS
		-------
		dict (in signature of "recipe": ProductionTreeNodeBase):
			the dict of all Recipe nodes; each node includes the exec count and
			in/out Item flux as attributes;
		"""
		node_dict = {}
		_, rexe, _, _ = self.get_current_profile()
		# first, create nodes
		for r, ex in rexe.items():
			# get recipe information
			recipe = self.get_recipe(r)
			# create node, add to tree
			rnode = self._new_node(PT_RecipeNode, name = r, execs = ex,
				in_flux = _collections_m_.Counter({k: v * ex\
					for (k, v) in recipe.inputs.items()}),
				out_flux = _collections_m_.Counter({k: v * ex\
					for (k, v) in recipe.products.items()})
			)
			# 
			node_dict[r] = rnode
		# second, make connections
		for r, rnode in node_dict.items():
			# get recipe information
			# create connection, one way is enough
			for dc in self.get_directly_connected_recipes(r, "down"):
				if dc in node_dict:
					self._connect_flux(rnode, node_dict[dc])
		return node_dict


	def _connect_flux(self,
			src_node: ProductionTreeNodeBase,
			dest_node: ProductionTreeNodeBase,
		) -> ProductionTreeNodeBase:
		"""
		(internal only) connect two nodes, inserting a new flux node in between;

		EXCEPTIONS
		----------
		TypeError: if either argument are not of type 'ProductionTreeNodeBase';
		"""
		if (not isinstance(src_node, ProductionTreeNodeBase)) or\
			(not isinstance(dest_node, ProductionTreeNodeBase)):
			raise TypeError("both nodes must be of type 'ProductionTreeNodeBase'")
		fnode = self._new_node(PT_FluxNode)
		src_node.connect(fnode)
		fnode.connect(dest_node)
		return fnode


	def _resolve_flux(self, recp_nodes):
		"""
		(internal only) resolve Item flux using constructed Recipe nodes;
		"""
		# terminal item nodes dicts
		sources = {}
		sinks = {}
		for node in recp_nodes.values():
			# resolve is done by requesting mode, i.e. downstream nodes
			# request resources from its uptreams
			for fname, fcount in node.in_flux.items():
				providers = self._list_flux_provider(node, fname)
				if not providers:
					self._add_terminal_node_flux("source",
						sources, node, fname, fcount)
				else:
					# TODO: figure out this and tree is done
					pass
			for fname, fcount in node.out_flux.items():
				requesters = self._list_flux_requester(node, fname)
				# no need to do if have requesters
				# that's repeatative with providers
				if not requesters:
					self._add_terminal_node_flux("sink",
						sinks, node, fname, fcount)
		return


	def _list_flux_provider(self, query_node, item_name):
		"""
		return a list of PT_RecipeNode's, which connects directly to the query
		node, and has an out flux of <item_name>;
		"""
		ret = []
		for flux in query_node.in_connections:
			s_node = flux.get_src_node()
			if isinstance(s_node, PT_RecipeNode)\
				and s_node.has_out_flux(item_name):
				ret.append(s_node)
		return ret


	def _list_flux_requester(self, query_node, item_name):
		"""
		return a list of PT_RecipeNode's, which connects directly to the query
		node, and has an out flux of <item_name>;
		"""
		ret = []
		for flux in query_node.out_connections:
			s_node = flux.get_dest_node()
			if isinstance(s_node, PT_RecipeNode)\
				and s_node.has_in_flux(item_name):
				ret.append(s_node)
		return ret


	def _add_terminal_node_flux(self,
			mode: str,
			node_dict: dict,
			query_node: ProductionTreeNodeBase,
			flux_item: str,
			flux_count: float,
		) -> None:
		"""
		add a source/sink node, with a <flux> connects to the 'req_node';
		"""
		# check value
		if mode == "source":
			node_type = PT_ItemSourceNode
		elif mode == "sink":
			node_type = PT_ItemSinkNode
		else:
			raise ValueError("'mode' must be either 'source' or 'sink'")
		# create node if not exists
		# not use setdefault since _new_node is called
		if flux_item not in node_dict:
			inode = self._new_node(node_type, item = flux_item, count = 0.0)
			node_dict[flux_item] = inode
		else:
			inode = node_dict[flux_item]
		assert inode.item == flux_item
		# update
		inode.count = inode.count + flux_count
		# connect to the query_node
		if mode == "source":
			fnode = self._connect_flux(inode, query_node)
		elif mode == "sink":
			fnode = self._connect_flux(query_node, inode)
		fnode.flux.update({flux_item: flux_count})
		return










































