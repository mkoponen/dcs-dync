do
	if dync == nil then
		env.info(string.format("Your MissionScripting.lua has either reverted back to default in a DCS World software update, or it was never modified by the DynC installer in the first place. Please execute the update-missionscripting.bat file that you find in DynC Server installation directory. Alternatively, README.md contains instructions for modifying it manually."), true)
	else
		dync.start(_G)
	end
end
