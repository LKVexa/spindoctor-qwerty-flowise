#!/usr/bin/env python3
# SpinDoctor Qwerty 1.1.0 - Flowise set-up helper
# Copyright (C) 2026 RUSSELL PHILIP SMITHSON <russellsmithson77@outlook.com>
# SPDX-License-Identifier: GPL-3.0-or-later
# This program is free software: you can redistribute it and/or modify it under the terms of the GNU General
# Public License as published by the Free Software Foundation, either version 3 of the License, or (at your
# option) any later version. It is distributed WITHOUT ANY WARRANTY; see the LICENSE file for details.
"""Print the Flowise settings for THIS copy of the repo (absolute paths filled in). Changes nothing.

  python3 tools/flowise_setup.py                  # human-readable
  python3 tools/flowise_setup.py --python python  # Windows: the command Flowise should start (python3 | python | py)
  python3 tools/flowise_setup.py --json           # machine-readable

Prints: the environment lines for the Flowise server (.env or shell), the Custom MCP "MCP Server Config" JSON, and the Flowise
variables for the Custom Tool. Standard library only.
"""
import json, os, re, sys

ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
MCP = os.path.join(ROOT, "engine", "scripts", "spindoctor_mcp.py")
CLI = os.path.join(ROOT, "engine", "scripts", "spindoctor_cli.py")


def main():
    a = sys.argv[1:]
    py = a[a.index("--python") + 1] if "--python" in a else ("python" if os.name == "nt" else "python3")
    if py not in ("python3", "python", "py"):
        print("--python must be python3, python or py (Flowise allows only plain command names here)"); return 2
    warn = []
    if re.search(r"[;&|`$(){}\[\]<>]", MCP):
        warn.append("This folder path contains characters Flowise's Custom MCP check rejects ( ; & | ` $ ( ) { } [ ] < > ). "
                    "Move the repo to a plain path such as C:/spindoctor-qwerty-flowise or /opt/spindoctor-qwerty-flowise.")
    env = {"CUSTOM_MCP_PROTOCOL": "stdio", "CUSTOM_MCP_ALLOWED_COMMANDS": py, "CUSTOM_MCP_ALLOWED_ABSOLUTE_SCRIPT_PATHS": MCP,
           "CUSTOM_MCP_ALLOWED_ENV_VARS": "SPINDOCTOR_WORKSPACE", "TOOL_FUNCTION_BUILTIN_DEP": "child_process"}
    mcp = {"command": py, "args": [MCP]}
    variables = {"spindoctor_cli": CLI, "spindoctor_python": py, "spindoctor_workspace": "(optional) folder for reports"}
    if "--json" in a:
        print(json.dumps({"env": env, "customMcpConfig": mcp, "variables": variables, "warnings": warn}, indent=2)); return 0
    print("1) Flowise server environment (add to Flowise's .env or export before `npx flowise start`, then restart Flowise):\n")
    for k, v in env.items(): print("   %s=%s" % (k, v))
    print("\n   (TOOL_FUNCTION_BUILTIN_DEP is only needed for the Custom Tool. If you already list modules there, add child_process.)")
    print("   (Custom node only: also set SHOW_COMMUNITY_NODES=true, or Flowise hides nodes that name an author.)")
    print("\n2) Custom MCP node -> MCP Server Config (then click refresh on Available Actions and select all six):\n")
    print("   " + json.dumps(mcp))
    print('\n   Optional: add  "env": {"SPINDOCTOR_WORKSPACE": "/your/reports/folder"}  to choose where reports go.')
    print("\n3) Custom Tool only: Flowise variables (Variables page, type Static):\n")
    for k, v in variables.items(): print("   %s = %s" % (k, v))
    for w in warn: print("\nWARNING: " + w)
    return 0


if __name__ == "__main__":
    sys.exit(main())
