import { afterEach, beforeEach, expect, test } from "bun:test";
import * as zod from "@oh-my-pi/omptype/zod";
import { createHash } from "node:crypto";
import { existsSync, mkdirSync, mkdtempSync, readFileSync, rmSync, symlinkSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { dirname, join } from "node:path";
import softwareFactory from "../omp-extension.ts";

let repo, runtime, ctx, sequence;
const vision = "docs/product-vision.md";
const architecture = "docs/architecture.md";
const feature = "docs/features/example";
function bind() {
  const hooks = {}, tools = {}, commands = {};
  softwareFactory({ zod, registerTool(tool) { tools[tool.name] = tool; },
    on(event, handler) { hooks[event] = handler; }, registerCommand(name, command) { commands[name] = command; } });
  return { hooks, tools, commands };
}
function document(path, approved = false, state = "draft", body = "# Document\n") {
  const type = path === vision ? "vision" : path === architecture ? "arch" : path.endsWith("system-design.md") ? "sd"
    : path.endsWith("implementation-plan.md") ? "plan" : path.endsWith("tdd.md") ? "tdd" : "prd";
  mkdirSync(dirname(join(repo, path)), { recursive: true });
  writeFileSync(join(repo, path), `---\nstate: ${state}\nrevision: ${type}-r1\n---\n${body}`);
  if (approved) {
    const agent = type === "tdd" || type === "plan";
    const file = join(repo, "docs", agent ? "agent-approvals.json" : "user-approvals.json");
    const manifest = existsSync(file) ? JSON.parse(readFileSync(file, "utf8")) : {};
    const hash = createHash("sha256").update(body).digest("hex");
    manifest[path] = agent ? { hash, evidence: "Reviews and checks passed." } : hash;
    writeFileSync(file, JSON.stringify(manifest));
  }
}
function ready(plan = false) {
  document(vision, true); document(architecture, true); document(`${feature}/prd.md`, true);
  document(`${feature}/tdd.md`, true);
  if (plan) document(`${feature}/implementation-plan.md`, true);
}
async function call(toolName, input, context = ctx, run = runtime) {
  return run.hooks.tool_call({ toolName, toolCallId: `call-${sequence++}`, input }, context);
}
async function spawn(agent = "draft-product-vision-agent", context = ctx, run = runtime) {
  return run.hooks.before_subagent_spawn({ agent, invocationKind: "task", patterns: [], spawnKey: `spawn-${sequence++}` }, context);
}
const reports = () => join(repo, ".session", "main");
let rewritten;
// Dispatch one reviewer through the hooks and save its report where OMP would (agent://<id>).
async function review(path, findings = [], { agent = "review-doc-technical-design-agent", name = `Review${sequence}`, failed = false } = {}) {
  const toolCallId = `task-${sequence++}`;
  const input = { context: "", tasks: [{ agent, name, task: `Review \`${path}\` per your skill.` }] };
  const blocked = await runtime.hooks.tool_call({ toolName: "task", toolCallId, input }, ctx);
  if (blocked?.block) return blocked;
  rewritten = blocked?.input;
  await runtime.hooks.tool_result({ toolName: "task", toolCallId, isError: failed, details: { progress: [{ index: 0, id: name }] } }, ctx);
  mkdirSync(reports(), { recursive: true });
  const body = findings.map(([id, severity]) => `### ${id} — Finding ${id}\n\n**Severity:** ${severity}\n`).join("\n") || "None";
  writeFileSync(join(reports(), `${name}.md`), JSON.stringify(`Outcome.\n\n## Findings\n\n${body}\n\n## Questions\n\nNone\n`));
}
async function execute(name, params, context = ctx) {
  return runtime.tools[name].execute("tool", runtime.tools[name].parameters.parse(params), undefined, undefined, context);
}
beforeEach(() => {
  repo = mkdtempSync(join(tmpdir(), "playbook-hooks-"));
  mkdirSync(join(repo, "docs"));
  writeFileSync(join(repo, "docs/user-approvals.json"), "{}");
  runtime = bind(); sequence = 0;
  ctx = { cwd: repo, agent: { kind: "main", id: "Main", name: "main", depth: 0 }, hasUI: true,
    ui: { confirm: async () => true, notify() {} },
    sessionManager: { getSessionId: () => "main", getSessionFile: () => `${reports()}.jsonl` } };
});
afterEach(() => rmSync(repo, { recursive: true, force: true }));

test("approval guard blocks write, edit sections, derived paths, AST globs/directories and aliases", async () => {
  symlinkSync(join(repo, "docs"), join(repo, "alias"));
  for (const name of ["user-approvals.json", "agent-approvals.json"]) {
    for (const [tool, input] of [
      ["write", { path: `docs/${name}` }], ["write", { path: join(repo, `docs/../docs/${name}`) }],
      ["write", { path: `alias/${name}` }], ["edit", { input: `[docs/${name}#A123]\nPUT 1.=1:\n+{}` }],
      ["edit", { paths: [`docs/${name}`] }], ["edit", { input: `[other.json#A123]\nMV docs/${name}` }],
      ["ast_edit", { paths: ["docs/*.json"] }], ["ast_edit", { paths: ["**/*"] }], ["ast_edit", { paths: ["docs"] }],
    ]) expect((await call(tool, input))?.block).toBe(true);
    expect(await call("write", { path: `elsewhere/${name}` })).toBeUndefined();
    expect(await call("read", { path: `docs/${name}` })).toBeUndefined();
    for (const tool of ["write", "edit"])
      for (const path of ["docs", "docs/*.json", "alias"])
        expect((await call(tool, { path }))?.block).toBe(true);
  }
});

test("approval guard blocks shell/eval write patterns but allows reads", async () => {
  for (const name of ["user-approvals.json", "agent-approvals.json"]) {
    for (const text of [`printf x > docs/${name}`, `tee docs/${name}`, `sed -i '' 's/x/y/' docs/${name}`,
      `mv tmp docs/${name}`, `cp tmp docs/${name}`, `rm docs/${name}`, `truncate -s 0 docs/${name}`,
      `open('docs/${name}', 'w').write('{}')`, `writeFileSync('docs/${name}', '{}')`, `Bun.write('docs/${name}', '{}')`])
      for (const tool of ["bash", "eval"]) expect((await call(tool, tool === "bash" ? { command: text } : { code: text }))?.block).toBe(true);
    for (const command of [`cat docs/${name}`, `jq . docs/${name}`, `git diff -- docs/${name}`,
      `git log -- docs/${name}`, `git show HEAD:docs/${name}`])
      expect(await call("bash", { command })).toBeUndefined();
  }
});

test("doc_approval wraps modes and shares the hook's exact refusal text", async () => {
  document(vision);
  const before = readFileSync(join(repo, "docs/user-approvals.json"), "utf8");
  for (const mode of ["accept", "revoke"]) {
    const refused = await execute("doc_approval", { mode, path: vision, ...(mode === "revoke" ? { reason: "Changed." } : {}) });
    expect(refused.isError).toBeUndefined(); expect(refused.details.status).toBe("refused");
    for (const name of ["user-approvals.json", "agent-approvals.json"])
      expect(refused.content[0].text).toBe((await call("write", { path: `docs/${name}` })).reason);
  }
  expect(readFileSync(join(repo, "docs/user-approvals.json"), "utf8")).toBe(before);
  document("docs/roadmap.md");
  for (const mode of ["accept", "revoke"]) {
    const refused = await execute("doc_approval", { mode, path: "docs/roadmap.md", ...(mode === "revoke" ? { reason: "Changed." } : {}) });
    expect(refused.details.data.reason).toBe("ungated");
    expect(refused.content[0].text).toBe((await call("write", { path: "docs/user-approvals.json" })).reason);
  }
  document(`${feature}/tdd.md`);
  const unreviewed = await execute("doc_approval", { mode: "accept", path: `${feature}/tdd.md` });
  expect(unreviewed.details.status).toBe("refused");
  expect(unreviewed.content[0].text).toContain("review_ledger");
  await review(`${feature}/tdd.md`);
  expect((await execute("review_ledger", { mode: "close", path: `${feature}/tdd.md` })).details.status).toBe("ok");
  expect((await execute("doc_approval", { mode: "accept", path: `${feature}/tdd.md` })).details.status).toBe("accepted");
  const status = await execute("doc_approval", { mode: "status", path: `${feature}/tdd.md` });
  expect(status.details.data[0].approved).toBe(true);
  expect((await execute("doc_approval", { mode: "revoke", path: `${feature}/tdd.md`, reason: "Changed design." })).details.status).toBe("revoked");
  expect((await execute("doc_approval", { mode: "revoke", path: `${feature}/tdd.md`, reason: "Already removed." })).details.status).toBe("unchanged");
  for (const params of [{ mode: "accept" }, { mode: "status", reason: "wrong mode" }])
    expect((await execute("doc_approval", params)).isError).toBe(true);
});

test("factory_status and approval tools fail closed on malformed approvals", async () => {
  expect((await execute("factory_status", {})).details.nextStep).toContain(vision);
  writeFileSync(join(repo, "docs/user-approvals.json"), "{");
  expect((await execute("factory_status", {})).isError).toBe(true);
  expect((await execute("doc_approval", { mode: "status" })).isError).toBe(true);
  await runtime.hooks.turn_start({}, ctx);
  await expect(call("write", { path: `${feature}/tdd.md` })).rejects.toThrow();
  await expect(spawn("orchestrate-implementation-plan-agent")).rejects.toThrow();
});

test("creation order blocks only new downstream product documents and preserves existing edits", async () => {
  document(vision);
  for (const [tool, input] of [["write", { path: "docs/architecture.md" }],
    ["edit", { input: `[${feature}/prd.md#A123]\nPUT 1.=1:\n+x` }]]) {
    const result = await call(tool, input);
    expect(result?.block).toBe(true); expect(result.reason).toContain(`${vision} is waiting for developer approval`);
    expect(result.reason).toContain("Next expected step:"); expect(result.reason).toContain("edits to existing documents");
    expect(result.reason).not.toContain("..");
  }
  document(`${feature}/implementation-plan.md`);
  for (const tool of ["write", "edit"]) expect(await call(tool, { path: `${feature}/implementation-plan.md` })).toBeUndefined();
  for (const path of ["docs/roadmap.md", "guides/tdd.md", "notes/prd.md", "docs/features/example/readme.md", "../outside/docs/architecture.md"])
    expect(await call("write", { path })).toBeUndefined();
  expect(await call("write", { path: vision })).toBeUndefined();
});

test("creation order uses session repo paths and current slice gates", async () => {
  ready();
  document(`${feature}/system-design.md`, true, "draft", "# System design\n## Slice order\n- slices/01-first\n- slices/02-second\n");
  document(`${feature}/tdd.md`, true, "done"); document(`${feature}/implementation-plan.md`, true, "done");
  document(`${feature}/slices/01-first/tdd.md`);
  const nested = { ...ctx, cwd: join(repo, "docs") };
  const result = await call("write", { path: `${feature}/slices/02-second/tdd.md` }, nested);
  expect(result?.block).toBe(true); expect(result.reason).toContain("slices/01-first/tdd.md");
  expect((await call("write", { path: join(repo, `${feature}/slices/01-first/implementation-plan.md`) }))?.block).toBe(true);
});

test("implementation gate requires valid TDD, plan and upstream developer gates; nested workers/reviewers pass", async () => {
  ready();
  expect((await spawn("orchestrate-implementation-plan-agent"))?.block).toBe(true);
  document(`${feature}/implementation-plan.md`, true);
  await runtime.hooks.turn_start({}, ctx);
  expect(await spawn("orchestrate-implementation-plan-agent")).toBeUndefined();
  document(architecture, false, "draft", "# Changed architecture\n"); await runtime.hooks.turn_start({}, ctx);
  expect((await spawn("orchestrate-implementation-plan-agent"))?.reason).toContain(architecture);
  const sub = { ...ctx, agent: { kind: "sub", id: "Worker", parentId: "Main", name: "task", depth: 1 } };
  for (const agent of ["task", "review-code-tests-agent", "orchestrate-fix-agent"])
    expect(await spawn(agent, sub, bind())).toBeUndefined();
});

test("ambiguous unfinished features do not block order or implementation", async () => {
  document(vision); document(`${feature}/prd.md`); document("docs/features/other/prd.md");
  expect(await call("write", { path: `${feature}/tdd.md` })).toBeUndefined();
  expect(await spawn("orchestrate-implementation-plan-agent")).toBeUndefined();
  const result = await runtime.hooks.before_agent_start({ systemPrompt: "BASE" }, ctx);
  expect(result.systemPrompt).toContain("Multiple features have unfinished work");
});

test("reviews gate on decisions, switch to change checks once clean, and stop a fix that keeps failing until the developer answers", async () => {
  const tdd = `${feature}/tdd.md`;
  const decide = (finding, decision, extra = {}) => execute("review_ledger", { mode: "decide", path: tdd,
    decisions: [{ finding, decision, reason: "Triage.", ...extra }] });
  document(tdd);
  expect(await review(tdd, [["R1-F1", "Major"], ["R1-F2", "Minor"]])).toBeUndefined();
  expect(existsSync(join(repo, ".playbook/reviews/features/example/tdd.json"))).toBe(true);
  expect((await review(tdd))?.reason).toContain("1:R1-F1, 1:R1-F2");
  expect((await decide("1:R1-F1", "nit")).content[0].text).toContain("only Minor");
  await decide("1:R1-F1", "accepted"); await decide("1:R1-F2", "nit");
  for (const round of [2, 3]) {
    document(tdd, false, "draft", `# Fix attempt ${round}\n`);
    expect(await review(tdd, [["R1-F1", "Major"]])).toBeUndefined();
    expect(rewritten).toBeUndefined();
    await decide(`${round}:R1-F1`, "duplicate", { duplicateOf: "1:R1-F1" });
  }
  document(tdd, false, "draft", "# Fix attempt 4\n");
  const stopped = await review(tdd);
  expect(stopped?.reason).toContain("has come back 2 times"); expect(stopped.reason).toContain("summarize for the developer");
  for (const event of [{ details: { selectedOptions: ["yes"], timedOut: true } }, { details: { chatRedirect: true } }]) {
    await runtime.hooks.tool_result({ toolName: "ask", toolCallId: "ask", ...event }, ctx);
    expect((await review(tdd))?.block).toBe(true);
  }
  await bind().hooks.input({}, { ...ctx, agent: { kind: "sub", id: "Child", parentId: "Main", name: "task", depth: 1 } });
  expect((await review(tdd))?.block).toBe(true);
  await new Promise(resolve => setTimeout(resolve, 5));
  await runtime.hooks.tool_result({ toolName: "ask", toolCallId: "ask", details: { results: [{ selectedOptions: ["yes"] }] } }, ctx);
  expect(await review(tdd)).toBeUndefined();
  document(tdd, false, "draft", "# Fix attempt 4\nNow complete.\n");
  expect(await review(tdd)).toBeUndefined();
  expect(rewritten.tasks[0].task).toContain("change check, not a full review");
  expect(rewritten.tasks[0].task).toContain("+Now complete.");
  const status = await execute("review_ledger", { mode: "status", path: tdd });
  expect(status.details.data.ledgers[0].rounds.map(round => round.mode)).toEqual(["full", "full", "full", "full", "check"]);
});

test("a reviewer must name one document, and a failed dispatch records no round", async () => {
  document(`${feature}/tdd.md`); document(`${feature}/slices/second/tdd.md`);
  const toolCallId = `task-${sequence++}`;
  const ambiguous = await runtime.hooks.tool_call({ toolName: "task", toolCallId, input: { tasks: [
    { agent: "review-doc-technical-design-agent", name: "Both", task: `Review ${feature}/tdd.md and ${feature}/slices/second/tdd.md.` }] } }, ctx);
  expect(ambiguous?.reason).toContain("several review subjects");
  expect(await review(`${feature}/tdd.md`, [], { failed: true })).toBeUndefined();
  const status = await execute("review_ledger", { mode: "status", path: `${feature}/tdd.md` });
  expect(status.details.data.ledgers[0].rounds).toEqual([]);
  const worker = { ...ctx, agent: { kind: "sub", id: "Worker", parentId: "Main", name: "task", depth: 1 } };
  expect(await bind().hooks.tool_call({ toolName: "task", toolCallId: "nested", input: { tasks: [
    { agent: "review-doc-technical-design-agent", name: "Nested", task: "Review the design." }] } }, worker)).toBeUndefined();
});

test("review ledgers are written only by the Playbook", async () => {
  document(`${feature}/tdd.md`);
  await review(`${feature}/tdd.md`);
  const ledger = ".playbook/reviews/features/example/tdd.json";
  for (const [tool, input] of [["write", { path: ledger }], ["edit", { input: `[${ledger}#A123]\nPUT 1.=1:\n+{}` }],
    ["write", { path: ".playbook/reviews/features/example/new.json" }], ["ast_edit", { paths: [".playbook"] }],
    ["bash", { command: `printf '{}' > ${ledger}` }], ["eval", { code: `Bun.write('${ledger}', '{}')` }]])
    expect((await call(tool, input))?.reason).toContain("written only by the Playbook");
  for (const [tool, input] of [["read", { path: ledger }], ["bash", { command: `cat ${ledger}` }]])
    expect(await call(tool, input)).toBeUndefined();
});

test("status line preserves string/array base prompts, includes documents and skill, and is main-only", async () => {
  document(vision);
  const result = await runtime.hooks.before_agent_start({ systemPrompt: "BASE POLICY" }, ctx);
  expect(result.systemPrompt.startsWith("BASE POLICY\n")).toBe(true);
  expect(result.systemPrompt).toContain(`${vision}: draft, not approved`);
  expect(result.systemPrompt).toContain("skill://orchestrate-factory");
  expect(result.systemPrompt).not.toContain("..");
  const array = await runtime.hooks.before_agent_start({ systemPrompt: ["BASE POLICY"] }, ctx);
  expect(array.systemPrompt[0]).toBe("BASE POLICY");
  expect(await runtime.hooks.before_agent_start({ systemPrompt: "CHILD" }, { ...ctx, agent: { ...ctx.agent, kind: "sub", id: "Sub", parentId: "Main" } })).toBeUndefined();
});

test("hash command shows a paste-ready line and writes nothing", async () => {
  document(vision);
  const before = readFileSync(join(repo, "docs/user-approvals.json"), "utf8");
  const command = runtime.commands["playbook-hash"];
  await command.handler(vision, { ...ctx, hasUI: false, ui: undefined });
  expect(readFileSync(join(repo, "docs/user-approvals.json"), "utf8")).toBe(before);
  const notifications = [];
  await command.handler(vision, { ...ctx, ui: { notify: (...args) => notifications.push(args) } });
  const hash = createHash("sha256").update("# Document\n").digest("hex");
  expect(notifications).toEqual([[`${vision}\n"${vision}": "${hash}",`, "info"]]);
  expect(readFileSync(join(repo, "docs/user-approvals.json"), "utf8")).toBe(before);
  expect(existsSync(join(repo, "docs/agent-approvals.json"))).toBe(false);
});

test("hash command without a path groups developer-gated entries by approval state", async () => {
  document(vision, true);
  document(architecture, true);
  document(architecture, false, "draft", "# Changed\n");
  document(`${feature}/prd.md`);
  document(`${feature}/tdd.md`);
  const line = (path, body) => `"${path}": "${createHash("sha256").update(body).digest("hex")}",`;
  const notifications = [];
  await runtime.commands["playbook-hash"].handler("  ", { ...ctx, ui: { notify: (...args) => notifications.push(args) } });
  expect(notifications).toEqual([[[
    "Developer-gated documents. Paste only the entries you approve into docs/user-approvals.json.",
    `Changed since approval:\n${line(architecture, "# Changed\n")}`,
    `Not yet approved:\n${line(`${feature}/prd.md`, "# Document\n")}`,
    `Approved (current):\n${line(vision, "# Document\n")}`,
  ].join("\n\n"), "info"]]);
});

test("every hook is inert without user approvals even when agent approvals exist", async () => {
  rmSync(join(repo, "docs/user-approvals.json"));
  writeFileSync(join(repo, "docs/agent-approvals.json"), "{}");
  for (const [event, input] of [["tool_call", { toolName: "bash", input: { command: "printf x > docs/user-approvals.json" } }],
    ["before_subagent_spawn", { agent: "orchestrate-implementation-plan-agent" }], ["before_agent_start", { systemPrompt: "BASE" }],
    ["input", {}], ["turn_start", {}], ["tool_result", { toolName: "ask", details: { selectedOptions: ["yes"] } }]])
    expect(await runtime.hooks[event](input, ctx)).toBeUndefined();
  expect((await execute("factory_status", {})).details.optedIn).toBe(false);
  expect(existsSync(join(repo, "docs/user-approvals.json"))).toBe(false);
});

test("cached status is invalidated by child acceptance in the same main turn", async () => {
  ready();
  document(`${feature}/tdd.md`, false, "draft", "# Changed design\n");
  expect((await call("write", { path: `${feature}/implementation-plan.md` }))?.block).toBe(true);
  await review(`${feature}/tdd.md`);
  await execute("review_ledger", { mode: "close", path: `${feature}/tdd.md` });
  const child = { ...ctx, agent: { kind: "sub", id: "Accepter", parentId: "Main", name: "task", depth: 1 } };
  const tool = bind().tools.doc_approval;
  const result = await tool.execute("accept", { mode: "accept", path: `${feature}/tdd.md` }, undefined, undefined, child);
  expect(result.details.status).toBe("accepted");
  expect(await call("write", { path: `${feature}/implementation-plan.md` })).toBeUndefined();
});

test("missing upstream document refusals and status use accurate wording and single periods", async () => {
  const result = await call("write", { path: architecture });
  expect(result?.block).toBe(true);
  expect(result.reason).toBe(`${vision} does not exist yet. Next expected step: Create ${vision}. Discussion, research, and edits to existing documents are still open.`);
  expect(result.reason).not.toContain("..");
  const status = await runtime.hooks.before_agent_start({ systemPrompt: "BASE POLICY" }, ctx);
  expect(status.systemPrompt).toContain(`next=Create ${vision}. Use review_ledger status`);
  expect(status.systemPrompt).not.toContain("..");
});
