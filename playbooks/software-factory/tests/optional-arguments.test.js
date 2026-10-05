import { test, expect } from "bun:test";
import * as zod from "@oh-my-pi/omptype/zod";
import { mkdtempSync, mkdirSync, writeFileSync, rmSync, existsSync, unlinkSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import softwareFactory from "../omp-extension.ts";

function seed(ir) {
  if (ir.k === "union") return seed(ir.members.find(v => !["undefined", "null"].includes(v.k)));
  if (ir.k === "lit") return ir.v;
  if (ir.k === "enum") return ir.values?.[0] ?? ir.v?.[0];
  if (ir.k === "object") return Object.fromEntries(ir.props.filter(p => !p.opt).map(p => [p.key, seed(p.val)]));
  if (ir.k === "array") return [];
  if (ir.k === "boolean") return false;
  if (ir.k === "number") return 1;
  return "fixture";
}

function kinds(ir) {
  return ir.k === "union" ? ir.members.flatMap(kinds) : [ir.k];
}

// Every registration participates, including future tools: no tool-name allowlist.
test("all registered tools treat every schema-optional empty argument as absent", async () => {
  const directory = mkdtempSync(join(tmpdir(), "playbook-optionals-"));
  const home = process.env.HOME;
  process.env.HOME = directory;
  mkdirSync(join(directory, ".omp", "agent", "sessions"), { recursive: true });
  const tools = [];
  softwareFactory({ zod, registerTool: definition => tools.push(definition), on() {}, registerCommand() {} });
  const plan = join(directory, "plan.md");
  mkdirSync(join(directory, "docs"));
  writeFileSync(join(directory, "docs", "user-approvals.json"), "{}");
  const doc = join(directory, "docs", "product-vision.md");
  writeFileSync(plan, "### T01 — Check\n- Depends on: none\n- Targets: none\n- Change: Check behavior.\n- Done when: Verified.\n- Verify: true\n");
  writeFileSync(doc, "---\nstate: draft\nrevision: vision-r1\n---\n# Vision\n");
  const values = { plan, path: doc, command: "printf ok", cwd: directory, since: "2099-01-01", agent: "review-skill-agent",
    version: 1, kind: "input", title: "Input", context: "Need input", question: "Which?", blocking: false };
  const invoke = async (tool, params) => {
    const result = await tool.execute("sweep", tool.parameters.parse(params), undefined, undefined, { cwd: directory });
    const details = { ...result.details };
    if (details.logPath && existsSync(details.logPath)) unlinkSync(details.logPath);
    for (const key of ["request", "duration", "logPath"]) delete details[key];
    return { isError: result.isError, details };
  };
  try {
    for (const tool of tools) {
      const props = tool.parameters.ir.props;
      const required = Object.fromEntries(props.filter(p => !p.opt).map(p => [p.key, values[p.key] ?? seed(p.val)]));
      if (tool.name === "doc_approval") required.mode = "status";
      for (const [key, value] of Object.entries({ path: doc, needed: "Choose the input.", intentBasisUnavailableReason: "No product document exists." })) {
        if (props.some(p => p.key === key)) required[key] = value;
      }
      const result = await invoke(tool, required);
      expect({ tool: tool.name, error: result.isError }).toEqual({
        tool: tool.name, error: undefined,
      });
      // Required-by-mode optional fields are left absent; execution must diagnose
      // them identically, while truly optional fields execute real programs.
      for (const prop of props.filter(p => p.opt)) {
        const baseline = { ...required };
        delete baseline[prop.key];
        const absent = await invoke(tool, baseline);
        const types = kinds(prop.val);
        const empties = ["", null, ...(types.includes("array") ? [[]] : []), ...(types.includes("object") ? [{}] : [])];
        for (const value of empties) {
          expect(await invoke(tool, { ...baseline, [prop.key]: value })).toEqual(absent);
        }
        if (prop.key === "task" && tool.parameters.ir.props.some(p => p.key === "worktreeRoot")) {
          const rejected = await tool.execute("sweep", { ...required, mode: "protected-diff", repo: directory,
            base: "HEAD", head: "HEAD", task: "" }, undefined, undefined, { cwd: directory });
          expect(rejected.isError).toBe(true);
          expect(rejected.details.message).toContain("task must be non-empty");
        }
      }
    }
  } finally {
    process.env.HOME = home;
    rmSync(directory, { recursive: true, force: true });
  }
}, 30_000);
