@echo off
setlocal
if not defined LOCALAPPDATA (
  echo AstraBlox Roblox MCP launcher: LOCALAPPDATA is not defined. 1>&2
  exit /b 2
)
if not exist "%LOCALAPPDATA%\Roblox\mcp.bat" (
  echo AstraBlox Roblox MCP launcher: mcp.bat was not found under LOCALAPPDATA. 1>&2
  exit /b 3
)
call "%LOCALAPPDATA%\Roblox\mcp.bat" %*
exit /b %ERRORLEVEL%
