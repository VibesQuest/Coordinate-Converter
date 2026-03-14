local function script_dir()
  local source = debug.getinfo(1, "S").source
  if source:sub(1, 1) == "@" then
    source = source:sub(2)
  end
  return source:match("^(.*[/\\])") or "./"
end

local base_dir = script_dir()
package.path = base_dir .. "?.lua;" .. package.path

local loader = require("coords_loader")
local converter = require("coords_converter")

local function read_file(path)
  local handle = assert(io.open(path, "r"))
  local text = handle:read("*a")
  handle:close()
  return text
end

local function dump_table(value, indent)
  indent = indent or ""
  if type(value) ~= "table" then
    return tostring(value)
  end

  local parts = {"{"}
  local next_indent = indent .. "  "
  for key, inner in pairs(value) do
    parts[#parts + 1] = string.format("\n%s%s = %s,", next_indent, tostring(key), dump_table(inner, next_indent))
  end
  parts[#parts + 1] = "\n" .. indent .. "}"
  return table.concat(parts)
end

local pack_root = base_dir .. "../.."
local pack = loader.load_coordinate_pack(pack_root, {
  read_file = read_file,
})

local zone_result = converter.convert_zone_buckets(pack, {
  [12] = {
    {42.1, 65.3},
  },
})
local instance_result = converter.replace_unknown_instance_buckets(pack, {
  [36] = {
    [0] = {
      {-1, -1},
    },
  },
})

print("zone conversion:", dump_table(zone_result))
print("instance fallback:", dump_table(instance_result))
