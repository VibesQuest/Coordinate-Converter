local M = {}
local json = require("json")

local FILES = {
  manifest = "manifest.json",
  zoneSpaces = "zone_spaces.json",
  projectionBounds = "projection_bounds.json",
  mapDefaults = "map_defaults.json",
  legacyBases = "legacy_bases.json",
  instanceAnchors = "instance_anchors.json",
}
local CURRENT_SCHEMA_VERSION = 2

local function assertf(value, message)
  if not value then
    error(message, 2)
  end
  return value
end

function M.load_coordinate_pack(pack_dir, opts)
  opts = opts or {}
  local read_file = assertf(opts.read_file, "opts.read_file is required")
  local json_decode = opts.json_decode or json.decode

  local pack = {}
  for key, filename in pairs(FILES) do
    local text = assertf(read_file(pack_dir .. "/" .. filename), "failed to read " .. filename)
    pack[key] = assertf(json_decode(text), "failed to decode " .. filename)
  end
  local schema_version = tonumber(pack.manifest.schemaVersion)
  assertf(
    schema_version == CURRENT_SCHEMA_VERSION,
    string.format(
      "unsupported coordinate pack schemaVersion=%s in %s/%s; expected %d",
      tostring(pack.manifest.schemaVersion),
      tostring(pack_dir),
      FILES.manifest,
      CURRENT_SCHEMA_VERSION
    )
  )

  pack.zoneSpaceByAreaId = {}
  for _, row in ipairs(pack.zoneSpaces) do
    pack.zoneSpaceByAreaId[tonumber(row.zoneAreaId)] = row
  end

  pack.projectionBoundsByKey = {}
  for _, row in ipairs(pack.projectionBounds) do
    local key = tostring(tonumber(row.mapId)) .. ":" .. tostring(tonumber(row.uiMapId))
    pack.projectionBoundsByKey[key] = row
  end

  pack.mapDefaultByMapId = {}
  for _, row in ipairs(pack.mapDefaults) do
    pack.mapDefaultByMapId[tonumber(row.mapId)] = tonumber(row.coordUiMapId)
  end

  pack.legacyBasisByKey = {}
  for _, row in ipairs(pack.legacyBases) do
    pack.legacyBasisByKey[tonumber(row.legacyKey)] = row
  end

  pack.instanceAnchorByMapId = {}
  for _, row in ipairs(pack.instanceAnchors) do
    pack.instanceAnchorByMapId[tonumber(row.instanceMapId)] = row
  end

  pack.instanceAnchorByZoneAreaId = {}
  for _, row in ipairs(pack.instanceAnchors) do
    if row.zoneAreaId ~= nil then
      pack.instanceAnchorByZoneAreaId[tonumber(row.zoneAreaId)] = row
    end
  end

  return pack
end

return M
