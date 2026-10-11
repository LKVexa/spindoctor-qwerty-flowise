# SpinDoctor Qwerty for Flowise

Run the **SpinDoctor 3.1.2 quantum-circuit simulator** from [Flowise](https://flowiseai.com) agents: `q.*` circuit scripts (1-298
logical qubits), the 241 built-in presets, folders of command files (`q.folder`), and theory tests from a file, pasted text or the
chat itself, each with TXT, PDF, JSON and CSV reports. The engine runs with Python on the Flowise server.

> **Honest limits.** SpinDoctor is a classical FP64 simulator. It is not a quantum computer, does not connect to quantum hardware,
> and gives no quantum speed-up or advantage. One entangled group is limited to 59 qubits and dense groups are limited by memory
> (2^n x 16 bytes). Registers wider than 29 qubits sample in basis Z only. Histograms are seeded Born samples.

Version 1.1.0 - engine 1.1.0 (SpinDoctor 3.1.2 parity) - tested with Flowise 3.1.4 - Python 3.8+, standard library only - no
network, no account, no keys.

## Three ways in

| Route | What you get | Needs |
|---|---|---|
| **Custom MCP** (recommended) | All 6 `spindoctor_*` tools, with their own schemas, in any agent | Flowise running where it can start Python (self-hosted, not Flowise Cloud) and 4 server settings |
| **Custom Tool** | One tool `spindoctor_qwerty` with an `action` field, imported from a JSON file | `TOOL_FUNCTION_BUILTIN_DEP=child_process` and 1 Flowise variable |
| **Custom node** | A "SpinDoctor Qwerty" node under Tools | A Flowise source checkout you build yourself, and `SHOW_COMMUNITY_NODES=true` |

All three run the same bundled engine in `engine/`. Pick one; you don't need all three.

## Repo layout

| Path | What it is |
|---|---|
| `engine/` | The SpinDoctor engine (`spindoctor/`), CLI and MCP launchers (`scripts/`), examples |
| `tools/flowise_setup.py` | Prints the Flowise settings for this copy, with absolute paths filled in. Changes nothing |
| `custom-tool/` | `spindoctor_qwerty-CustomTool.json` (import file), plus its function (`.function.js`) and input schema (`.schema.json`) |
| `node/SpinDoctorQwerty/` | TypeScript custom node and icon |
| `FUNCTIONS.md` | The full function table, with a runnable example for every command |
| `tests/` | Host check, shared end-to-end suite, local stand-in model, reference outputs |

## Set-up

Put this repo on the Flowise server (for example `git clone https://github.com/LKVexa/spindoctor-qwerty-flowise`) in a plain folder
path, then run:

```bash
python3 tools/flowise_setup.py            # Windows: python tools/flowise_setup.py --python python
```

It prints the settings below with your real paths. Requirements: Python 3.8 or newer on the Flowise server. No packages to install.

### Custom MCP (recommended)

1. Add these to Flowise's environment (its `.env` file, or export them before `npx flowise start`) and restart Flowise:

   ```
   CUSTOM_MCP_PROTOCOL=stdio
   CUSTOM_MCP_ALLOWED_COMMANDS=python3
   CUSTOM_MCP_ALLOWED_ABSOLUTE_SCRIPT_PATHS=/full/path/to/spindoctor-qwerty-flowise/engine/scripts/spindoctor_mcp.py
   CUSTOM_MCP_ALLOWED_ENV_VARS=SPINDOCTOR_WORKSPACE
   ```

   Flowise 3.1 refuses every stdio command until these are set: the command must be in the allowed list, the first argument must be
   exactly an allowed script path, and arguments may not contain shell characters (`;` `&` `|` `$` `(` `)` `{` `}` `[` `]` `<` `>` or backticks). So a folder such as
   `C:\Program Files (x86)\...` won't work; use a plain one. (The Flowise docs page still describes an older built-in allow-list;
   3.1.4's code uses these four settings.)
2. In an Agent or Tool Agent, add **Custom MCP** and paste the MCP Server Config:

   ```json
   {"command": "python3", "args": ["/full/path/to/spindoctor-qwerty-flowise/engine/scripts/spindoctor_mcp.py"]}
   ```

   Add `"env": {"SPINDOCTOR_WORKSPACE": "/your/reports/folder"}` to choose where reports go.
3. Click refresh on **Available Actions** and select all six.

### Custom Tool

1. Set `TOOL_FUNCTION_BUILTIN_DEP=child_process` on the Flowise server (if you already list modules there, add `child_process`) and
   restart Flowise.
2. **Variables** page: add a Static variable `spindoctor_cli` = the full path of `engine/scripts/spindoctor_cli.py`. Optional:
   `spindoctor_python` (`python3`, `python`, `py` or a full path), `spindoctor_workspace` (reports folder), `spindoctor_timeout_s`
   (default 280).
3. **Tools** page: Load `custom-tool/spindoctor_qwerty-CustomTool.json`, save, and add a **Custom Tool** node that selects it.

The tool takes `action` (`script`, `folder`, `preset`, `list`, `report`, `functions`, `theory`) and `input`. Flowise stops tool
functions after `SANDBOX_TIMEOUT` (300 s by default), so long runs are cut off; use the Custom MCP route for those. If
`E2B_APIKEY` is set, Flowise runs tool functions in a remote E2B sandbox that can't see your engine; the Custom Tool needs the local
sandbox.

### Custom node

Follow Flowise's [building a node](https://docs.flowiseai.com/contributing/building-node) guide: copy `node/SpinDoctorQwerty/` to
`packages/components/nodes/tools/SpinDoctorQwerty/` in a Flowise source checkout, build, and start Flowise with
`SHOW_COMMUNITY_NODES=true` (Flowise hides nodes that name an author unless this is set). Set **Engine CLI path** to the full path of
`engine/scripts/spindoctor_cli.py`. Optional inputs: Python executable, Workspace folder, Tool name, Timeout.

### Reports

Reports and state go to `~/spindoctor-workspace` on the Flowise server unless you set a workspace as above. Paths in your messages
must be paths **on the Flowise server**, because that's where the engine runs.

## SpinDoctor Qwerty - plugin tools

| Function | What it does | Command to type |
|---|---|---|
| Function table (spindoctor_functions) | Show this table in chat | Ask: "show the SpinDoctor functions" |
| Run a script (spindoctor_run_script) | Run any q.* lines above; returns results + TXT/JSON/CSV/PDF report paths | Ask: "run q.circuit new bell 2 / q.circuit add h 0 / ..." |
| Run a preset (spindoctor_run_preset) | Run qc-001..qc-241 with overrides | Ask: "run preset qc-067 with shots=64" |
| List presets (spindoctor_list_presets) | Search the 241 presets | Ask: "list presets about Grover" |
| Read a report (spindoctor_report) | List/read TXT reports (PDF/JSON paths alongside) | Ask: "show the newest SpinDoctor report" |
| Test a theory from a file (spindoctor_test_theory source=file) | Read a .txt/.md/.pdf/.py/.json/.csv/.q attachment, then hypothesis -> prediction -> q.* script -> run -> verdict + TXT/PDF theory report | Ask: "test the theory in C:/notes/theory.md" (the host must pass the file path/content) |
| Test a theory from text (spindoctor_test_theory source=text) | Same pipeline for pasted text | Ask: "test this theory: a Hadamard on \|0> gives 50/50" |
| Test the theory we discussed (spindoctor_test_theory source=chat) | The AI summarises the theory from the conversation (claims, assumptions, variables, prediction), you confirm, then it is tested; quoted excerpts go in the report under 'Source: chat history'. An exported chat transcript (.txt/.md/.json/.html) also works | Ask: "test the theory we discussed" or "test the theory in my exported chat C:/chats/conversation.json" |

Every command family is listed with a runnable example in **[FUNCTIONS.md](FUNCTIONS.md)** (the exact table the tool shows):
circuits (`q.circuit`, including 298-qubit wide registers and the `mcx7` gate), queries (`q.query`), the tranche register
(`q.tranche`), the procedural grid, presets and sequences, resource planning, math calculators, physics models, lessons, noise, error
correction, compilation, algorithms, inputs/folders/history (`q.input`, `q.folder`, `q.history`) and the cartridge commands.

## Theory testing

`spindoctor_test_theory` turns a claim into a test: hypothesis -> measurable prediction -> `q.*` script -> run -> compare -> a TXT +
JSON + PDF **theory test report** with the hypothesis, script, raw results, verdict (*supported*, *not supported* or *inconclusive*)
and limits.

- **From a file:** .txt, .md, .pdf, .py, .json, .csv or .q. In Flowise, give the file's absolute path on your computer (or paste the text).
- **From pasted text.**
- **From the chat history:** say *"test the theory we discussed"*. The model writes a short summary (claims, assumptions, variables,
  measurable prediction), shows it to you to confirm or correct, then passes it with optional quoted excerpts; the report records them
  under *Source: chat history*. Exported chat transcripts (.txt/.md/.json/.html from ChatGPT, Claude and others) also work.
- The plugin cannot read your conversation or attachments by itself: only the model sees them, and very long conversations may already
  be truncated by the context window.

Sample theory files and chat transcripts are in `engine/examples/theory/`. The two sample
PDFs are stored as text; run `python3 engine/examples/theory/make_sample_pdfs.py` to
recreate them.

## Folder ingestion (`q.folder`)

`q.folder run path="<folder>"` runs every supported file at the top level of a folder (.txt, .csv, .json, .qasm, .qasm2, .circuit,
.pdf) in ordinal name order: 1-128 supported files, at most 4 MiB per file, 1-128 commands per file and 4096 characters per command,
strict UTF-8. Other files (for example .md) are skipped and listed. The first failing file stops the job.


## Testing

| Test | Command |
|---|---|
| Static checks | `python3 tests/flowise_host_check.py` |
| Real Flowise | `python3 tests/flowise_host_check.py --flowise-dir DIR --node /path/to/node --add-node` |

`DIR` is a folder where `npm install flowise` was run. **Real host, scripted model:** the host check starts that Flowise on 127.0.0.1
with throwaway data folders and its own settings, creates a throwaway local admin in the empty database (Flowise requires one; no
FlowiseAI account), lists the Custom MCP actions, imports the Custom Tool, builds a Tool Agent chatflow (ChatOpenAI pointed at
`tests/stub_llm.py`, a local scripted stand-in model, Buffer Memory, Custom MCP, Custom Tool and the custom node) and runs a
prediction through Flowise's own agent. Then it stops only the Flowise it started and runs the shared end-to-end suite against the
MCP server. `--add-node` compiles the custom node with that install's TypeScript and copies it into that install, so use a
throwaway install. Results for 1.1.0 (Flowise 3.1.4 from npm, Linux, Python 3.13) are in [E2E_RESULTS.md](E2E_RESULTS.md). Not
tested: a real model choosing the tools, Agentflow V2 agents (the same Custom MCP and Custom Tool nodes are used there), the
Flowise UI by hand, Windows, macOS.

## Author and license

Author: **RUSSELL PHILIP SMITHSON** <russellsmithson77@outlook.com>

Copyright (C) 2026 RUSSELL PHILIP SMITHSON. Licensed under the GNU General Public License v3.0 or later (`GPL-3.0-or-later`): see
[LICENSE](LICENSE), [NOTICE](NOTICE) and [COPYRIGHT](COPYRIGHT). Flowise is a trademark of its owner; this project is not
affiliated with FlowiseAI.
