# Changelog

## 1.1.0 - 2026-10-11

- Engine 1.1.0 at parity with the updated SpinDoctor 3.1.2: 1-298 logical qubits (59 per entangled factor), the `mcx7` gate,
  wide-register Born-Z sampling, `q.folder` with 3.1.2 semantics, CSV report copies and measurement-CSV fitting equations. All 241
  presets replayed. New tools `spindoctor_functions` (function table) and `spindoctor_test_theory` (theory testing from a file, pasted
  text or the chat, with TXT+JSON+PDF theory reports).
- **New: Custom MCP set-up** (the recommended route). Flowise's Custom MCP node starts the bundled MCP server over stdio and offers all
  six `spindoctor_*` tools to any agent. Flowise 3.1 refuses every stdio command until the operator allows it, so
  `tools/flowise_setup.py` prints the exact settings for your copy (`CUSTOM_MCP_PROTOCOL`, `CUSTOM_MCP_ALLOWED_COMMANDS`,
  `CUSTOM_MCP_ALLOWED_ABSOLUTE_SCRIPT_PATHS`, `CUSTOM_MCP_ALLOWED_ENV_VARS`) and the MCP Server Config JSON.
- **Custom Tool fixed.** 1.0 read `process.platform` and `process.env`, but Flowise sets `process` to undefined inside tool functions, so
  every call failed and returned an empty result. It now reads its settings only from Flowise variables and detects Windows from the
  path separator. It also used `spawnSync`, which froze the whole Flowise server for the length of a run; it now runs the engine
  asynchronously, with a timeout below Flowise's 300 s sandbox limit (variable `spindoctor_timeout_s`) and an output cap. New `folder`
  action, `spindoctor_workspace` variable, and the export file is renamed to Flowise's own pattern (`spindoctor_qwerty-CustomTool.json`).
- **Custom node fixed.** 1.0's base classes came only from `DynamicStructuredTool` (no `Tool`), so the node couldn't connect to an
  agent's Tools input. It also names an author, and Flowise hides such nodes unless `SHOW_COMMUNITY_NODES=true`, which wasn't
  documented. Now: `Tool` added to the base classes, node version 2, async engine call with timeout, `folder` action, optional tool name
  and timeout, set-up steps in the README. It compiles in strict mode against Flowise 3.1.4's types and loads in a real server.
- Tests: `tests/flowise_host_check.py` (static checks, and a real Flowise run: Custom MCP, Custom Tool and custom node in a Tool Agent
  chatflow driven by a local stand-in model), plus the shared end-to-end suite.
- License changed from MIT to GPL-3.0-or-later. Author RUSSELL PHILIP SMITHSON. README, NOTICE, COPYRIGHT and SPDX headers added.
  The repo root is now the package root (1.0 had everything in `spindoctor-qwerty/`).

## 1.0.0

- First release: Custom Tool (function + schema + export JSON) and a TypeScript custom node, both shelling out to the bundled engine.
