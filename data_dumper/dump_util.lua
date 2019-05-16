#!/usr/bin/env lua5.3


-- get rid of any references into table 'defines'
defines = {}
setmetatable(defines, {
	-- index anything in 'defines' simply return defines itself
	__index = function(self, key)
		_raw = rawget(self, key)
		if _raw then
			return _raw
		else
			return self
		end
	end
})


-- dump table as json
local function to_json_scalar(value)
	local _type = type(value)
	if (_type == "number") then
		return tostring(value)
	elseif (_type == "boolean") then
		return tostring(value)
	elseif (_type == "string") then
		return ("\"" .. value .. "\"")
	elseif (_type == "nil") then
		return "null"
	else
		error(("unexpected value type: %s"):format(type(value)))
	end
	return
end

function dump_json(file, table)
	assert(type(table) == "table", type(table))
	local sec_begin, sec_end, iter_meth

	if (table[1] ~= nil) then
		sec_begin, sec_end = "[", "]"
		iter_meth = ipairs
	else
		sec_begin, sec_end = "{", "}"
		iter_meth = pairs
	end

	-- dump section data
	local n_items = 0
	file:write(sec_begin)
	for k, v in iter_meth(table) do
		assert((type(k) == "number") or (type(k) == "string"), k)
		-- should add a separator?
		if (n_items > 0) then
			file:write(",")
		end
		n_items = n_items + 1
		-- should write the key?
		if (sec_begin == "{") then
			file:write(to_json_scalar(k) .. ":")
		end
		-- dump value
		-- is a table? if so, recurse
		if (type(v) == "table") then
			dump_json(file, v)
		else
			file:write(to_json_scalar(v))
		end
	end
	file:write(sec_end)
	return
end
