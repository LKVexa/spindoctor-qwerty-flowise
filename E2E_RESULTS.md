# E2E results - spindoctor-qwerty-flowise 1.1.0

Host: **real Flowise 3.1.4** (npm package `flowise`, Node 24, Linux x64) started by the host check on 127.0.0.1 with throwaway data
folders and telemetry off. Flowise requires a local admin, so the check creates a throwaway one in the empty database (no FlowiseAI
account). Model turns come from `tests/stub_llm.py`, a local scripted stand-in that Flowise's ChatOpenAI node calls through its Base
Path, with a placeholder key, so tool calls are scripted; everything between the model and the engine (Tool Agent, Custom MCP client
and security checks, Custom Tool sandbox, Flowise variables, the compiled custom node) is the real Flowise. Python 3.13.5.

Not tested: a real model choosing the tools by itself, Agentflow V2 agents, clicking through the Flowise UI, Flowise Cloud,
Windows, macOS.

## Host check: 20/20

| Result | Check |
|---|---|
| PASS | Custom Tool export: name/description/color/iconSrc/schema/func; schema string = schema.json; func = function.js byte for byte |
| PASS | Custom Tool schema: action (required, 7 actions listed) + input (optional), Flowise schema rows |
| PASS | Custom Tool function: async spawn (no spawnSync blocking the Flowise server), no `process` (hidden by Flowise), timeout, output cap, $vars set-up message, no network |
| PASS | custom node source: INode with 'Tool' base class, version 2, author, SPDX header, async engine call with timeout |
| PASS | tools/flowise_setup.py: Custom MCP config passes Flowise 3.1 rules (allowed command, script path = args[0] in the allow-list, no shell characters, no cwd) |
| PASS | custom node compiles in strict mode against the installed Flowise types (flowise-components, @langchain/core, zod) |
| PASS | real Flowise 3.1.4 started on 127.0.0.1 (throwaway data folders, telemetry off) |
| PASS | throwaway local admin registered and signed in (empty local database; no FlowiseAI account) |
| PASS | Custom MCP (stdio, Flowise allow-lists): Flowise's MCP client lists the 6 spindoctor_* actions |
| PASS | Custom MCP security: a script path outside CUSTOM_MCP_ALLOWED_ABSOLUTE_SCRIPT_PATHS is refused (no actions) |
| PASS | Custom Tool imported from custom-tool/spindoctor_qwerty-CustomTool.json; credential + variables created |
| PASS | Tool Agent chatflow created (ChatOpenAI -> local stand-in, Buffer Memory, Custom MCP, Custom Tool, SpinDoctor Qwerty node) |
| PASS | custom node loaded by the real Flowise server: category Tools, base classes include Tool, version 2 |
| PASS | prediction through Flowise's Tool Agent: answer returned, 8 tool calls recorded |
| PASS | Custom MCP tools via Flowise: function table, Bell run (ok, PDF report), preset qc-001 (ok) |
| PASS | Custom MCP theory test from the chat: verdict supported, 2 excerpts recorded, theory PDF on disk |
| PASS | Custom Tool (NodeVM, child_process): function table (gates) and a GHZ script through the Flowise variables |
| PASS | custom node tool: preset qc-002 ok and preset list filtered by 'grover' |
| PASS | the model was offered exactly the expected tools (8) |
| PASS | shared E2E suite against the server Custom MCP starts (engine/scripts/spindoctor_mcp.py): SUMMARY 12/12 |

## Shared end-to-end suite against the Custom MCP server: 12/12

Started the same way Flowise's Custom MCP node starts it: `python3 engine/scripts/spindoctor_mcp.py`.

| Result | Check |
|---|---|
| PASS | initialize (server spindoctor-qwerty 1.1.0) |
| PASS | tools/list exposes the 6 tools |
| PASS | function table (Markdown, 19 sections, 298-qubit limits listed) |
| PASS | 241 presets listed |
| PASS | one script per command family (16 families, every table example) |
| PASS | 298-qubit circuit with mcx7 (prepared-factor-Born-Z) |
| PASS | q.folder on mixed .txt/.csv/.json/.qasm folder (+ .md skipped) |
| PASS | theory from a file -> supported, TXT+PDF report |
| PASS | theory from a chat summary + quoted excerpts -> supported |
| PASS | theory from an exported chat transcript -> supported |
| PASS | presets qc-001..qc-025 match the updated 3.1.2 reference (20 identical, 5 documented differences) |
| PASS | TXT+PDF reports valid (255 PDFs, 255 TXT twins) |

## Runs

- Clean room (fresh copy of the staged repo, 2026-10-11 PT): host check 20/20 (real Flowise 3.1.4, with --add-node), shared end-to-end 12/12.
