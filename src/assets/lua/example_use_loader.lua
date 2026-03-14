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

local function read_file(path)
  local handle = assert(io.open(path, "r"))
  local text = handle:read("*a")
  handle:close()
  return text
end

local pack_root = base_dir .. "../.."
local pack = loader.load_coordinate_pack(pack_root, {
  read_file = read_file,
})

print("flavor:", pack.manifest.flavor)
print("map 0 default coordUiMapId:", pack.mapDefaultByMapId[0])
