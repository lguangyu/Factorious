#!/usr/bin/env python3

import collections as _collections_m_


class _FactorioTunes(object):
	# namespace use
	# an attribute-index safe
	def __init__(self, *ka, **kw):
		super(_FactorioTunes, self).__init__()
		return


class FactorioTunes015(_FactorioTunes):
	def __init__(self, *ka, **kw):
		super(FactorioTunes015, self).__init__(*ka, **kw)
		# crafter settings
		self.CRAFTERS = {
			"assembling-machine-1": {
				"repr": "asm-1",
				"recipe_type": ["crafting", "advanced-crafting"],
				"speed": 0.50,
			},
			"assembling-machine-2": {
				"repr": "asm-2",
				"recipe_type": ["crafting", "advanced-crafting", "crafting-with-fluid"],
				"speed": 0.75,
			},
			"assembling-machine-3": {
				"repr": "asm-3",
				"recipe_type": ["crafting", "advanced-crafting", "crafting-with-fluid"],
				"speed": 1.25,
			},
			"centrifuge": {
				"recipe_type": ["centrifuging"],
				"speed": 0.75,
			},
			"chemical-plant": {
				"recipe_type": ["chemistry"],
				"speed": 1.25,
			},
			"electric-furnace": {
				"repr": "fnc-3",
				"recipe_type": ["smelting"],
				"speed": 2.00,
			},
			"oil-refinery": {
				"recipe_type": ["oil-processing"],
				"speed": 1.00,
			},
			"rocket-silo": {
				"recipe_type": ["rocket-building"],
				"speed": 1.00,
			},
			"steel-furnace": {
				"repr": "fnc-2",
				"recipe_type": ["smelting"],
				"speed": 2.00,
			},
			"stone-furnace": {
				"repr": "fnc-1",
				"recipe_type": ["smelting"],
				"speed": 1.00,
			},
			"nuclear-reactor": {
				"recipe_type": ["uranium-as-fuel"],
				"speed": 1.00,
			},
		}

		# create a "category": ["crafter"] dict
		self.RECIPE_CATEGORIES = _collections_m_.defaultdict(list)
		for k, v in self.CRAFTERS.items():
			for t in v["recipe_type"]:
				self.RECIPE_CATEGORIES[t].append(k)
		for v in self.RECIPE_CATEGORIES.values():
			v.sort(key = lambda x: self.CRAFTERS[x].get("repr", x),\
				reverse = True)

		# commonly-known as trivials
		self.COMMON_TRIVIALS = [
			"steam",
			"water",
		]
		# concatenated
		self.COMMON_TRIVIALS_STR = ",".join(self.COMMON_TRIVIALS)

		# fluids
		self.FLUIDS = [
			"crude-oil",
			"heavy-oil",
			"light-oil",
			"lubricant",
			"petroleum-gas",
			"steam",
			"sulfuric-acid",
			"water",
		]
	
		# these are item conversions not included in real recipes
		# missing these may end up with unexpected results
		self.MADEUP_RECIPES = [
			{
				"category": "uranium-as-fuel",
				"expensive": None,
				"name": "uranium-fuel-consumption",
				"normal": {
					"craft_time": 200.0,
					"ingredients": {
						"uranium-fuel-cell": 1
					},
					"results": {
						"used-up-uranium-fuel-cell": 1
					}
				}
			}
		]

		# if encounter these things in calculation,force put them onto the
		# optimization list;
		# though cases are rare, if not force such thing to use optimization,
		# it will poison the optimization later
		#
		# example is "heavy-oil" when disabling basic and advanced oil processings
		# then since coal liquefaction is the only recipe, it is non-ambiguous;
		# but balancing the side products of it is toxic
		#
		# 2019-03-09 update:
		# CURRENTLY DEPRECATED
		# now all products of a multi-product recipe are forced to going through
		# optimizer, obviously including heavy-oil
		#self.ENFORCE_OPTIMIZE = [
		#	"heavy-oil",
		#]

		# accompany this item in optimization process
		# if force the 
		self.ITEM_ACCOMPANY = {
			"uranium-fuel-cell": {"used-up-uranium-fuel-cell": 1},
		}
		return


def load_factorio_version_tunes(version: str) -> _FactorioTunes:
	"""
	get Factorio tunes configs

	PARAMETERS
	----------
	version:
		str of Factorio version;

	EXCEPTIONS
	----------
	LookupError: if <version> does not match anything in database
	"""
	if version == "0.15":
		return FactorioTunes015()
	else:
		LookupError("bad Factorio version descriptor: '%s'" % version)
