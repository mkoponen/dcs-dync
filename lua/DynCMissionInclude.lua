do
	if dync == nil then
		env.info(string.format("You need two extra lines in MissionScripting.lua in order to give DynC the rights it needs to use certain restricted Lua functions. If you have already added them and still see this, a recent DCS World update may have overwritten the file and you need to add them again.\n\nThe file is found in [Your game installation folder]\\Scripts\\MissionScripting.lua and the changes need to go anywhere before the line \"--Sanitize Mission Scripting environment\". Find the lines to add in README.md of the installation zip."), true)
	else
		dync.start(_G)
	end
end
