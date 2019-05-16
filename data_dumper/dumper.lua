#!/usr/bin/env lua5.3

require("dump_util")


local function get_args()
	local usage = ([[%s <factorio-path> <module-path>

arguments:
    factorio-path: path to the Factorio install directory (required)
    module-path: path to the module to be dumped (required)
]]):format(arg[0])
	if (#arg ~= 2) then
		io.stderr:write("error: insufficient arguments\n\n" .. usage)
		os.exit(-1)
	end
	local factorio_path, module_path = table.unpack(arg)
	return factorio_path, module_path
end


local function quarantine_load(module_path)
	-- temporarily add module_path to the package.path for require modules
	-- restore package.path after require() to avoid namespace contamination
	-- especially for data.lua which is identically named by all modules

	-- load module_path/data.lua
	local old_package_path = package.path
	-- add module path
	local search_path = module_path .. "/?.lua"
	package.path = package.path .. ";" .. search_path
	-- load
	require("data")
	-- restore old search path
	package.path = old_package_path
	package.loaded["data"] = nil
	return _G["data"]
end


local function load_modules(factorio_path, module_path)
	-- dataloader is necessary
	package.path = package.path .. ";" .. factorio_path .. "/data/core/lualib/?.lua"
	require("dataloader")
	-- core maybe referenced by other modules
	--quarantine_load(factorio_path .. "/data/core")
	-- read module data
	quarantine_load(module_path)
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
			ret.results[v.name] = v.amount * (v.probability or 1.0)
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
	local factorio_path, module_path = get_args()
	load_modules(factorio_path, module_path)
	local recipes = extract_all_recipe_data(_G["data"].raw.recipe)
	dump_json(io.stdout, recipes)
	return os.exit(0)
end

main()
