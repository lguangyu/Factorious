#!/usr/bin/env lua5.3

require("dump_util")


local function get_args()
	local usage = ([[%s <data-path> <module-path>

arguments:
    data-path: path to the Factorio/data directory (required)
    module-path: path to the module to be dumped (required)
]]):format(arg[0])
	if (#arg ~= 2) then
		io.stderr:write("error: insufficient arguments\n\n" .. usage)
		os.exit(-1)
	end
	local data_path, module_path = table.unpack(arg)
	return data_path, module_path
end

local function quarantine_load(module_path, module_file, reset_load_flag)
	--[[
	load data from Factorio's module.
	this is essentially done by:
		require(module_file)
	i.e. load <module_path>/<module_file>.lua;
	before we actually do this, the search path must be first added;
	after loading, the search path will be restored; thus it's ready for load
	the next module (if needed) to avoid namespace contamination;
	that is, critical for modules since 'data.lua' commonly exists in every
	module; we need to clean up the search path to ensure that the newest call
	to require(module_file) loads the desired file.
	]]
	if reset_load_flag == nil then
		reset_load_flag = true
	end

	-- load data.lua
	local old_package_path = package.path
	package.path = package.path .. ";" .. module_path .. "/?.lua"
	require(module_file)
	-- restore old search path and reset the loaded flag
	-- this will force lua to forget the module is somewhat loaded
	package.path = old_package_path
	if reset_load_flag then
		package.loaded[module_file] = nil
	end
	return _G["data"]
end

local function load_base_module(data_path)
	-- this loads necessities, must be done first even before core is loaded
	package.path = package.path .. ";" .. data_path .. "/core/lualib/?.lua"
	quarantine_load(data_path .. "/core/lualib", "util", false)
	quarantine_load(data_path .. "/core/lualib", "dataloader")
	-- now load core first
	quarantine_load(data_path .. "/core", "data")
	_G["data"].is_demo = false
	-- this loads <data_path>/base/data.lua
	quarantine_load(data_path .. "/base", "data")
	return _G["data"]
end

local function extract_recipe_formula(formula)
	local ret = {}
	-- craft time
	ret.craft_time = formula.energy_required or 0.5
	-- ingredients
	ret.ingredients = {}
	for _, v in ipairs(formula.ingredients) do
		if (v.name) then
			ret.ingredients[v.name] = v.amount -- fluid format
		else
			ret.ingredients[v[1]] = v[2] -- {item, count} -> table[item] = count
		end
	end
	-- results
	ret.results = {}
	if (formula.results) then
		for _, v in ipairs(formula.results) do
			if v.name then
				ret.results[v.name] = v.amount * (v.probability or 1)
			else
				ret.results[v[1]] = v[2] * (v.probability or 1)
			end
		end
	else
		ret.results[formula.result] = formula.result_count or 1
	end
	return ret
end

local function extract_recipe_data(recipe)
	assert(recipe.type == "recipe", recipe.type)
	local ret = {}
	-- name of the recipe
	ret.name = recipe.name
	-- category
	ret.category = recipe.category or "crafting"
	-- has normal/expensive modes?
	if (recipe.expensive) then
		ret.normal = extract_recipe_formula(recipe.normal)
		ret.expensive = extract_recipe_formula(recipe.expensive)
	else
		ret.normal = extract_recipe_formula(recipe)
		ret.expensive = nil
	end
	return ret
end

local function extract_all_recipe_data(recipes)
	assert(type(recipes) == "table", type(recipes))
	local ret = {}
	for name, recipe in pairs(recipes) do
		ret[name] = extract_recipe_data(recipe)
	end
	return ret
end

function main()
	local data_path, module_path = get_args()
	load_base_module(data_path)
	local recipes = extract_all_recipe_data(_G["data"].raw.recipe)
	dump_json(io.stdout, recipes)
	return os.exit(0)
end

main()
