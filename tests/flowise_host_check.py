#!/usr/bin/env python3
"""Run from the repo root:

  python3 tests/flowise_host_check.py                                  # static checks only
  python3 tests/flowise_host_check.py --flowise-dir DIR [--node NODE] [--add-node] [--out tests/host_check.json]

Static: Custom Tool export (schema, function identical to custom-tool/*.js), custom node source, Custom MCP config generator.
Real host (with --flowise-dir = a folder where `npm install flowise` was run): starts that Flowise on 127.0.0.1 with throwaway data
folders and its own environment (the Custom MCP allow-lists and TOOL_FUNCTION_BUILTIN_DEP=child_process), creates a throwaway local
admin in that empty database (Flowise requires one; no FlowiseAI account, nothing leaves the machine), lists the Custom MCP actions,
creates a placeholder OpenAI credential, the Flowise variables and the Custom Tool, builds a Tool Agent chatflow whose ChatOpenAI node
points at tests/stub_llm.py (a local scripted stand-in model on 127.0.0.1), runs predictions through Flowise's own agent, then
stops only the Flowise process it started. --add-node also compiles node/SpinDoctorQwerty with the TypeScript compiler that ships with
that Flowise install and copies the result into that install's flowise-components/dist/nodes/tools/SpinDoctorQwerty/, so the
custom node loads in the real server too (this changes that Flowise install; use a throwaway one).
Standard library only (Python 3.8+).
"""
import http.cookiejar, json, os, re, shutil, signal, socket, subprocess, sys, tempfile, time, urllib.request
sys.dont_write_bytecode = True
HERE = os.path.dirname(os.path.abspath(__file__)); ROOT = os.path.dirname(HERE)
ENGINE = os.path.join(ROOT, "engine"); CLI = os.path.join(ENGINE, "scripts", "spindoctor_cli.py"); MCP = os.path.join(ENGINE, "scripts", "spindoctor_mcp.py")
R = []
OK = lambda s: bool(re.search(r'"ok":\s*true', s or ''))
TOOLS = ["spindoctor_functions", "spindoctor_list_presets", "spindoctor_report", "spindoctor_run_preset", "spindoctor_run_script", "spindoctor_test_theory"]


def T(name, ok, detail=""):
    R.append({"check": name, "pass": bool(ok), "detail": str(detail)[:600]})
    print(("PASS " if ok else "FAIL ") + name + ("" if ok else "  -- " + str(detail)[:500])); sys.stdout.flush()


def static():
    ct = os.path.join(ROOT, "custom-tool"); exp = json.load(open(os.path.join(ct, "spindoctor_qwerty-CustomTool.json"), encoding="utf-8"))
    func = open(os.path.join(ct, "spindoctor_qwerty.function.js"), encoding="utf-8").read()
    sch = json.load(open(os.path.join(ct, "spindoctor_qwerty.schema.json"), encoding="utf-8"))
    T("Custom Tool export: name/description/color/iconSrc/schema/func; schema string = schema.json; func = function.js byte for byte",
      set(exp) == {"name", "description", "color", "iconSrc", "schema", "func"} and re.fullmatch(r"[a-z0-9_-]+", exp["name"])
      and json.loads(exp["schema"]) == sch and exp["func"] == func, sorted(exp))
    T("Custom Tool schema: action (required, 7 actions listed) + input (optional), Flowise schema rows",
      [r["property"] for r in sch] == ["action", "input"] and sch[0]["required"] is True and sch[1]["required"] is False
      and all(a in sch[0]["description"] for a in ("script", "folder", "preset", "list", "report", "functions", "theory")), sch)
    T("Custom Tool function: async spawn (no spawnSync blocking the Flowise server), no `process` (hidden by Flowise), timeout, output cap, $vars set-up message, no network",
      "spawnSync" not in func and "spawn(" in func and "setTimeout" in func and "truncated" in func and "spindoctor_cli" in func
      and "process." not in func and not re.search(r"require\(.(https?|net|node-fetch|axios).\)", func))
    ts = open(os.path.join(ROOT, "node", "SpinDoctorQwerty", "SpinDoctorQwerty.ts"), encoding="utf-8").read()
    T("custom node source: INode with 'Tool' base class, version 2, author, SPDX header, async engine call with timeout",
      "implements INode" in ts and "[this.type, 'Tool'," in ts and "this.version = 2.0" in ts and "RUSSELL PHILIP SMITHSON" in ts
      and "SPDX-License-Identifier: GPL-3.0-or-later" in ts and "spawnSync" not in ts and "setTimeout" in ts)
    out = subprocess.run([sys.executable, os.path.join(ROOT, "tools", "flowise_setup.py"), "--json"], stdout=subprocess.PIPE, stderr=subprocess.PIPE)
    try: cfg = json.loads(out.stdout)
    except Exception: cfg = {}
    m = cfg.get("customMcpConfig", {}); env = cfg.get("env", {})
    T("tools/flowise_setup.py: Custom MCP config passes Flowise 3.1 rules (allowed command, script path = args[0] in the allow-list, no shell characters, no cwd)",
      m.get("command") in ("python3", "python", "py") and m.get("args") == [MCP] and env.get("CUSTOM_MCP_ALLOWED_ABSOLUTE_SCRIPT_PATHS") == MCP
      and env.get("CUSTOM_MCP_PROTOCOL") == "stdio" and m["command"] in env.get("CUSTOM_MCP_ALLOWED_COMMANDS", "").split(",") and "cwd" not in m
      and not re.search(r"[;&|`$(){}\[\]<>]", MCP), cfg)


class Flowise:
    def __init__(self, base): self.base = base; self.cj = http.cookiejar.CookieJar(); self.op = urllib.request.build_opener(urllib.request.HTTPCookieProcessor(self.cj))

    def req(self, method, path, body=None, timeout=600):
        data = json.dumps(body).encode() if body is not None else None
        r = urllib.request.Request(self.base + path, data=data, method=method, headers={"Content-Type": "application/json", "x-request-from": "internal"})
        try:
            with self.op.open(r, timeout=timeout) as f: t = f.read().decode("utf-8", "replace")
        except urllib.error.HTTPError as e:
            t = e.read().decode("utf-8", "replace")
        try: return json.loads(t)
        except Exception: return t


def free_port():
    s = socket.socket(); s.bind(("127.0.0.1", 0)); p = s.getsockname()[1]; s.close(); return p


def compile_node(fdir, node):
    nm = os.path.join(fdir, "node_modules"); comp = os.path.join(nm, "flowise-components", "dist")
    tmp = tempfile.mkdtemp(prefix="sdq-ts-"); d = os.path.join(tmp, "nodes", "tools", "SpinDoctorQwerty"); os.makedirs(d)
    os.symlink(os.path.join(comp, "src"), os.path.join(tmp, "src")); os.symlink(nm, os.path.join(tmp, "node_modules"))
    shutil.copy(os.path.join(ROOT, "node", "SpinDoctorQwerty", "SpinDoctorQwerty.ts"), d)
    json.dump({"compilerOptions": {"target": "ES2020", "module": "commonjs", "moduleResolution": "node", "strict": True, "esModuleInterop": True,
               "skipLibCheck": True, "outDir": ".", "rootDir": "."}, "files": ["nodes/tools/SpinDoctorQwerty/SpinDoctorQwerty.ts"]}, open(os.path.join(tmp, "tsconfig.json"), "w"))
    r = subprocess.run([node, os.path.join(nm, "typescript", "bin", "tsc"), "-p", "tsconfig.json"], cwd=tmp, stdout=subprocess.PIPE, stderr=subprocess.STDOUT)
    js = os.path.join(d, "SpinDoctorQwerty.js"); ok = r.returncode == 0 and os.path.isfile(js)
    T("custom node compiles in strict mode against the installed Flowise types (flowise-components, @langchain/core, zod)", ok, r.stdout.decode()[-500:])
    if ok:
        dst = os.path.join(comp, "nodes", "tools", "SpinDoctorQwerty"); os.makedirs(dst, exist_ok=True)
        shutil.copy(js, dst); shutil.copy(os.path.join(ROOT, "node", "SpinDoctorQwerty", "spindoctor.svg"), dst)
    shutil.rmtree(tmp, ignore_errors=True); return ok


def build_node(fw, nid, name, inputs, x, credential=None):
    d = fw.req("GET", "/api/v1/nodes/" + name)
    prim = {"string", "number", "boolean", "password", "json", "code", "date", "file", "folder", "options", "multiOptions", "asyncOptions", "asyncMultiOptions", "datagrid", "tabs"}
    ins = {i["name"]: i.get("default", "") for i in d.get("inputs", [])}; ins.update(inputs)
    anchors = [dict(i, id="%s-input-%s-%s" % (nid, i["name"], i["type"])) for i in d.get("inputs", []) if i["type"] not in prim]
    params = [dict(i, id="%s-input-%s-%s" % (nid, i["name"], i["type"])) for i in d.get("inputs", []) if i["type"] in prim]
    bc = "|".join(d["baseClasses"])
    data = dict(d, id=nid, inputs=ins, outputs={}, inputAnchors=anchors, inputParams=params, selected=False,
                outputAnchors=[{"id": "%s-output-%s-%s" % (nid, d["name"], bc), "name": d["name"], "label": d["label"], "type": bc}])
    if credential: data["credential"] = credential; ins["FLOWISE_CREDENTIAL_ID"] = credential
    return {"id": nid, "type": "customNode", "position": {"x": x, "y": 100}, "positionAbsolute": {"x": x, "y": 100}, "width": 300, "height": 500, "data": data}


def edge(src, tgt, inp, typ):
    sh = "%s-output-%s-%s" % (src["id"], src["data"]["name"], "|".join(src["data"]["baseClasses"]))
    th = "%s-input-%s-%s" % (tgt["id"], inp, typ)
    return {"source": src["id"], "sourceHandle": sh, "target": tgt["id"], "targetHandle": th, "type": "buttonedge", "id": sh + "-" + th}


def real(fdir, node, add_node):
    if add_node and not compile_node(fdir, node): return
    tmp = tempfile.mkdtemp(prefix="sdq-flowise-"); port = free_port(); ws = os.path.join(tmp, "ws")
    for d in ("db", "keys", "storage", "logs", "home"): os.makedirs(os.path.join(tmp, d))
    py = "python3"
    env = {k: v for k, v in os.environ.items() if not k.startswith(("CUSTOM_MCP", "TOOL_FUNCTION", "SPINDOCTOR", "E2B"))}
    env.update(HOME=os.path.join(tmp, "home"), PORT=str(port), HOST="127.0.0.1", DATABASE_PATH=os.path.join(tmp, "db"), SECRETKEY_PATH=os.path.join(tmp, "keys"),
               BLOB_STORAGE_PATH=os.path.join(tmp, "storage"), LOG_PATH=os.path.join(tmp, "logs"), DISABLE_FLOWISE_TELEMETRY="true",
               TOOL_FUNCTION_BUILTIN_DEP="child_process", CUSTOM_MCP_PROTOCOL="stdio", CUSTOM_MCP_ALLOWED_COMMANDS=py,
               CUSTOM_MCP_ALLOWED_ABSOLUTE_SCRIPT_PATHS=MCP, CUSTOM_MCP_ALLOWED_ENV_VARS="SPINDOCTOR_WORKSPACE", SHOW_COMMUNITY_NODES="true" if add_node else "false",
               PATH=os.path.dirname(node) + os.pathsep + os.environ.get("PATH", ""))
    log = open(os.path.join(tmp, "server.log"), "w")
    srv = subprocess.Popen([node, os.path.join(fdir, "node_modules", "flowise", "bin", "run"), "start"], cwd=fdir, env=env, stdout=log, stderr=subprocess.STDOUT, start_new_session=True)
    stub = None
    try:
        fw = Flowise("http://127.0.0.1:%d" % port); t0 = time.time(); up = False
        while time.time() - t0 < 240 and srv.poll() is None:
            try:
                if fw.req("GET", "/api/v1/ping", timeout=5) == "pong": up = True; break
            except Exception: pass
            time.sleep(2)
        ver = fw.req("GET", "/api/v1/version") if up else {}
        T("real Flowise %s started on 127.0.0.1 (throwaway data folders, telemetry off)" % (ver.get("version", "?") if isinstance(ver, dict) else "?"), up, open(os.path.join(tmp, "server.log")).read()[-500:])
        if not up: return
        pw = "Local-%d-Test#" % port
        reg = fw.req("POST", "/api/v1/account/register", {"user": {"name": "Local Test Admin", "email": "admin@example.test", "credential": pw}})
        lg = fw.req("POST", "/api/v1/auth/login", {"email": "admin@example.test", "password": pw})
        T("throwaway local admin registered and signed in (empty local database; no FlowiseAI account)", isinstance(lg, dict) and lg.get("email") == "admin@example.test", [reg, lg])
        cfg = json.dumps({"command": py, "args": [MCP], "env": {"SPINDOCTOR_WORKSPACE": ws}})
        acts = fw.req("POST", "/api/v1/node-load-method/customMCP", {"loadMethod": "listActions", "inputs": {"mcpServerConfig": cfg}})
        names = sorted(a.get("name") for a in acts) if isinstance(acts, list) else []
        T("Custom MCP (stdio, Flowise allow-lists): Flowise's MCP client lists the 6 spindoctor_* actions", names == TOOLS, acts)
        bad = fw.req("POST", "/api/v1/node-load-method/customMCP", {"loadMethod": "listActions", "inputs": {"mcpServerConfig": json.dumps({"command": py, "args": [CLI]})}})
        T("Custom MCP security: a script path outside CUSTOM_MCP_ALLOWED_ABSOLUTE_SCRIPT_PATHS is refused (no actions)",
          not any(str(x.get("name", "")).startswith("spindoctor_") for x in (bad if isinstance(bad, list) else [])), str(bad)[:300])
        cred = fw.req("POST", "/api/v1/credentials", {"name": "local stand-in (no key)", "credentialName": "openAIApi", "plainDataObj": {"openAIApiKey": "local-stub"}})
        for k, v in (("spindoctor_cli", CLI), ("spindoctor_workspace", ws)):
            fw.req("POST", "/api/v1/variables", {"name": k, "value": v, "type": "static"})
        exp = json.load(open(os.path.join(ROOT, "custom-tool", "spindoctor_qwerty-CustomTool.json"), encoding="utf-8"))
        tool = fw.req("POST", "/api/v1/tools", exp)
        T("Custom Tool imported from custom-tool/spindoctor_qwerty-CustomTool.json; credential + variables created",
          isinstance(tool, dict) and tool.get("id") and isinstance(cred, dict) and cred.get("id"), [str(tool)[:200], str(cred)[:200]])
        sport = free_port(); slog = os.path.join(tmp, "stub.jsonl"); sscript = os.path.join(tmp, "script.json")
        P = lambda x: {"kind": "probability", "outcome": x, "expected": 0.5, "tolerance": 0.05}
        steps = [{"tool": "spindoctor_functions", "args": {}},
                 {"tool": "spindoctor_run_script", "args": {"script": "q.circuit new bell 2\nq.circuit add h 0\nq.circuit add cx 0 1\nq.circuit run shots 1000 basis z"}},
                 {"tool": "spindoctor_run_preset", "args": {"preset_id": "qc-001"}},
                 {"tool": "spindoctor_test_theory", "args": {"source": "chat", "text": "Theory: H then CX makes a Bell state; only 00 and 11, about half each.",
                  "excerpts": ["User: does H then CX entangle two qubits?", "Assistant: yes, a Bell state."], "hypothesis": "H(0) then CX(0,1) prepares a Bell state",
                  "prediction": "P(00)=P(11)=0.5", "script": "q.circuit new th 2\nq.circuit add h 0\nq.circuit add cx 0 1\nq.circuit run shots 4000 basis z", "checks": [P("00"), P("11")]}},
                 {"tool": "spindoctor_qwerty", "args": {"action": "functions", "input": "gates"}},
                 {"tool": "spindoctor_qwerty", "args": {"action": "script", "input": "q.circuit new g 3\nq.circuit add h 0\nq.circuit add cx 0 1\nq.circuit add cx 1 2\nq.circuit run shots 500 basis z"}}]
        if add_node:
            steps += [{"tool": "spindoctor_node", "args": {"action": "preset", "input": "qc-002"}}, {"tool": "spindoctor_node", "args": {"action": "list", "input": "grover"}}]
        steps += [{"text": "Done. SpinDoctor is a classical simulation, not quantum hardware."}]
        json.dump(steps, open(sscript, "w"))
        stub = subprocess.Popen([sys.executable, os.path.join(HERE, "stub_llm.py"), str(sport), slog, sscript], stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
        time.sleep(1)
        llm = build_node(fw, "chatOpenAI_0", "chatOpenAI", {"modelName": "gpt-4o-mini", "temperature": 0, "streaming": False, "basepath": "http://127.0.0.1:%d/v1" % sport}, 0, cred.get("id"))
        mem = build_node(fw, "bufferMemory_0", "bufferMemory", {}, 350)
        mcp = build_node(fw, "customMCP_0", "customMCP", {"mcpServerConfig": cfg, "mcpActions": json.dumps(TOOLS)}, 700)
        ctool = build_node(fw, "customTool_0", "customTool", {"selectedTool": tool.get("id"), "returnDirect": False}, 1050)
        nodes = [llm, mem, mcp, ctool]; tool_nodes = [mcp, ctool]
        if add_node:
            sn = build_node(fw, "spinDoctorQwerty_0", "spinDoctorQwerty", {"enginePath": CLI, "workspace": ws, "toolName": "spindoctor_node"}, 1400)
            nodes.append(sn); tool_nodes.append(sn)
        agent = build_node(fw, "toolAgent_0", "toolAgent", {"model": "{{chatOpenAI_0.data.instance}}", "memory": "{{bufferMemory_0.data.instance}}",
                           "tools": ["{{%s.data.instance}}" % n["id"] for n in tool_nodes], "maxIterations": 20,
                           "systemMessage": "You run the SpinDoctor simulator. It is a classical simulation, not quantum hardware."}, 1800)
        nodes.append(agent)
        edges = [edge(llm, agent, "model", "BaseChatModel"), edge(mem, agent, "memory", "BaseChatMemory")] + [edge(n, agent, "tools", "Tool") for n in tool_nodes]
        cf = fw.req("POST", "/api/v1/chatflows", {"name": "SpinDoctor Qwerty host check", "deployed": False, "isPublic": False, "type": "CHATFLOW",
                                                  "flowData": json.dumps({"nodes": nodes, "edges": edges, "viewport": {"x": 0, "y": 0, "zoom": 1}})})
        T("Tool Agent chatflow created (ChatOpenAI -> local stand-in, Buffer Memory, Custom MCP, Custom Tool%s)" % (", SpinDoctor Qwerty node" if add_node else ""),
          isinstance(cf, dict) and cf.get("id"), str(cf)[:300])
        if add_node:
            nd = fw.req("GET", "/api/v1/nodes/spinDoctorQwerty")
            T("custom node loaded by the real Flowise server: category Tools, base classes include Tool, version 2",
              isinstance(nd, dict) and nd.get("category") == "Tools" and "Tool" in nd.get("baseClasses", []) and nd.get("version") == 2, str(nd)[:300])
        pr = fw.req("POST", "/api/v1/prediction/" + cf["id"], {"question": "Show the SpinDoctor functions, run a Bell circuit and preset qc-001, test the Bell theory we discussed.", "streaming": False}, timeout=900)
        used = pr.get("usedTools", []) if isinstance(pr, dict) else []
        out = {}
        def norm(v):  # MCP tool output arrives as a JSON list of content parts
            try:
                j = json.loads(v) if isinstance(v, str) else v
                if isinstance(j, list) and all(isinstance(x, dict) and "text" in x for x in j): return "".join(x["text"] for x in j)
            except Exception: pass
            return v if isinstance(v, str) else json.dumps(v)
        for u in used: out.setdefault(u.get("tool"), []).append(norm(u.get("toolOutput", "")))
        print("INFO used tools:", [(u.get("tool"), str(u.get("toolOutput", ""))[:80]) for u in used])
        g = lambda n, i=0: out.get(n, [""] * (i + 1))[i] if len(out.get(n, [])) > i else ""
        T("prediction through Flowise's Tool Agent: answer returned, %d tool calls recorded" % len(used),
          isinstance(pr, dict) and "classical simulation" in str(pr.get("text", "")) and len(used) == len(steps) - 1, str(pr)[:400])
        T("Custom MCP tools via Flowise: function table, Bell run (ok, PDF report), preset qc-001 (ok)",
          "| Function |" in g("spindoctor_functions") and OK(g("spindoctor_run_script")) and ".pdf" in g("spindoctor_run_script")
          and OK(g("spindoctor_run_preset")) and "qc-001" in g("spindoctor_run_preset"), {k: v[0][:150] for k, v in out.items()})
        th = g("spindoctor_test_theory"); pdfs = re.findall(r'"([^"]+\.pdf)"', th)
        T("Custom MCP theory test from the chat: verdict supported, 2 excerpts recorded, theory PDF on disk",
          re.search(r'"verdict":\s*"supported"', th) and re.search(r'"excerptsRecorded":\s*2', th) and pdfs and os.path.isfile(pdfs[0]), th[:300])
        T("Custom Tool (NodeVM, child_process): function table (gates) and a GHZ script through the Flowise variables",
          "Gate set" in g("spindoctor_qwerty", 0) and OK(g("spindoctor_qwerty", 1)) and ws in g("spindoctor_qwerty", 1).replace("\\\\", "\\"),
          [g("spindoctor_qwerty", 0)[:150], g("spindoctor_qwerty", 1)[:150]])
        if add_node:
            T("custom node tool: preset qc-002 ok and preset list filtered by 'grover'",
              OK(g("spindoctor_node", 0)) and "qc-002" in g("spindoctor_node", 0) and "grover" in g("spindoctor_node", 1).lower(), [g("spindoctor_node", 0)[:150], g("spindoctor_node", 1)[:150]])
        recs = [json.loads(l) for l in open(slog)] if os.path.exists(slog) else []
        offered = sorted(set(recs[0]["tools"])) if recs else []
        want = sorted(TOOLS + ["spindoctor_qwerty"] + (["spindoctor_node"] if add_node else []))
        T("the model was offered exactly the expected tools (%d)" % len(want), offered == want, offered)
    finally:
        if stub: stub.kill()
        try: os.killpg(srv.pid, signal.SIGTERM); srv.wait(30)
        except Exception: pass
        shutil.rmtree(tmp, ignore_errors=True)


def main():
    a = sys.argv[1:]; opt = {}; i = 0
    while i < len(a):
        if a[i] == "--add-node": opt["--add-node"] = True; i += 1
        else: opt[a[i]] = a[i + 1]; i += 2
    outp = opt.get("--out", os.path.join(HERE, "host_check.json"))
    static()
    if opt.get("--flowise-dir"):
        real(os.path.abspath(opt["--flowise-dir"]), opt.get("--node") or shutil.which("node") or "node", bool(opt.get("--add-node")))
        e2e = os.path.join(HERE, "e2e_results.json")
        r = subprocess.run([sys.executable, os.path.join(HERE, "e2e_mcp.py"), "--server", sys.executable, MCP, "--examples", os.path.join(ENGINE, "examples", "theory"), "--out", e2e],
                           stdout=subprocess.PIPE, stderr=subprocess.STDOUT, timeout=3600)
        t = r.stdout.decode("utf-8", "replace"); m = re.search(r"SUMMARY (\d+)/(\d+)", t)
        T("shared E2E suite against the server Custom MCP starts (engine/scripts/spindoctor_mcp.py): %s" % (m.group(0) if m else "?"),
          r.returncode == 0 and m and m.group(1) == m.group(2), "\n".join(l for l in t.splitlines() if l.startswith("FAIL"))[-500:])
    json.dump({"passed": sum(r["pass"] for r in R), "total": len(R), "python": sys.version.split()[0], "checks": R}, open(outp, "w"), indent=1)
    print("HOST CHECK %d/%d passed" % (sum(r["pass"] for r in R), len(R)))
    return 0 if all(r["pass"] for r in R) else 1


if __name__ == "__main__":
    sys.exit(main())
