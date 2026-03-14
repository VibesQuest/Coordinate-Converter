local M = {}

local function decode_error(message, index)
  error(string.format("json decode error at %d: %s", index, message), 2)
end

local function skip_ws(text, index)
  while true do
    local c = text:sub(index, index)
    if c == "" then
      return index
    end
    if c ~= " " and c ~= "\n" and c ~= "\r" and c ~= "\t" then
      return index
    end
    index = index + 1
  end
end

local parse_value

local function parse_string(text, index)
  index = index + 1
  local out = {}

  while true do
    local c = text:sub(index, index)
    if c == "" then
      decode_error("unterminated string", index)
    end
    if c == '"' then
      return table.concat(out), index + 1
    end
    if c == "\\" then
      local esc = text:sub(index + 1, index + 1)
      if esc == '"' or esc == "\\" or esc == "/" then
        out[#out + 1] = esc
        index = index + 2
      elseif esc == "b" then
        out[#out + 1] = "\b"
        index = index + 2
      elseif esc == "f" then
        out[#out + 1] = "\f"
        index = index + 2
      elseif esc == "n" then
        out[#out + 1] = "\n"
        index = index + 2
      elseif esc == "r" then
        out[#out + 1] = "\r"
        index = index + 2
      elseif esc == "t" then
        out[#out + 1] = "\t"
        index = index + 2
      elseif esc == "u" then
        local hex = text:sub(index + 2, index + 5)
        if not hex:match("^[0-9a-fA-F][0-9a-fA-F][0-9a-fA-F][0-9a-fA-F]$") then
          decode_error("invalid unicode escape", index)
        end
        out[#out + 1] = utf8.char(tonumber(hex, 16))
        index = index + 6
      else
        decode_error("invalid escape sequence", index)
      end
    else
      out[#out + 1] = c
      index = index + 1
    end
  end
end

local function parse_number(text, index)
  local start_index = index
  local c = text:sub(index, index)
  if c == "-" then
    index = index + 1
  end

  local int_part = text:sub(index, index)
  if int_part == "0" then
    index = index + 1
  else
    if not int_part:match("%d") then
      decode_error("invalid number", index)
    end
    repeat
      index = index + 1
      c = text:sub(index, index)
    until not c:match("%d")
  end

  c = text:sub(index, index)
  if c == "." then
    index = index + 1
    if not text:sub(index, index):match("%d") then
      decode_error("invalid fractional part", index)
    end
    repeat
      index = index + 1
      c = text:sub(index, index)
    until not c:match("%d")
  end

  c = text:sub(index, index)
  if c == "e" or c == "E" then
    index = index + 1
    c = text:sub(index, index)
    if c == "+" or c == "-" then
      index = index + 1
    end
    if not text:sub(index, index):match("%d") then
      decode_error("invalid exponent", index)
    end
    repeat
      index = index + 1
      c = text:sub(index, index)
    until not c:match("%d")
  end

  local value = tonumber(text:sub(start_index, index - 1))
  if value == nil then
    decode_error("invalid number", start_index)
  end
  return value, index
end

local function parse_array(text, index)
  index = index + 1
  local result = {}
  index = skip_ws(text, index)
  if text:sub(index, index) == "]" then
    return result, index + 1
  end

  while true do
    local value
    value, index = parse_value(text, index)
    result[#result + 1] = value
    index = skip_ws(text, index)
    local c = text:sub(index, index)
    if c == "]" then
      return result, index + 1
    end
    if c ~= "," then
      decode_error("expected ',' or ']'", index)
    end
    index = skip_ws(text, index + 1)
  end
end

local function parse_object(text, index)
  index = index + 1
  local result = {}
  index = skip_ws(text, index)
  if text:sub(index, index) == "}" then
    return result, index + 1
  end

  while true do
    if text:sub(index, index) ~= '"' then
      decode_error("expected string key", index)
    end
    local key
    key, index = parse_string(text, index)
    index = skip_ws(text, index)
    if text:sub(index, index) ~= ":" then
      decode_error("expected ':'", index)
    end
    index = skip_ws(text, index + 1)
    local value
    value, index = parse_value(text, index)
    result[key] = value
    index = skip_ws(text, index)
    local c = text:sub(index, index)
    if c == "}" then
      return result, index + 1
    end
    if c ~= "," then
      decode_error("expected ',' or '}'", index)
    end
    index = skip_ws(text, index + 1)
  end
end

function parse_value(text, index)
  index = skip_ws(text, index)
  local c = text:sub(index, index)
  if c == '"' then
    return parse_string(text, index)
  end
  if c == "{" then
    return parse_object(text, index)
  end
  if c == "[" then
    return parse_array(text, index)
  end
  if c == "-" or c:match("%d") then
    return parse_number(text, index)
  end
  if text:sub(index, index + 3) == "true" then
    return true, index + 4
  end
  if text:sub(index, index + 4) == "false" then
    return false, index + 5
  end
  if text:sub(index, index + 3) == "null" then
    return nil, index + 4
  end
  decode_error("unexpected token", index)
end

function M.decode(text)
  local value, index = parse_value(text, 1)
  index = skip_ws(text, index)
  if index <= #text then
    decode_error("trailing characters", index)
  end
  return value
end

return M
