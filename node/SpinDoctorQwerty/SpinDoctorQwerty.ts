// SpinDoctor Qwerty 1.1.0 - Flowise custom node
// Copyright (C) 2026 RUSSELL PHILIP SMITHSON <russellsmithson77@outlook.com>
// SPDX-License-Identifier: GPL-3.0-or-later
// This program is free software: you can redistribute it and/or modify it under the terms of the GNU General
// Public License as published by the Free Software Foundation, either version 3 of the License, or (at your
// option) any later version. It is distributed WITHOUT ANY WARRANTY; see the LICENSE file for details.
//
// Flowise custom node (https://docs.flowiseai.com/contributing/building-node). Copy this folder to
// packages/components/nodes/tools/SpinDoctorQwerty/ in a Flowise source checkout and build. It returns one LangChain tool that
// runs the bundled SpinDoctor engine (engine/scripts/spindoctor_cli.py) with Python 3 on the Flowise server.
// Classical FP64 simulation - not a quantum computer. No network access.
import { spawn } from 'child_process'
import { z } from 'zod'
import { DynamicStructuredTool } from '@langchain/core/tools'
import { INode, INodeData, INodeParams } from '../../../src/Interface'
import { getBaseClasses } from '../../../src/utils'

const OUTPUT_LIMIT = 60000
const ACTIONS = ['script', 'folder', 'preset', 'list', 'report', 'functions', 'theory'] as const

export function callEngine(python: string, cli: string, tool: string, args: Record<string, unknown>, timeoutS = 280): Promise<string> {
    return new Promise((resolve) => {
        let out = ''
        let err = ''
        let done = false
        const finish = (s: string) => {
            if (!done) {
                done = true
                clearTimeout(timer)
                resolve(s)
            }
        }
        const child = spawn(python, [cli, 'tool', tool], {
            windowsHide: true,
            env: { ...process.env, PYTHONUTF8: '1', PYTHONDONTWRITEBYTECODE: '1' }
        })
        const timer = setTimeout(() => {
            child.kill()
            finish(JSON.stringify({ ok: false, error: `SpinDoctor timed out after ${timeoutS} s` }))
        }, timeoutS * 1000)
        child.stdout.setEncoding('utf8')
        child.stderr.setEncoding('utf8')
        child.stdout.on('data', (d: string) => {
            if (out.length < 64 * 1024 * 1024) out += d
        })
        child.stderr.on('data', (d: string) => {
            err = (err + d).slice(-4000)
        })
        child.on('error', (e) => finish(`Python 3 is required to run SpinDoctor (${python}): ${e.message}`))
        child.on('close', () => {
            const line = out.trim().split('\n').pop() || JSON.stringify({ ok: false, error: err.slice(-2000) || 'no output from the engine' })
            try {
                const j = JSON.parse(line)
                if (j.ok && typeof j.markdown === 'string') {
                    finish(j.markdown)
                    return
                }
            } catch {
                /* not JSON */
            }
            finish(line.length > OUTPUT_LIMIT ? line.slice(0, OUTPUT_LIMIT) + '...[truncated; see the report files]' : line)
        })
        child.stdin.on('error', () => undefined)
        child.stdin.end(JSON.stringify(args))
    })
}

export function toEngineCall(action: string, input: string, workspace?: string): { tool: string; args: Record<string, unknown> } | string {
    const text = input ?? ''
    const ws = (a: Record<string, unknown>) => (workspace ? { workspace, ...a } : a)
    switch (action) {
        case 'script':
            return { tool: 'spindoctor_run_script', args: ws({ script: text }) }
        case 'folder':
            return { tool: 'spindoctor_run_script', args: ws({ script: `q.folder run path="${text.trim().replace(/"/g, '')}"` }) }
        case 'preset': {
            const parts = text.trim().split(/\s+/).filter(Boolean)
            const overrides: Record<string, string> = {}
            for (const p of parts.slice(1)) {
                const i = p.indexOf('=')
                if (i > 0) overrides[p.slice(0, i)] = p.slice(i + 1)
            }
            return { tool: 'spindoctor_run_preset', args: ws({ preset_id: parts[0] || '', overrides }) }
        }
        case 'list':
            return { tool: 'spindoctor_list_presets', args: { filter: text } }
        case 'report':
            return { tool: 'spindoctor_report', args: ws(text.trim() ? { name: text.trim() } : { limit: 10 }) }
        case 'functions': {
            const p = text.trim().split(/\s+/).filter(Boolean)
            return { tool: 'spindoctor_functions', args: { section: p[0] || 'commands', filter: p.slice(1).join(' ') } }
        }
        case 'theory':
            if (text.trim().startsWith('{')) {
                try {
                    return { tool: 'spindoctor_test_theory', args: ws(JSON.parse(text)) }
                } catch (e) {
                    return 'theory input must be a JSON object: ' + (e as Error).message
                }
            }
            return { tool: 'spindoctor_test_theory', args: ws({ action: 'extract', source: 'text', text }) }
        default:
            return `Unknown action "${action}". Use ${ACTIONS.join(', ')}.`
    }
}

export const TOOL_DESCRIPTION =
    'Run the SpinDoctor 3.1.2 quantum-circuit SIMULATOR (classical FP64 on this server, not a quantum computer; 1-298 logical qubits, ' +
    'at most 59 in one entangled group). action=script runs q.* commands (one per line); action=folder runs every command file in a ' +
    'folder (input: absolute folder path); action=preset runs qc-001..qc-241 (input: id plus optional name=value overrides); ' +
    'action=list lists presets (input: filter); action=report shows a report (input: name; empty lists recent); action=functions returns ' +
    'the function table (input: section commands|gates|tools|presets|all plus optional filter; show it to the user verbatim); ' +
    'action=theory tests a theory (input: JSON with source file|text|chat, path, text, excerpts, hypothesis, prediction, script, checks; ' +
    'for a theory from the chat, summarise it and get the user to confirm first). Never present results as quantum hardware or quantum advantage.'

class SpinDoctorQwerty_Tools implements INode {
    label: string
    name: string
    version: number
    description: string
    type: string
    icon: string
    category: string
    author: string
    baseClasses: string[]
    inputs: INodeParams[]

    constructor() {
        this.label = 'SpinDoctor Qwerty'
        this.name = 'spinDoctorQwerty'
        this.version = 2.0
        this.type = 'SpinDoctorQwerty'
        this.icon = 'spindoctor.svg'
        this.category = 'Tools'
        this.author = 'RUSSELL PHILIP SMITHSON'
        this.description =
            'SpinDoctor 3.1.2 quantum-circuit simulator (classical): q.* scripts, folders, the 241 presets, reports, function table, theory tests'
        // 'Tool' lets the node connect to agent tool inputs (a DynamicStructuredTool alone only reports StructuredTool)
        this.baseClasses = [this.type, 'Tool', ...getBaseClasses(DynamicStructuredTool)]
        this.inputs = [
            {
                label: 'Engine CLI path',
                name: 'enginePath',
                type: 'string',
                placeholder: '/path/to/spindoctor-qwerty-flowise/engine/scripts/spindoctor_cli.py',
                description: 'Absolute path of engine/scripts/spindoctor_cli.py on the Flowise server'
            },
            { label: 'Python executable', name: 'python', type: 'string', optional: true, placeholder: 'python3' },
            {
                label: 'Workspace folder',
                name: 'workspace',
                type: 'string',
                optional: true,
                additionalParams: true,
                description: 'Where state and reports go (default ~/spindoctor-workspace)'
            },
            { label: 'Tool name', name: 'toolName', type: 'string', optional: true, additionalParams: true, placeholder: 'spindoctor_qwerty' },
            { label: 'Timeout (seconds)', name: 'timeout', type: 'number', optional: true, additionalParams: true, placeholder: '280' }
        ]
    }

    async init(nodeData: INodeData): Promise<any> {
        const cli = ((nodeData.inputs?.enginePath as string) || process.env.SPINDOCTOR_QWERTY_CLI || '').trim()
        const python = ((nodeData.inputs?.python as string) || '').trim() || (process.platform === 'win32' ? 'python' : 'python3')
        const workspace = ((nodeData.inputs?.workspace as string) || '').trim() || undefined
        const name = ((nodeData.inputs?.toolName as string) || '').trim() || 'spindoctor_qwerty'
        const timeoutS = Math.max(5, Number(nodeData.inputs?.timeout) || 280)
        if (!cli) throw new Error('SpinDoctor Qwerty: set "Engine CLI path" to the absolute path of engine/scripts/spindoctor_cli.py')
        return new DynamicStructuredTool({
            name,
            description: TOOL_DESCRIPTION,
            schema: z.object({
                action: z.enum(ACTIONS).describe('What to do'),
                input: z.string().optional().describe('Commands, folder path, preset id + overrides, filter text, report name, section, or theory JSON')
            }),
            func: async ({ action, input }: { action: string; input?: string }) => {
                const call = toEngineCall(action, input ?? '', workspace)
                if (typeof call === 'string') return call
                return callEngine(python, cli, call.tool, call.args, timeoutS)
            }
        })
    }
}

module.exports = { nodeClass: SpinDoctorQwerty_Tools, callEngine, toEngineCall, TOOL_DESCRIPTION }
