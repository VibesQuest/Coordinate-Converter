local M = {}

local UNKNOWN_COORD_UI_MAP_ID = 0

local function ensure_bucket(result, map_id, coord_ui_map_id)
  result[map_id] = result[map_id] or {}
  result[map_id][coord_ui_map_id] = result[map_id][coord_ui_map_id] or {}
  return result[map_id][coord_ui_map_id]
end

local function round(value, decimals)
  local scale = 10 ^ decimals
  return math.floor(value * scale + 0.5) / scale
end

local function is_unknown_bucket(points)
  if not points or #points == 0 then
    return false
  end
  for _, point in ipairs(points) do
    if tonumber(point[1]) ~= -1 or tonumber(point[2]) ~= -1 then
      return false
    end
  end
  return true
end

local function is_unknown_point(point)
  return tonumber(point[1]) == -1 and tonumber(point[2]) == -1
end

local function normalize_point(point)
  local normalized = {tonumber(point[1]), tonumber(point[2])}
  for index = 3, #point do
    normalized[#normalized + 1] = point[index]
  end
  return normalized
end

local function should_emit_unknown_instance_bucket(pack, zone_area_id, map_id, point)
  return is_unknown_point(point)
end

local function target_coord_ui_map_id(pack, zone_space)
  local map_id = tonumber(zone_space.mapId)
  local coord_ui_map_id = pack.mapDefaultByMapId[map_id]
  if coord_ui_map_id ~= nil then
    return tonumber(coord_ui_map_id)
  end
  if zone_space.parentUiMapId ~= nil then
    return tonumber(zone_space.parentUiMapId)
  end
  return tonumber(zone_space.zoneUiMapId)
end

local function get_projection_bounds(pack, map_id, ui_map_id)
  local key = tostring(map_id) .. ":" .. tostring(ui_map_id)
  local bounds = pack.projectionBoundsByKey[key]
  if not bounds then
    error(string.format("No projection bounds for mapId=%d, uiMapId=%d", map_id, ui_map_id), 2)
  end
  return bounds
end

local function convert_legacy_point(pack, legacy_basis, zone_space, target_bounds, point)
  if legacy_basis ~= nil then
    if tonumber(legacy_basis.targetCoordUiMapId) == UNKNOWN_COORD_UI_MAP_ID then
      if (
        legacy_basis.transform == "identity"
        and tonumber(point[1]) == -1
        and tonumber(point[2]) == -1
      ) then
        return -1, -1
      end
      error(
        string.format(
          "Legacy key=%s maps to unresolved instance space; only {-1,-1} sentinel points are supported",
          tostring(legacy_basis.legacyKey)
        ),
        2
      )
    end
    if legacy_basis.transform == "identity" then
      return tonumber(point[1]), tonumber(point[2])
    end

    local source_bounds = get_projection_bounds(
      pack,
      tonumber(legacy_basis.mapId),
      tonumber(legacy_basis.sourceCoordUiMapId)
    )
    local world_x, world_y = M.invert_zone_percent_to_world(
      source_bounds,
      tonumber(point[1]),
      tonumber(point[2])
    )
    if target_bounds == nil then
      error("Missing target bounds for legacy reprojection", 2)
    end
    return M.project_world_to_percent(target_bounds, world_x, world_y)
  end

  if zone_space == nil then
    error("Missing zone-space record for legacy conversion", 2)
  end
  if target_bounds == nil then
    error("Missing target bounds for legacy reprojection", 2)
  end
  local world_x, world_y = M.invert_zone_percent_to_world(
    zone_space,
    tonumber(point[1]),
    tonumber(point[2])
  )
  return M.project_world_to_percent(target_bounds, world_x, world_y)
end

function M.invert_zone_percent_to_world(zone_space, zone_x, zone_y)
  local dx = tonumber(zone_space.worldXMax) - tonumber(zone_space.worldXMin)
  local dy = tonumber(zone_space.worldYMax) - tonumber(zone_space.worldYMin)
  if dx == 0 or dy == 0 then
    local source_label
    if zone_space.zoneAreaId ~= nil then
      source_label = string.format("zoneAreaId=%s", tostring(zone_space.zoneAreaId))
    else
      source_label = string.format(
        "mapId=%s, uiMapId=%s",
        tostring(zone_space.mapId),
        tostring(zone_space.uiMapId)
      )
    end
    error(string.format("Degenerate source bounds for %s", source_label), 2)
  end

  local world_y = tonumber(zone_space.worldYMax) - (zone_x / 100.0) * dy
  local world_x = tonumber(zone_space.worldXMax) - (zone_y / 100.0) * dx
  return world_x, world_y
end

function M.project_world_to_percent(bounds, world_x, world_y)
  local dx = tonumber(bounds.worldXMax) - tonumber(bounds.worldXMin)
  local dy = tonumber(bounds.worldYMax) - tonumber(bounds.worldYMin)
  if dx == 0 or dy == 0 then
    error(string.format("Degenerate target bounds for mapId=%s, uiMapId=%s", tostring(bounds.mapId), tostring(bounds.uiMapId)), 2)
  end

  local x = (tonumber(bounds.worldYMax) - world_y) / dy * 100.0
  local y = (tonumber(bounds.worldXMax) - world_x) / dx * 100.0
  return x, y
end

function M.convert_zone_buckets(pack, zone_buckets, coord_decimals)
  coord_decimals = coord_decimals or 2
  local result = {}

  for zone_area_id, points in pairs(zone_buckets) do
    local legacy_basis = pack.legacyBasisByKey[tonumber(zone_area_id)]
    local zone_space = pack.zoneSpaceByAreaId[tonumber(zone_area_id)]
    if legacy_basis == nil and zone_space == nil then
      error(string.format("No coordinate mapping for legacy key=%s", tostring(zone_area_id)), 2)
    end

    local map_id = legacy_basis and tonumber(legacy_basis.mapId) or tonumber(zone_space.mapId)
    local coord_ui_map_id = legacy_basis
      and tonumber(legacy_basis.targetCoordUiMapId)
      or target_coord_ui_map_id(pack, zone_space)
    local bounds = coord_ui_map_id == UNKNOWN_COORD_UI_MAP_ID
      and nil
      or get_projection_bounds(pack, map_id, coord_ui_map_id)
    local bucket = ensure_bucket(result, map_id, coord_ui_map_id)

    for _, point in ipairs(points) do
      if should_emit_unknown_instance_bucket(pack, zone_area_id, map_id, point) then
        local unknown_bucket = ensure_bucket(result, map_id, UNKNOWN_COORD_UI_MAP_ID)
        unknown_bucket[#unknown_bucket + 1] = {-1, -1}
        goto continue_point
      end
      local x, y = convert_legacy_point(pack, legacy_basis, zone_space, bounds, point)
      local coord_pair = {round(x, coord_decimals), round(y, coord_decimals)}
      if legacy_basis ~= nil and legacy_basis.defaultUiMapHintId ~= nil then
        coord_pair[#coord_pair + 1] = tonumber(legacy_basis.defaultUiMapHintId)
      end
      bucket[#bucket + 1] = coord_pair
      ::continue_point::
    end
  end

  return result
end

function M.replace_unknown_instance_buckets(pack, map_buckets)
  local result = {}

  for map_id, coord_buckets in pairs(map_buckets) do
    local numeric_map_id = tonumber(map_id)
    local anchor_record = pack.instanceAnchorByMapId[numeric_map_id]
    local bucket_count = 0
    local unknown_points = nil
    for coord_ui_map_id, points in pairs(coord_buckets) do
      bucket_count = bucket_count + 1
      if tonumber(coord_ui_map_id) == UNKNOWN_COORD_UI_MAP_ID then
        unknown_points = points
      end
    end

    if anchor_record and bucket_count == 1 and is_unknown_bucket(unknown_points) then
      for _, bucket in ipairs(anchor_record.entrances) do
        local out_bucket = ensure_bucket(
          result,
          tonumber(bucket.mapId),
          tonumber(bucket.coordUiMapId)
        )
        for _, point in ipairs(bucket.points) do
          out_bucket[#out_bucket + 1] = {tonumber(point[1]), tonumber(point[2])}
        end
      end
    else
      for coord_ui_map_id, points in pairs(coord_buckets) do
        local out_bucket = ensure_bucket(result, numeric_map_id, tonumber(coord_ui_map_id))
        for _, point in ipairs(points) do
          out_bucket[#out_bucket + 1] = normalize_point(point)
        end
      end
    end
  end

  return result
end

return M
