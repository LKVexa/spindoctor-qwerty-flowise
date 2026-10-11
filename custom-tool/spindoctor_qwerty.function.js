// SpinDoctor Qwerty 1.1.0 - Flowise Custom Tool function
// Copyright (C) 2026 RUSSELL PHILIP SMITHSON <russellsmithson77@outlook.com>
// SPDX-License-Identifier: GPL-3.0-or-later
// Runs the bundled SpinDoctor engine (classical FP64 simulator, not a quantum computer) with Python 3 on the Flowise server.
// Needs the server setting TOOL_FUNCTION_BUILTIN_DEP=child_process (or a list that includes it).
// Flowise variables: spindoctor_cli (required: absolute path of engine/scripts/spindoctor_cli.py),
// spindoctor_python (optional: python3 / python / py / full path), spindoctor_workspace (optional: reports folder),
// spindoctor_timeout_s (optional, default 280; Flowise stops tool functions after SANDBOX_TIMEOUT, 300 s by default).
// Input Schema properties arrive as $action and $input. No network access.
// Flowise hides `process` from tool functions, so settings come only from $vars and Windows is detected from the path separator.
const { spawn } = require('child_process');
const V = (typeof $vars === 'object' && $vars) ? $vars : {};
const cli = String(V.spindoctor_cli || '').trim();
const python = String(V.spindoctor_python || '').trim() || (require('path').sep === '\\' ? 'python' : 'python3');
const workspace = String(V.spindoctor_workspace || '').trim();
const timeoutS = Math.max(5, Number(V.spindoctor_timeout_s) || 280);
if (!cli) return 'SpinDoctor is not set up: create the Flowise variable spindoctor_cli with the absolute path of engine/scripts/spindoctor_cli.py.';
const action = String(typeof $action === 'undefined' ? '' : $action).toLowerCase().trim();
const text = typeof $input === 'undefined' || $input === null ? '' : String($input);
const ws = (a) => (workspace ? Object.assign({ workspace: workspace }, a) : a);
let tool;
let args;
if (action === 'script') { tool = 'spindoctor_run_script'; args = ws({ script: text }); }
else if (action === 'folder') { tool = 'spindoctor_run_script'; args = ws({ script: 'q.folder run path="' + text.trim().replace(/"/g, '') + '"' }); }
else if (action === 'preset') {
  const p = text.trim().split(/\s+/).filter(Boolean); const ov = {};
  for (const x of p.slice(1)) { const i = x.indexOf('='); if (i > 0) ov[x.slice(0, i)] = x.slice(i + 1); }
  tool = 'spindoctor_run_preset'; args = ws({ preset_id: p[0] || '', overrides: ov });
}
else if (action === 'list') { tool = 'spindoctor_list_presets'; args = { filter: text }; }
else if (action === 'report') { tool = 'spindoctor_report'; args = ws(text.trim() ? { name: text.trim() } : { limit: 10 }); }
else if (action === 'functions') { const p = text.trim().split(/\s+/).filter(Boolean); tool = 'spindoctor_functions'; args = { section: p[0] || 'commands', filter: p.slice(1).join(' ') }; }
else if (action === 'theory') {
  tool = 'spindoctor_test_theory';
  if (text.trim().startsWith('{')) { try { args = ws(JSON.parse(text)); } catch (e) { return 'theory input must be a JSON object: ' + e.message; } }
  else args = ws({ action: 'extract', source: 'text', text: text });
}
else return 'Unknown action "' + action + '". Use script, folder, preset, list, report, functions or theory.';
const LIMIT = 60000;
return await new Promise((resolve) => {
  let out = ''; let err = ''; let done = false;
  const finish = (s) => { if (!done) { done = true; clearTimeout(timer); resolve(s); } };
  let child;
  try { child = spawn(python, ['-X', 'utf8', '-B', cli, 'tool', tool], { windowsHide: true }); }
  catch (e) { finish('Python 3 is required to run SpinDoctor: ' + e.message); return; }
  const timer = setTimeout(() => { child.kill(); finish(JSON.stringify({ ok: false, error: 'SpinDoctor timed out after ' + timeoutS + ' s' })); }, timeoutS * 1000);
  child.stdout.setEncoding('utf8'); child.stderr.setEncoding('utf8');
  child.stdout.on('data', (d) => { if (out.length < 64 * 1024 * 1024) out += d; });
  child.stderr.on('data', (d) => { err = (err + d).slice(-4000); });
  child.on('error', (e) => finish('Python 3 is required to run SpinDoctor (' + python + '): ' + e.message));
  child.on('close', () => {
    const line = out.trim().split('\n').pop() || JSON.stringify({ ok: false, error: err.slice(-2000) || 'no output from the engine' });
    try { const j = JSON.parse(line); if (j.ok && typeof j.markdown === 'string') { finish(j.markdown); return; } } catch (e) { /* not JSON */ }
    finish(line.length > LIMIT ? line.slice(0, LIMIT) + '...[truncated; see the report files]' : line);
  });
  child.stdin.on('error', () => {});
  child.stdin.end(JSON.stringify(args));
});
