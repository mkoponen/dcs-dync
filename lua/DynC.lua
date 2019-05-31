do
	-- Default value for socket. You may want to change this line if something in your computer already uses this socket.
	dync.socket = "http://127.0.0.1:44444"
	
	---------------------------------------------------------------------------------------
	-- Below here, you probably don't want to change anything unless you know the code well
	---------------------------------------------------------------------------------------
	
	package.path  = package.path..";.\\LuaSocket\\?.lua;"
	package.cpath = package.cpath..";.\\LuaSocket\\?.dll;"

	local http = require("dync_httpfix")
	local ltn12 = require('ltn12')

	-----------------------------------------------------------------------------
	-- Module declaration
	-----------------------------------------------------------------------------
	local json = {}             -- Public namespace
	local json_private = {}     -- Private namespace

	-- Public constants
	json.EMPTY_ARRAY={}
	json.EMPTY_OBJECT={}

	-- Public functions

	-- Private functions
	local decode_scanArray
	local decode_scanComment
	local decode_scanConstant
	local decode_scanNumber
	local decode_scanObject
	local decode_scanString
	local decode_scanWhitespace
	local encodeString
	local isArray
	local isEncodable

	local server = nil

	function string.starts(String,Start)
	   return string.sub(String,1,string.len(Start))==Start
	end

	function string.split(inputstr, sep)
			if sep == nil then
					sep = "%s"
			end
			local t={} ; i=0
			for str in string.gmatch(inputstr, "([^"..sep.."]+)") do
					t[i] = str
					i = i + 1
			end
			return t
	end

	-----------------------------------------------------------------------------
	-- PUBLIC FUNCTIONS
	-----------------------------------------------------------------------------
	--- Encodes an arbitrary Lua object / variable.
	-- @param v The Lua object / variable to be JSON encoded.
	-- @return String containing the JSON encoding in internal Lua string format (i.e. not unicode)
	function json.encode (v)
	  -- Handle nil values
	  if v==nil then
		return "null"
	  end

	  local vtype = type(v)

	  -- Handle strings
	  if vtype=='string' then
		return '"' .. json_private.encodeString(v) .. '"'	    -- Need to handle encoding in string
	  end

	  -- Handle booleans
	  if vtype=='number' or vtype=='boolean' then
		return tostring(v)
	  end

	  -- Handle tables
	  if vtype=='table' then
		local rval = {}
		-- Consider arrays separately
		local bArray, maxCount = isArray(v)
		if bArray then
		  for i = 1,maxCount do
			table.insert(rval, json.encode(v[i]))
		  end
		else	-- An object, not an array
		  for i,j in pairs(v) do
			if isEncodable(i) and isEncodable(j) then
			  table.insert(rval, '"' .. json_private.encodeString(i) .. '":' .. json.encode(j))
			end
		  end
		end
		if bArray then
		  return '[' .. table.concat(rval,',') ..']'
		else
		  return '{' .. table.concat(rval,',') .. '}'
		end
	  end

	  -- Handle null values
	  if vtype=='function' and v==json.null then
		return 'null'
	  end

	  assert(false,'encode attempt to encode unsupported type ' .. vtype .. ':' .. tostring(v))
	end


	--- Decodes a JSON string and returns the decoded value as a Lua data structure / value.
	-- @param s The string to scan.
	-- @param [startPos] Optional starting position where the JSON string is located. Defaults to 1.
	-- @param Lua object, number The object that was scanned, as a Lua table / string / number / boolean or nil,
	-- and the position of the first character after
	-- the scanned JSON object.
	function json.decode(s, startPos)
	  startPos = startPos and startPos or 1
	  startPos = decode_scanWhitespace(s,startPos)
	  assert(startPos<=string.len(s), 'Unterminated JSON encoded object found at position in [' .. s .. ']')
	  local curChar = string.sub(s,startPos,startPos)
	  -- Object
	  if curChar=='{' then
		return decode_scanObject(s,startPos)
	  end
	  -- Array
	  if curChar=='[' then
		return decode_scanArray(s,startPos)
	  end
	  -- Number
	  if string.find("+-0123456789.e", curChar, 1, true) then
		return decode_scanNumber(s,startPos)
	  end
	  -- String
	  if curChar==[["]] or curChar==[[']] then
		return decode_scanString(s,startPos)
	  end
	  if string.sub(s,startPos,startPos+1)=='/*' then
		return json.decode(s, decode_scanComment(s,startPos))
	  end
	  -- Otherwise, it must be a constant
	  return decode_scanConstant(s,startPos)
	end

	--- The null function allows one to specify a null value in an associative array (which is otherwise
	-- discarded if you set the value with 'nil' in Lua. Simply set t = { first=json.null }
	function json.null()
	  return json.null -- so json.null() will also return null ;-)
	end
	-----------------------------------------------------------------------------
	-- Internal, PRIVATE functions.
	-- Following a Python-like convention, I have prefixed all these 'PRIVATE'
	-- functions with an underscore.
	-----------------------------------------------------------------------------

	--- Scans an array from JSON into a Lua object
	-- startPos begins at the start of the array.
	-- Returns the array and the next starting position
	-- @param s The string being scanned.
	-- @param startPos The starting position for the scan.
	-- @return table, int The scanned array as a table, and the position of the next character to scan.
	function decode_scanArray(s,startPos)
	  local array = {}	-- The return value
	  local stringLen = string.len(s)
	  assert(string.sub(s,startPos,startPos)=='[','decode_scanArray called but array does not start at position ' .. startPos .. ' in string:\n'..s )
	  startPos = startPos + 1
	  -- Infinite loop for array elements
	  local index = 1
	  repeat
		startPos = decode_scanWhitespace(s,startPos)
		assert(startPos<=stringLen,'JSON String ended unexpectedly scanning array.')
		local curChar = string.sub(s,startPos,startPos)
		if (curChar==']') then
		  return array, startPos+1
		end
		if (curChar==',') then
		  startPos = decode_scanWhitespace(s,startPos+1)
		end
		assert(startPos<=stringLen, 'JSON String ended unexpectedly scanning array.')
		object, startPos = json.decode(s,startPos)
		array[index] = object
		index = index + 1
	  until false
	end

	--- Scans a comment and discards the comment.
	-- Returns the position of the next character following the comment.
	-- @param string s The JSON string to scan.
	-- @param int startPos The starting position of the comment
	function decode_scanComment(s, startPos)
	  assert( string.sub(s,startPos,startPos+1)=='/*', "decode_scanComment called but comment does not start at position " .. startPos)
	  local endPos = string.find(s,'*/',startPos+2)
	  assert(endPos~=nil, "Unterminated comment in string at " .. startPos)
	  return endPos+2
	end

	--- Scans for given constants: true, false or null
	-- Returns the appropriate Lua type, and the position of the next character to read.
	-- @param s The string being scanned.
	-- @param startPos The position in the string at which to start scanning.
	-- @return object, int The object (true, false or nil) and the position at which the next character should be
	-- scanned.
	function decode_scanConstant(s, startPos)
	  local consts = { ["true"] = true, ["false"] = false, ["null"] = nil }
	  local constNames = {"true","false","null"}

	  for i,k in pairs(constNames) do
		if string.sub(s,startPos, startPos + string.len(k) -1 )==k then
		  return consts[k], startPos + string.len(k)
		end
	  end
	  assert(nil, 'Failed to scan constant from string ' .. s .. ' at starting position ' .. startPos)
	end

	--- Scans a number from the JSON encoded string.
	-- (in fact, also is able to scan numeric +- eqns, which is not
	-- in the JSON spec.)
	-- Returns the number, and the position of the next character
	-- after the number.
	-- @param s The string being scanned.
	-- @param startPos The position at which to start scanning.
	-- @return number, int The extracted number and the position of the next character to scan.
	function decode_scanNumber(s,startPos)
	  local endPos = startPos+1
	  local stringLen = string.len(s)
	  local acceptableChars = "+-0123456789.e"
	  while (string.find(acceptableChars, string.sub(s,endPos,endPos), 1, true)
		and endPos<=stringLen
		) do
		endPos = endPos + 1
	  end
	  local stringValue = 'return ' .. string.sub(s,startPos, endPos-1)
	  --local stringEval = load(stringValue)
	  local stringEval = loadstring(stringValue)
	  assert(stringEval, 'Failed to scan number [ ' .. stringValue .. '] in JSON string at position ' .. startPos .. ' : ' .. endPos)
	  return stringEval(), endPos
	end

	--- Scans a JSON object into a Lua object.
	-- startPos begins at the start of the object.
	-- Returns the object and the next starting position.
	-- @param s The string being scanned.
	-- @param startPos The starting position of the scan.
	-- @return table, int The scanned object as a table and the position of the next character to scan.
	function decode_scanObject(s,startPos)
	  local object = {}
	  local stringLen = string.len(s)
	  local key, value
	  assert(string.sub(s,startPos,startPos)=='{','decode_scanObject called but object does not start at position ' .. startPos .. ' in string:\n' .. s)
	  startPos = startPos + 1
	  repeat
		startPos = decode_scanWhitespace(s,startPos)
		assert(startPos<=stringLen, 'JSON string ended unexpectedly while scanning object.')
		local curChar = string.sub(s,startPos,startPos)
		if (curChar=='}') then
		  return object,startPos+1
		end
		if (curChar==',') then
		  startPos = decode_scanWhitespace(s,startPos+1)
		end
		assert(startPos<=stringLen, 'JSON string ended unexpectedly scanning object.')
		-- Scan the key
		key, startPos = json.decode(s,startPos)
		assert(startPos<=stringLen, 'JSON string ended unexpectedly searching for value of key ' .. key)
		startPos = decode_scanWhitespace(s,startPos)
		assert(startPos<=stringLen, 'JSON string ended unexpectedly searching for value of key ' .. key)
		assert(string.sub(s,startPos,startPos)==':','JSON object key-value assignment mal-formed at ' .. startPos)
		startPos = decode_scanWhitespace(s,startPos+1)
		assert(startPos<=stringLen, 'JSON string ended unexpectedly searching for value of key ' .. key)
		value, startPos = json.decode(s,startPos)
		object[key]=value
	  until false	-- infinite loop while key-value pairs are found
	end

	-- START SoniEx2
	-- Initialize some things used by decode_scanString
	-- You know, for efficiency
	local escapeSequences = {
	  ["\\t"] = "\t",
	  ["\\f"] = "\f",
	  ["\\r"] = "\r",
	  ["\\n"] = "\n",
	  ["\\b"] = "\b"
	}
	setmetatable(escapeSequences, {__index = function(t,k)
	  -- skip "\" aka strip escape
	  return string.sub(k,2)
	end})
	-- END SoniEx2

	--- Scans a JSON string from the opening inverted comma or single quote to the
	-- end of the string.
	-- Returns the string extracted as a Lua string,
	-- and the position of the next non-string character
	-- (after the closing inverted comma or single quote).
	-- @param s The string being scanned.
	-- @param startPos The starting position of the scan.
	-- @return string, int The extracted string as a Lua string, and the next character to parse.
	function decode_scanString(s,startPos)
	  assert(startPos, 'decode_scanString(..) called without start position')
	  local startChar = string.sub(s,startPos,startPos)
	  -- START SoniEx2
	  -- PS: I don't think single quotes are valid JSON
	  assert(startChar == [["]] or startChar == [[']],'decode_scanString called for a non-string')
	  --assert(startPos, "String decoding failed: missing closing " .. startChar .. " for string at position " .. oldStart)
	  local t = {}
	  local i,j = startPos,startPos
	  while string.find(s, startChar, j+1) ~= j+1 do
		local oldj = j
		i,j = string.find(s, "\\.", j+1)
		local x,y = string.find(s, startChar, oldj+1)
		if not i or x < i then
		  i,j = x,y-1
		end
		table.insert(t, string.sub(s, oldj+1, i-1))
		if string.sub(s, i, j) == "\\u" then
		  local a = string.sub(s,j+1,j+4)
		  j = j + 4
		  local n = tonumber(a, 16)
		  assert(n, "String decoding failed: bad Unicode escape " .. a .. " at position " .. i .. " : " .. j)
		  -- math.floor(x/2^y) == lazy right shift
		  -- a % 2^b == bitwise_and(a, (2^b)-1)
		  -- 64 = 2^6
		  -- 4096 = 2^12 (or 2^6 * 2^6)
		  local x
		  if n < 0x80 then
			x = string.char(n % 0x80)
		  elseif n < 0x800 then
			-- [110x xxxx] [10xx xxxx]
			x = string.char(0xC0 + (math.floor(n/64) % 0x20), 0x80 + (n % 0x40))
		  else
			-- [1110 xxxx] [10xx xxxx] [10xx xxxx]
			x = string.char(0xE0 + (math.floor(n/4096) % 0x10), 0x80 + (math.floor(n/64) % 0x40), 0x80 + (n % 0x40))
		  end
		  table.insert(t, x)
		else
		  table.insert(t, escapeSequences[string.sub(s, i, j)])
		end
	  end
	  table.insert(t,string.sub(j, j+1))
	  assert(string.find(s, startChar, j+1), "String decoding failed: missing closing " .. startChar .. " at position " .. j .. "(for string at position " .. startPos .. ")")
	  return table.concat(t,""), j+2
	  -- END SoniEx2
	end

	--- Scans a JSON string skipping all whitespace from the current start position.
	-- Returns the position of the first non-whitespace character, or nil if the whole end of string is reached.
	-- @param s The string being scanned
	-- @param startPos The starting position where we should begin removing whitespace.
	-- @return int The first position where non-whitespace was encountered, or string.len(s)+1 if the end of string
	-- was reached.
	function decode_scanWhitespace(s,startPos)
	  local whitespace=" \n\r\t"
	  local stringLen = string.len(s)
	  while ( string.find(whitespace, string.sub(s,startPos,startPos), 1, true)  and startPos <= stringLen) do
		startPos = startPos + 1
	  end
	  return startPos
	end

	--- Encodes a string to be JSON-compatible.
	-- This just involves back-quoting inverted commas, back-quotes and newlines, I think ;-)
	-- @param s The string to return as a JSON encoded (i.e. backquoted string)
	-- @return The string appropriately escaped.

	local escapeList = {
		['"']  = '\\"',
		['\\'] = '\\\\',
		['/']  = '\\/',
		['\b'] = '\\b',
		['\f'] = '\\f',
		['\n'] = '\\n',
		['\r'] = '\\r',
		['\t'] = '\\t'
	}

	function json_private.encodeString(s)
	 local s = tostring(s)
	 return s:gsub(".", function(c) return escapeList[c] end) -- SoniEx2: 5.0 compat
	end

	-- Determines whether the given Lua type is an array or a table / dictionary.
	-- We consider any table an array if it has indexes 1..n for its n items, and no
	-- other data in the table.
	-- I think this method is currently a little 'flaky', but can't think of a good way around it yet...
	-- @param t The table to evaluate as an array
	-- @return boolean, number True if the table can be represented as an array, false otherwise. If true,
	-- the second returned value is the maximum
	-- number of indexed elements in the array.
	function isArray(t)
	  -- Next we count all the elements, ensuring that any non-indexed elements are not-encodable
	  -- (with the possible exception of 'n')
	  if (t == json.EMPTY_ARRAY) then return true, 0 end
	  if (t == json.EMPTY_OBJECT) then return false end

	  local maxIndex = 0
	  for k,v in pairs(t) do
		if (type(k)=='number' and math.floor(k)==k and 1<=k) then	-- k,v is an indexed pair
		  if (not isEncodable(v)) then return false end	-- All array elements must be encodable
		  maxIndex = math.max(maxIndex,k)
		else
		  if (k=='n') then
			if v ~= (t.n or #t) then return false end  -- False if n does not hold the number of elements
		  else -- Else of (k=='n')
			if isEncodable(v) then return false end
		  end  -- End of (k~='n')
		end -- End of k,v not an indexed pair
	  end  -- End of loop across all pairs
	  return true, maxIndex
	end

	--- Determines whether the given Lua object / table / variable can be JSON encoded. The only
	-- types that are JSON encodable are: string, boolean, number, nil, table and json.null.
	-- In this implementation, all other types are ignored.
	-- @param o The object to examine.
	-- @return boolean True if the object should be JSON encoded, false if it should be ignored.
	function isEncodable(o)
	  local t = type(o)
	  return (t=='string' or t=='boolean' or t=='number' or t=='nil' or t=='table') or
		 (t=='function' and o==json.null)
	end

	json.rpc = {}     -- Module public namespace

	-----------------------------------------------------------------------------
	-- Imports and dependencies
	-----------------------------------------------------------------------------


	-----------------------------------------------------------------------------
	-- PUBLIC functions
	-----------------------------------------------------------------------------

	--- Creates an RPC Proxy object for the given Url of a JSON-RPC server.
	-- @param url The URL for the JSON RPC Server.
	-- @return Object on which JSON-RPC remote methods can be called.
	-- EXAMPLE Usage:
	--   local jsolait = json.rpc.proxy('http://jsolait.net/testj.py')
	--   print(jsolait.echo('This is a test of the echo method!'))
	--   print(jsolait.args2String('first','second','third'))
	--   table.foreachi( jsolait.args2Array(5,4,3,2,1), print)
	function json.rpc.proxy(url)
	  local serverProxy = {}
	  local proxyMeta = {
		__index = function(self, key)
		  return function(...)
			return json.rpc.call(url, key, ...)
		  end
		end
	  }
	  setmetatable(serverProxy, proxyMeta)
	  return serverProxy
	end

	--- Calls a JSON RPC method on a remote server.
	-- Returns a boolean true if the call succeeded, false otherwise.
	-- On success, the second returned parameter is the decoded
	-- JSON object from the server.
	-- On http failure, returns nil and an error message.
	-- On success, returns the result and nil.
	-- @param url The url of the JSON RPC server.
	-- @param method The method being called.
	-- @param ... Parameters to pass to the method.
	-- @return result, error The JSON RPC result and error. One or the other should be nil. If both
	-- are nil, this means that the result of the RPC call was nil.
	-- EXAMPLE Usage:
	--   print(json.rpc.call('http://jsolait.net/testj.py','echo','This string will be returned'))
	function json.rpc.call(url, method, ...)
	  local JSONRequestArray = {
		id=tostring(math.random()),
		["method"]=method,
		params = ...
	  }
	  local httpResponse, result , code
	  local jsonRequest = json.encode(JSONRequestArray)
	  -- We use the sophisticated http.request form (with ltn12 sources and sinks) so that
	  -- we can set the content-type to text/plain. While this shouldn't strictly-speaking be true,
	  -- it seems a good idea (Xavante won't work w/out a content-type header, although a patch
	  -- is needed to Xavante to make it work with text/plain)

	  local resultChunks = {}

	  httpResponse, code = http.request(
		{ ['url'] = url,
		  sink = ltn12.sink.table(resultChunks),
		  method = 'POST',
		  headers = { ['content-type']='application/json-rpc', ['content-length']=string.len(jsonRequest) },
		  source = ltn12.source.string(jsonRequest)
		}
	  )

	  --httpResponse, code = dync_httpfix.request(
	  --  { ['url'] = url,
	  --    sink = ltn12.sink.table(resultChunks),
	  --    method = 'POST',
	  --    headers = { ['content-type']='application/json-rpc', ['content-length']=string.len(jsonRequest) },
	  --    source = ltn12.source.string(jsonRequest)
	  --  }
	  -- )
	  httpResponse = table.concat(resultChunks)
	  -- Check the http response code
	  if (code~=200) then
		return nil, "HTTP ERROR: " .. code
	  end
	  -- And decode the httpResponse and check the JSON RPC result code
	  result = json.decode( httpResponse )
	  if result.result then
		return result.result, nil
	  else
		return nil, result.error
	  end
	end


	local live_units = {}
	local fly_commands = {}
	local delayed_routes = {}
	local scored_planes = {}
	server = json.rpc.proxy(dync_socket)



	-- Configurable parameters
	local center_randomness = 0.0
	local dispersion = 300.0
	local disable_roads = true
	
	unitTypes = {}
	unitTypes.navy = {}
	unitTypes.navy.blue = {
	  VINSON = "VINSON",
	  PERRY = "PERRY",
	  TICONDEROG = "TICONDEROG"
	}
	unitTypes.navy.red = {
	  ALBATROS = "ALBATROS",
	  KUZNECOW = "KUZNECOW",
	  MOLNIYA = "MOLNIYA",
	  MOSCOW = "MOSCOW",
	  NEUSTRASH = "NEUSTRASH",
	  PIOTR = "PIOTR",
	  REZKY = "REZKY"
	}
	unitTypes.navy.civil = {
	  ELNYA = "ELNYA",
	  Drycargo_ship2 = "Dry-cargo ship-2",
	  Drycargo_ship1 = "Dry-cargo ship-1",
	  ZWEZDNY = "ZWEZDNY"
	}
	unitTypes.navy.submarine = {
	  KILO = "KILO",
	  SOM = "SOM"
	}
	unitTypes.navy.speedboat = {
	  speedboat = "speedboat"
	}
	unitTypes.vehicles = {}
	unitTypes.vehicles.Howitzers = {
	  _2B11_mortar = "2B11 mortar",
	  SAU_Gvozdika = "SAU Gvozdika",
	  SAU_Msta = "SAU Msta",
	  SAU_Akatsia = "SAU Akatsia",
	  SAU_2C9 = "SAU 2-C9",
	  M109 = "M-109"
	}
	unitTypes.vehicles.IFV = {
	  AAV7 = "AAV7",
	  BMD1 = "BMD-1",
	  BMP1 = "BMP-1",
	  BMP2 = "BMP-2",
	  BMP3 = "BMP-3",
	  Boman = "Boman",
	  BRDM2 = "BRDM-2",
	  BTR80 = "BTR-80",
	  BTR_D = "BTR_D",
	  Bunker = "Bunker",
	  Cobra = "Cobra",
	  LAV25 = "LAV-25",
	  M1043_HMMWV_Armament = "M1043 HMMWV Armament",
	  M1045_HMMWV_TOW = "M1045 HMMWV TOW",
	  M1126_Stryker_ICV = "M1126 Stryker ICV",
	  M113 = "M-113",
	  M1134_Stryker_ATGM = "M1134 Stryker ATGM",
	  M2_Bradley = "M-2 Bradley",
	  Marder = "Marder",
	  MCV80 = "MCV-80",
	  MTLB = "MTLB",
	  Paratrooper_RPG16 = "Paratrooper RPG-16",
	  Paratrooper_AKS74 = "Paratrooper AKS-74",
	  Sandbox = "Sandbox",
	  Soldier_AK = "Soldier AK",
	  Infantry_AK = "Infantry AK",
	  Soldier_M249 = "Soldier M249",
	  Soldier_M4 = "Soldier M4",
	  Soldier_M4_GRG = "Soldier M4 GRG",
	  Soldier_RPG = "Soldier RPG",
	  TPZ = "TPZ"
	}
	unitTypes.vehicles.MLRS = {
	  GradURAL = "Grad-URAL",
	  Uragan_BM27 = "Uragan_BM-27",
	  Smerch = "Smerch",
	  MLRS = "MLRS"
	}
	unitTypes.vehicles.SAM = {
	  _2S6_Tunguska = "2S6 Tunguska",
	  Kub_2P25_ln = "Kub 2P25 ln",
	  _5p73_s125_ln = "5p73 s-125 ln",
	  S300PS_5P85C_ln = "S-300PS 5P85C ln",
	  S300PS_5P85D_ln = "S-300PS 5P85D ln",
	  SA11_Buk_LN_9A310M1 = "SA-11 Buk LN 9A310M1",
	  Osa_9A33_ln = "Osa 9A33 ln",
	  Tor_9A331 = "Tor 9A331",
	  Strela10M3 = "Strela-10M3",
	  Strela1_9P31 = "Strela-1 9P31",
	  SA11_Buk_CC_9S470M1 = "SA-11 Buk CC 9S470M1",
	  SA8_Osa_LD_9T217 = "SA-8 Osa LD 9T217",
	  Patriot_AMG = "Patriot AMG",
	  Patriot_ECS = "Patriot ECS",
	  Gepard = "Gepard",
	  Hawk_pcp = "Hawk pcp",
	  SA18_Igla_manpad = "SA-18 Igla manpad",
	  SA18_Igla_comm = "SA-18 Igla comm",
	  Igla_manpad_INS = "Igla manpad INS",
	  SA18_IglaS_manpad = "SA-18 Igla-S manpad",
	  SA18_IglaS_comm = "SA-18 Igla-S comm",
	  Vulcan = "Vulcan",
	  Hawk_ln = "Hawk ln",
	  M48_Chaparral = "M48 Chaparral",
	  M6_Linebacker = "M6 Linebacker",
	  Patriot_ln = "Patriot ln",
	  M1097_Avenger = "M1097 Avenger",
	  Patriot_EPP = "Patriot EPP",
	  Patriot_cp = "Patriot cp",
	  Roland_ADS = "Roland ADS",
	  S300PS_54K6_cp = "S-300PS 54K6 cp",
	  Stinger_manpad_GRG = "Stinger manpad GRG",
	  Stinger_manpad_dsr = "Stinger manpad dsr",
	  Stinger_comm_dsr = "Stinger comm dsr",
	  Stinger_manpad = "Stinger manpad",
	  Stinger_comm = "Stinger comm",
	  ZSU234_Shilka = "ZSU-23-4 Shilka",
	  ZU23_Emplacement_Closed = "ZU-23 Emplacement Closed",
	  ZU23_Emplacement = "ZU-23 Emplacement",
	  ZU23_Closed_Insurgent = "ZU-23 Closed Insurgent",
	  Ural375_ZU23_Insurgent = "Ural-375 ZU-23 Insurgent",
	  ZU23_Insurgent = "ZU-23 Insurgent",
	  Ural375_ZU23 = "Ural-375 ZU-23"
	}
	unitTypes.vehicles.radar = {
	  _1L13_EWR = "1L13 EWR",
	  Kub_1S91_str = "Kub 1S91 str",
	  S300PS_40B6M_tr = "S-300PS 40B6M tr",
	  S300PS_40B6MD_sr = "S-300PS 40B6MD sr",
	  _55G6_EWR = "55G6 EWR",
	  S300PS_64H6E_sr = "S-300PS 64H6E sr",
	  SA11_Buk_SR_9S18M1 = "SA-11 Buk SR 9S18M1",
	  Dog_Ear_radar = "Dog Ear radar",
	  Hawk_tr = "Hawk tr",
	  Hawk_sr = "Hawk sr",
	  Patriot_str = "Patriot str",
	  Hawk_cwar = "Hawk cwar",
	  p19_s125_sr = "p-19 s-125 sr",
	  Roland_Radar = "Roland Radar",
	  snr_s125_tr = "snr s-125 tr"
	}
	unitTypes.vehicles.Structures = {
	  house1arm = "house1arm",
	  house2arm = "house2arm",
	  outpost_road = "outpost_road",
	  outpost = "outpost",
	  houseA_arm = "houseA_arm"
	}
	unitTypes.vehicles.Tanks = {
	  Challenger2 = "Challenger2",
	  Leclerc = "Leclerc",
	  Leopard1A3 = "Leopard1A3",
	  Leopard2 = "Leopard-2",
	  M60 = "M-60",
	  M1128_Stryker_MGS = "M1128 Stryker MGS",
	  M1_Abrams = "M-1 Abrams",
	  T55 = "T-55",
	  T72B = "T-72B",
	  T80UD = "T-80UD",
	  T90 = "T-90"
	}
	unitTypes.vehicles.unarmed = {
	  Ural4320_APA5D = "Ural-4320 APA-5D",
	  ATMZ5 = "ATMZ-5",
	  ATZ10 = "ATZ-10",
	  GAZ3307 = "GAZ-3307",
	  GAZ3308 = "GAZ-3308",
	  GAZ66 = "GAZ-66",
	  M978_HEMTT_Tanker = "M978 HEMTT Tanker",
	  HEMTT_TFFT = "HEMTT TFFT",
	  IKARUS_Bus = "IKARUS Bus",
	  KAMAZ_Truck = "KAMAZ Truck",
	  LAZ_Bus = "LAZ Bus",
	  Hummer = "Hummer",
	  M_818 = "M 818",
	  MAZ6303 = "MAZ-6303",
	  Predator_GCS = "Predator GCS",
	  Predator_TrojanSpirit = "Predator TrojanSpirit",
	  Suidae = "Suidae",
	  Tigr_233036 = "Tigr_233036",
	  Trolley_bus = "Trolley bus",
	  UAZ469 = "UAZ-469",
	  Ural_ATsP6 = "Ural ATsP-6",
	  Ural375_PBU = "Ural-375 PBU",
	  Ural375 = "Ural-375",
	  Ural432031 = "Ural-4320-31",
	  Ural4320T = "Ural-4320T",
	  VAZ_Car = "VAZ Car",
	  ZiL131_APA80 = "ZiL-131 APA-80",
	  SKP11 = "SKP-11",
	  ZIL131_KUNG = "ZIL-131 KUNG",
	  ZIL4331 = "ZIL-4331"
	}




	function handle_event(event)
		env.info(string.format("Event code %d happened", event.id), false)
		if event.id == world.event.S_EVENT_MISSION_END then

			local param = {}
			param["positions"] = {}

			for k,v in pairs(live_units) do

				if string.find(v["unitname"], "__im__") or string.find(v["groupname"], "__im__") or string.find(v["groupname"], "__ig__") then
					-- Ignore
				else
					local unit = Unit.getByName(v["unitname"])

					if unit ~= nil then
						local pos = unit:getPoint()
						param["positions"][v["unitname"]] = string.format("%f,%f",pos.x, pos.z)
					else
						-- Somehow we didn't get EVENT_DEAD for this unit. We report it destroyed now.

						env.info("Reported destroyed unit at mission end: "..v["unitname"]..", group: "..v["groupname"], false)
						local result, error = server.unitdestroyed({v["unitname"], v["groupname"]})
					end
				end
			end

			local result, error = server.missionend({json.encode(param),})
			local resultobj = json.decode(result)

			if resultobj["code"] ~= "0" then
				env.info(string.format("Server error: %s", resultobj["error"]), true)
			else
				if resultobj["event"] == "end" then
					env.info(string.format("Campaign ended: %s", resultobj["result"]), true)
				end
			end
		elseif event.id == world.event.S_EVENT_DEAD or event.id == world.event.S_EVENT_PILOT_DEAD or
				event.id == world.event.S_EVENT_CRASH or event.id == world.event.S_EVENT_EJECTION then
				
			env.info(string.format("Some death event %d, where dead=%d, pilot_dead=%d, crash=%d, eject=%d", event.id, world.event.S_EVENT_DEAD, 
			world.event.S_EVENT_PILOT_DEAD, world.event.S_EVENT_CRASH, world.event.S_EVENT_EJECTION), false)			
			
			if event.initiator == nil then
				env.info("Event initiator was nil: ignore event", false)
				return
			end

			local name = event.initiator:getName()
			
			if scored_planes[name] ~= nil then
				env.info("Unit "..name.." already scored: Ignore further death events", false)
				return
			end
			
			-- Somewhat crudely handle object types that don't have groups. Make the apparent group name the unit name.
			local groupname = name
			local is_unit = false
			if Object.getCategory(event.initiator) == 1 then
				is_unit = true
				groupname = Unit.getGroup(event.initiator):getName()
			end

			if string.find(name, "__ig__") or string.find(groupname, "__ig__") then
				-- ig: ignore
				return
			end
			
			local already_scored = false
			
			-- __ig__ (Ignore) handled. Planes for any other tag are still scored, so we handle that here.
			
			if scored_planes[name] ~= nil then
				already_scored = true				
			elseif is_unit == true then
				local unit_table = mist.DBs.unitsByName[name]
				if unit_table["category"] == "plane" then
					local coalition_str
					local coalition_id = event.initiator:getCoalition()
					if coalition_id == coalition.side.RED then
						coalition_str = "red"
					elseif coalition_id == coalition.side.BLUE then
						coalition_str = "blue"
					else
						return
					end				
				
					env.info(string.format("Some plane died, of skill %s", unit_table["skill"]), false)
					scored_planes[name] = true
					
					if unit_table["skill"] ~= nil and (unit_table["skill"] == "Player" or unit_table["skill"] == "Client") then
						env.info(string.format("Player plane died"), false)
						if event.id == world.event.S_EVENT_EJECTION then							
							local result, error = server.changescore({"player_eject", coalition_str, name})
						else
							local result, error = server.changescore({"player_death", coalition_str, name})
						end
						already_scored = true
						
					elseif unit_table["skill"] ~= nil then
						env.info(string.format("A.I. plane died"), false)
						
						if event.id == world.event.S_EVENT_EJECTION then
							scored_planes[name] = true
							local result, error = server.changescore({"ai_eject", coalition_str, name})
						else
							local result, error = server.changescore({"ai_death", coalition_str, name})							
						end
						already_scored = true
					end					
				end
			end

			if string.find(name, "__im__") or string.find(groupname, "__im__") then
				-- im: immortal
				return
			end
			
			if string.find(name, "__mm__") or string.find(groupname, "__mm__") then
				-- mm: mapmarker
				return
			end
			
			if string.find(name, "__cm__") or string.find(groupname, "__cm__") then
				-- cm: cornermarker
				return
			end

			if string.find(name, "__su__") then
				-- su: support unit
				local coalition_id = event.initiator:getCoalition()

				if coalition_id == coalition.side.RED then
					local result, error = server.supportdestroyed({"red",})
					env.info("Reported red coalition support unit destroyed", false)
				elseif coalition_id == coalition.side.BLUE then
					local result, error = server.supportdestroyed({"blue",})
					env.info("Reported blue coalition support unit destroyed", false)				
				end
			elseif string.find(name, "__in__") then
				-- in: infantry

				-- Weep for the tragedy. Do absolutely nothing at all.

			else
				found_it = false

				for k,v in pairs(live_units) do
					if name == v["unitname"] then
						-- Somewhat crudely handle object types that don't have groups. Make the apparent group name the unit name.
						local groupname = name
						if Object.getCategory(event.initiator) == 1 then
							groupname = Unit.getGroup(event.initiator):getName()
						end
						local coalition_str
						local coalition_id = event.initiator:getCoalition()
						if coalition_id == coalition.side.RED then
							coalition_str = "red"
						elseif coalition_id == coalition.side.BLUE then
							coalition_str = "blue"
						else
							return
						end
						
						local result, error = server.unitdestroyed({name, groupname})
						env.info("Reported destroyed unit: "..name..", group: "..groupname, false)
						live_units[k] = nil
						found_it = true
						if already_scored == false then
							local result, error = server.changescore({"unit_destroyed", coalition_str, name})
						end
						break
					end
				end
				if found_it == false then
					env.info("Unit "..name.." was already reported destroyed in earlier event", false)
				end
			end
		elseif event.id == world.event.S_EVENT_TAKEOFF then

			local name = event.initiator:getName()
			-- Somewhat crudely handle object types that don't have groups. Make the apparent group name the unit name.
			local groupname = name
			if Object.getCategory(event.initiator) == 1 then
				groupname = Unit.getGroup(event.initiator):getName()
			end

			if string.find(name, "__ig__") or string.find(groupname, "__ig__") then
				-- ig: ignore
				return
			end

			env.info("Plane "..name.." took off", false)
			local coord = fly_commands[name]

			if coord ~= nil then
				env.info("Gave the pending orders to plane: "..name, false)
				planeGoCoord(event.initiator, coord.x, coord.y)
				fly_commands[name] = nil
			end
		end
	end

	function getunits()

		jsonobj = {}
		jsonobj["units"] = {}

		for k,v in pairs(mist.DBs.unitsByName) do
			jsonobj["units"][k] = {}
			jsonobj["units"][k]["category"] = v["category"]
			jsonobj["units"][k]["type"] = v["type"]
			jsonobj["units"][k]["group"] = v["groupName"]
			jsonobj["units"][k]["coalition"] = v["coalition"]
			jsonobj["units"][k]["pos"] = string.format("%f,%f", v["point"].x, v["point"].y)
		end

		units = jsonobj["units"]
		jsonobj["routes"] = {}
		jsonobj["goals"] = {}
		jsonobj["mapmarkers"] = {}
		jsonobj["cornermarkers"] = {}
		jsonobj["bullseye"] = {}
		
		if mist.DBs.missionData.bullseye.red ~= nil then
			jsonobj["bullseye"]["red"] = string.format("%f,%f", mist.DBs.missionData.bullseye.red.x, mist.DBs.missionData.bullseye.red.y)
		end
		
		if mist.DBs.missionData.bullseye.blue ~= nil then
			jsonobj["bullseye"]["blue"] = string.format("%f,%f", mist.DBs.missionData.bullseye.blue.x, mist.DBs.missionData.bullseye.blue.y)
		end
		
		mist.DBs.missionData.bullseye.red.x = env.mission.coalition.red.bullseye.x --should it be point.x?
			mist.DBs.missionData.bullseye.red.y = env.mission.coalition.red.bullseye.y
			mist.DBs.missionData.bullseye.blue.x = env.mission.coalition.blue.bullseye.x
			mist.DBs.missionData.bullseye.blue.y = env.mission.coalition.blue.bullseye.y

		for k,v in pairs(units) do

			if string.starts(k, "routemarker") or string.find(k, "__rom__") or string.find(v["group"], "__rom__") then

				local grp = Group.getByName(v["group"])
				local points = mist.getGroupPoints(grp:getID())

				if points ~= nil then

					local newroute = {}
					tkeys = {}

					for k2 in pairs(points) do
						table.insert(tkeys, k2)
					end
					table.sort(tkeys)

					for _, k2 in ipairs(tkeys) do
						table.insert(newroute, string.format("%f,%f", points[k2]["x"], points[k2]["y"]))
					end
					table.insert(jsonobj["routes"], newroute)
				end
				Unit.getByName(k):destroy()
				jsonobj["units"][k] = nil

			elseif string.starts(k, "roadmarker") or string.find(k, "__rdm__") or string.find(v["group"], "__rdm__") then

				Unit.getByName(k):destroy()
				jsonobj["units"][k] = nil
			
			elseif string.starts(k, "mapmarker") or string.find(k, "__mm__") or string.find(v["group"], "__mm__") then
			
				mapmarker = {}
				mapmarker["name"] = v["group"]
				mapmarker["pos"] = v["pos"]
				table.insert(jsonobj["mapmarkers"], mapmarker)
				
				if Unit.getByName(k) then
					Unit.getByName(k):destroy()
				elseif StaticObject.getByName(k) then					
					StaticObject.getByName(k):destroy()				
				end
				jsonobj["units"][k] = nil
				
			elseif string.find(k, "__cm__") or string.find(v["group"], "__cm__") then
			
				cornermarker = {}
				cornermarker["pos"] = v["pos"]
				table.insert(jsonobj["cornermarkers"], cornermarker)
				
				if Unit.getByName(k) then
					Unit.getByName(k):destroy()
				elseif StaticObject.getByName(k) then					
					StaticObject.getByName(k):destroy()				
				end
				jsonobj["units"][k] = nil

			elseif string.starts(k, "objective") or string.find(k, "__ob__") or string.find(v["group"], "__ob__") then

				local coalition_str = v["coalition"]
				local spl = string.split(v["pos"], ",")
				local x = spl[0]
				local y = spl[1]

				if (coalition_str == "red" or coalition_str == "blue") then

					-- Neutrals are ignored. They are simply deleted.
					jsonobj["goals"][coalition_str] = x..","..y
				end

				Unit.getByName(k):destroy()
				jsonobj["units"][k] = nil

			elseif string.find(k, "__ig__") or string.find(v["group"], "__ig__") then

				jsonobj["units"][k] = nil

			else

				table.insert(live_units, {unitname = k, groupname = v["group"]})
			end
		end
		local result, error = server.processjson({json.encode(jsonobj),})
		local resultobj = json.decode(result)

		if (resultobj["code"] ~= "0") then
			env.info(resultobj["error"], true)
			return
		end

		local destroyed = resultobj["destroyed"]

		for k,v in pairs(destroyed) do

			local unit = Unit.getByName(k)
			if unit ~= nil then
				unit:destroy()
			end
			for k2,v2 in pairs(live_units) do
				if v2["unitname"] == k then
					live_units[k2] = nil
					break
				end
			end
		end

		local groupspos = resultobj["groupspos"]
		local groupsdest = resultobj["groupsdest"]
		local supportpos = resultobj["supportpos"]
		local airdest = resultobj["airdest"]
		local supportnumred = tonumber(resultobj["supportnum"]["red"])
		local supportnumblue = tonumber(resultobj["supportnum"]["blue"])
		local infantrypos = resultobj["infantrypos"]
		local dyngroups = resultobj["dyngroups"]

		local splred = string.split(airdest["red"], ",")
		local xred = splred[0]
		local yred = splred[1]
		local vec2red = {x = tonumber(splred[0]), y = tonumber(splred[1])}
		local splblue = string.split(airdest["blue"], ",")
		local xblue = splblue[0]
		local yblue = splblue[1]
		local vec2blue = {x = tonumber(splblue[0]), y = tonumber(splblue[1])}
		local groundvec3 = nil
		env.info(string.format("Red air: %f,%f; blue air: %f,%f", vec2red.x, vec2red.y, vec2blue.x, vec2blue.y), false)

		for k,v in pairs(units) do
			if v["category"] == "plane" then

				if v["coalition"] == "red" then
					fly_commands[k] = vec2red

					-- Note: If the plane is a player, planeGoCoord will simply do nothing.
					-- If we push the task to the group AI controller at the very first second, it turns out that
					-- the AI gets confused and does random things. Apparently it needs to process the takeoff task
					-- first. That's why we schedule it after 10 seconds.
					--mist.scheduleFunction(planeGoCoord,{v["group"], vec2red.x, vec2red.y}, timer.getTime() + 10)
				elseif v["coalition"] == "blue" then
					fly_commands[k] = vec2blue
					--mist.scheduleFunction(planeGoCoord,{v["group"], vec2blue.x, vec2blue.y}, timer.getTime() + 10)
				end

			end
		end

		for k,v in pairs(groupspos) do

			local spl = string.split(v, ",")
			local x = spl[0]
			local y = spl[1]
			local vec2 = {x = tonumber(spl[0]), y = tonumber(spl[1])}
			groundvec3 = mist.utils.makeVec3GL (vec2)			
			mist.teleportToPoint ({point=groundvec3, gpName=k, action="teleport", disperse="disp", maxDisp=dispersion,
								   radius=center_randomness})
		end

		splred = string.split(supportpos["red"], ",")
		xred = splred[0]
		yred = splred[1]
		vec2red = {x = tonumber(splred[0]), y = tonumber(splred[1])}
		splblue = string.split(supportpos["blue"], ",")
		xblue = splblue[0]
		yblue = splblue[1]
		vec2blue = {x = tonumber(splblue[0]), y = tonumber(splblue[1])}

		local addedgroup = {country="USA", category="vehicle", groupName="support-blue __su__"}
		local addedunits = {}
		vec2blue = mist.getRandPointInCircle(vec2blue, center_randomness)

		for i = 1, supportnumblue do
			local vec2unit = mist.getRandPointInCircle(vec2blue, dispersion)
			table.insert(addedunits, {unitName = string.format("support-blue-%d", i), skill = "Excellent", type = "Hummer",
									  x = vec2unit.x, y = vec2unit.y})
		end
		addedgroup["units"] = addedunits
		mist.dynAdd(addedgroup)
		addedgroup = {country = "Russia", category = "vehicle", groupName = "support-red __su__"}
		addedunits = {}
		vec2red = mist.getRandPointInCircle(vec2red, center_randomness)
		for i = 1, supportnumred do
			local vec2unit = mist.getRandPointInCircle(vec2red, dispersion)
			table.insert(addedunits, {unitName = string.format("support-red-%d", i), skill = "Excellent", type = "Ural ATsP-6",
									  x = vec2unit.x, y = vec2unit.y})
		end
		addedgroup["units"] = addedunits
		mist.dynAdd(addedgroup)

		local infantryID = 1

		for k,v in pairs(infantrypos["red"]) do
			local num = tonumber(v["number"])
			local spl = string.split(v["pos"], ",")
			local x = spl[0]
			local y = spl[1]
			local vec2 = {x = tonumber(spl[0]), y = tonumber(spl[1])}
			local name = string.format("Infantry red %dX #%d (dyn) __in__", num, infantryID)

			local addedgroup = {country="Russia", category="vehicle", groupName=name,
								 units={{unitName=name, skill="Excellent", type="Infantry AK", x=vec2.x, y=vec2.y},}}

			mist.dynAdd(addedgroup)

			infantryID = infantryID + 1
		end

		infantryID = 1

		for k,v in pairs(infantrypos["blue"]) do
			local num = tonumber(v["number"])
			local spl = string.split(v["pos"], ",")
			local x = spl[0]
			local y = spl[1]
			local vec2 = {x = tonumber(spl[0]), y = tonumber(spl[1])}
			local name = string.format("Infantry blue %dX #%d (dyn) __in__", num, infantryID)

			local addedgroup = {country="USA", category="vehicle", groupName=name,
								 units={{unitName=name, skill="Excellent", type="Soldier M249", x=vec2.x, y=vec2.y},}}

			mist.dynAdd(addedgroup)

			infantryID = infantryID + 1
		end

		for k,v in pairs(dyngroups["red"]) do

			local addedunits = {}
			local groupCenter = nil

			for k2,v2 in pairs(v["units"]) do
				local spl = string.split(v2["pos"], ",")
				local x = spl[0]
				local y = spl[1]
				local vec2 = {x = tonumber(spl[0]), y = tonumber(spl[1])}

				if groupCenter == nil then
					groupCenter = mist.getRandPointInCircle(vec2, center_randomness)
				end

				vec2 = mist.getRandPointInCircle(groupCenter, dispersion)
				table.insert(addedunits, {unitName = v2["name"], skill = v2["skill"], type = v2["type"], x = vec2.x, y = vec2.y})
			end

			env.info("Found red dynamic unit to add: "..v["name"], false)
			local addedgroup = {country="Russia", category=v["category"], groupName=v["name"], units=addedunits}
			mist.dynAdd(addedgroup)
			groupCenter = nil
		end

		for k,v in pairs(dyngroups["blue"]) do

			local addedunits = {}
			local groupCenter = nil

			for k2,v2 in pairs(v["units"]) do
				local spl = string.split(v2["pos"], ",")
				local x = spl[0]
				local y = spl[1]
				local vec2 = {x = tonumber(spl[0]), y = tonumber(spl[1])}

				if groupCenter == nil then
					groupCenter = mist.getRandPointInCircle(vec2, center_randomness)
				end

				vec2 = mist.getRandPointInCircle(groupCenter, dispersion)
				table.insert(addedunits, {unitName = v2["name"], skill = v2["skill"], type = v2["type"], x = vec2.x, y = vec2.y})
			end

			env.info("Found blue dynamic unit to add: "..v["name"], false)
			local addedgroup = {country="USA", category=v["category"], groupName=v["name"], units=addedunits}
			mist.dynAdd(addedgroup)
			groupCenter = nil
		end

		for k,v in pairs(groupsdest) do
			env.info("Setting route for group "..k.." to: "..v, false)
			local spl = string.split(v, ",")
			local x = spl[0]
			local y = spl[1]
			local destvec2 = {x = tonumber(spl[0]), y = tonumber(spl[1])}
			groundvec3 = mist.utils.makeVec3GL (destvec2)
			local gpData = Group.getByName(k)			
			mist.groupToRandomPoint({group = gpData, point = groundvec3, radius = center_randomness, disableRoads = disable_roads})
		end

		return
	end


	function planeGoCoord(unit, x_coord, y_coord)
		local vec2 = {x = x_coord, y = y_coord}
		local comboTask = {
			id = 'ComboTask',
			params = {
				tasks = {
					[1] = {
						id = 'Orbit',
						params = {
							pattern = "Circle",
							point = vec2,
						},
					},
					--[[1] = {
						id = 'Bombing',
						params = {
							attackQty = 2,
							point = vec2,
						},
					},--]]
				},
			},
		}
		if type(unit) == 'string' then
			unit = Unit.getByName(unit)
		end
		if unit then
			local unitCon = unit:getController()

			if unitCon then
				unitCon:pushTask(comboTask)
				unitCon:setOption(AI.Option.Air.id.ROE, AI.Option.Air.val.ROE.WEAPON_FREE)

				unitCon:setOption(AI.Option.Air.id.REACTION_ON_THREAT,
								  AI.Option.Air.val.REACTION_ON_THREAT.ALLOW_ABORT_MISSION)
				return true
			end
		end
		return false
	end


	function dync_start(mission_env_)

		dync.mission_env = mission_env_
		server = json.rpc.proxy(dync.socket)
		log("Dync.socket: "..dync.socket)
		getunits()
		mist.addEventHandler(handle_event)

	end
	dync.start = dync_start

end
