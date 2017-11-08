#!/usr/bin/lua
--lua Recipe2Json.lua 1>recipe.json 2>odd_recipe.json

data = {
	recipes = {}
}

function data:extend(tbl)
	for _, v in pairs(tbl) do
		table.insert(self.recipes, v)
	end
end

function concatItemList(list, level)
	local ret = nil
	for i, v in ipairs(list) do
		ret = (ret and ret..",\n" or "\n")..string.rep("\t", level).."\""..(v.name or v[1]).."\": "..(v.amount or v[2])
	end
	return ret
end

function isOddRecipe(recipe)
	local root = recipe.normal or recipe
	return recipe.name == (root.result or (root.results and (root.results[1][1] or root.results[1].name)))
end

function writeRecipe(recipe, ostream)
	ostream:write(("\t\"%s\": {\n"):format(recipe.name))
	ostream:write(("\t\t\"category\": \"%s\",\n"):format(recipe.category or "crafting"))
	if (recipe.normal) then
		ostream:write("\t\t\"normal\": {\n")
		ostream:write(("\t\t\t\"craft_time\": %.1f,\n"):format(recipe.normal.energy_required or 0.5))
		ostream:write(("\t\t\t\"ingredients\": {%s\n\t\t\t},\n"):format(concatItemList(recipe.normal.ingredients, 4)))
		if (recipe.normal.results) then
			ostream:write(("\t\t\t\"results\": {%s\n\t\t\t}\n"):format(concatItemList(recipe.normal.results, 4)))
		else
			ostream:write(("\t\t\t\"result_count\": %s\n"):format(recipe.normal.amount or 1))
		end
		ostream:write("\t\t},\n")
		ostream:write("\t\t\"expensive\": {\n")
		ostream:write(("\t\t\t\"craft_time\": %.1f,\n"):format(recipe.normal.energy_required or 0.5))
		ostream:write(("\t\t\t\"ingredients\": {%s\n\t\t\t},\n"):format(concatItemList(recipe.expensive.ingredients, 4)))
		if (recipe.expensive.results) then
			ostream:write(("\t\t\t\"results\": {%s\n\t\t\t}\n"):format(concatItemList(recipe.expensive.results, 4)))
		else
			ostream:write(("\t\t\t\"result_count\": %s\n"):format(recipe.expensive.amount or 1))
		end
		ostream:write("\t\t}\n")
	else
		ostream:write(("\t\t\"craft_time\": %.1f,\n"):format(recipe.energy_required or 0.5))
		ostream:write(("\t\t\"ingredients\": {%s\n\t\t},\n"):format(concatItemList(recipe.ingredients, 3)))
		if (recipe.results) then
			ostream:write(("\t\t\"results\": {%s\n\t\t}\n"):format(concatItemList(recipe.results, 3)))
		else
			ostream:write(("\t\t\"result_count\": %s\n"):format(recipe.amount or recipe.result_count or 1))
		end
	end
	ostream:write(("\t}"):format(recipe.name))
end

function data:rewrite()
	local stdout_flag, stderr_flag = false, false
	io.stdout:write("{")
	io.stderr:write("{")
	local target
	for i, v in ipairs(self.recipes) do
		if (not isOddRecipe(v)) then
			if (not stderr_flag) then
				stderr_flag = true
				io.stderr:write("\n")
			else
				io.stderr:write(",\n")
			end
			writeRecipe(v, io.stderr)
		else
			if (not stdout_flag) then
				stdout_flag = true
				io.stdout:write("\n")
			else
				io.stdout:write(",\n")
			end
			writeRecipe(v, io.stdout)
		end
	end
	io.stdout:write("\n}\n")
	io.stderr:write("\n}\n")
end

require("raw.all_recipe")

data:rewrite()
