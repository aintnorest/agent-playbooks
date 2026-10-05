import { afterEach, beforeEach, expect, test } from "bun:test";
import * as zod from "@oh-my-pi/omptype/zod";
import { spawnSync } from "node:child_process";
import { createHash } from "node:crypto";
import { mkdtempSync, mkdirSync, readFileSync, rmSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import softwareFactory from "../omp-extension.ts";

let workspace;
let repo;
let tool;
let statusTool;
let requestTool;
let runsTool;

function git(...args) {
  const result = spawnSync("git", args, { cwd: repo, encoding: "utf8" });
  if (result.error || result.status !== 0) {
    throw result.error ?? new Error(result.stderr);
  }
  return result.stdout.trim();
}

beforeEach(() => {
  workspace = mkdtempSync(join(tmpdir(), "playbook-tool-test-"));
  repo = join(workspace, "repo");
  mkdirSync(repo);
  softwareFactory({
    zod,
    on() {},
    registerCommand() {},
    registerTool(definition) {
      if (definition.name === "check_implementation_plan") tool = definition;
      if (definition.name === "check_doc_status") statusTool = definition;
      if (definition.name === "request_developer") requestTool = definition;
      if (definition.name === "collect_agent_runs") runsTool = definition;
    },
  });
  writeFileSync(join(repo, "implementation-plan.md"),
    "### T01 — Acceptance test\n" +
    "- Depends on: none\n" +
    "- Targets: `tests/test_accept.py` (create)\n" +
    "- Protects: tests/test_accept.py\n" +
    "- Change: Verify approved TDD scenario.\n" +
    "- Done when: Missing behavior fails as specified.\n" +
    "- Verify: Run acceptance test; expect specified failure.\n\n" +
    "### T02 — Implementation\n" +
    "- Depends on: T01\n" +
    "  - T01 — supplies acceptance test.\n" +
    "- Targets: `src/main.py` (create)\n" +
    "- Change: Implement approved design.\n" +
    "- Done when: Protected scenario passes.\n" +
    "- Verify: Run acceptance test; expect pass.\n");
  git("init", "-q");
  git("-c", "user.name=Test", "-c", "user.email=test@example.invalid",
      "commit", "-q", "--allow-empty", "-m", "base");
});

afterEach(() => {
  rmSync(workspace, { recursive: true, force: true });
});

test("static checks accept absent, null, and empty protected-diff fields", async () => {
  const plan = "implementation-plan.md";
  for (const mode of ["check", "json"]) {
    for (const fields of [
      {},
      { repo: null, base: null, head: null, task: null },
      { repo: "", base: "", head: "", task: "" },
    ]) {
      const result = await tool.execute("test", { mode, plan, ...fields },
        undefined, undefined, { cwd: repo });
      expect(result.isError).toBeUndefined();
      expect(result.details.status).toBe("ok");
      if (mode === "json") expect(result.details.tasks.map(task => task.id)).toEqual(["T01", "T02"]);
    }
  }

  const rejected = await tool.execute("test",
    { mode: "check", plan, repo: ".", base: "", head: "", task: "" },
    undefined, undefined, { cwd: repo });
  expect(rejected.isError).toBe(true);
  expect(rejected.details.message).toBe("Check and JSON modes do not accept repo, base, head, task, or worktreeRoot.");
});

test("document status tool reads metadata and rejects legacy prose", async () => {
  const docs = join(repo, "docs");
  mkdirSync(docs);
  const path = join(docs, "product-vision.md");
  const body = "# Product vision\n\n## Status\n\nReviewed against product research.\n";
  writeFileSync(path, "---\nstate: active\nrevision: vision-r2\n---\n" + body);
  writeFileSync(join(docs, "user-approvals.json"), JSON.stringify({
    "docs/product-vision.md": createHash("sha256").update(body).digest("hex"),
  }));
  const parsed = await statusTool.execute("test", { mode: "json", path, repo },
    undefined, undefined, { cwd: repo });
  expect(parsed.isError).toBeUndefined();
  expect(parsed.details.documents).toEqual([
    { path, type: "vision", state: "active", revision: "vision-r2",
      approval: { gate: "developer", valid: true } },
  ]);

  writeFileSync(path, "# Product vision\n\n## Status\n\nApproved.\n");
  const invalid = await statusTool.execute("test", { mode: "check", path },
    undefined, undefined, { cwd: repo });
  expect(invalid.isError).toBe(true);
  expect(invalid.details.stderr).toContain("missing status frontmatter");
});

test("document frozen-diff tool rejects edits to a delivered PRD", async () => {
  const feature = join(repo, "docs", "features", "search");
  mkdirSync(feature, { recursive: true });
  const path = join(feature, "prd.md");
  const body = "# Search\n\nThe delivered contract.\n";
  writeFileSync(path, "---\nstate: done\nrevision: prd-r3\n---\n" + body);
  writeFileSync(join(repo, "docs", "user-approvals.json"), JSON.stringify({
    "docs/features/search/prd.md": createHash("sha256").update(body).digest("hex"),
  }));
  git("add", "docs");
  git("-c", "user.name=Test", "-c", "user.email=test@example.invalid",
    "commit", "-q", "-m", "deliver feature");
  const base = git("rev-parse", "HEAD");

  writeFileSync(path, readFileSync(path, "utf8") + "\nA new requirement.\n");
  git("add", "docs/features/search/prd.md");
  git("-c", "user.name=Test", "-c", "user.email=test@example.invalid",
    "commit", "-q", "-m", "alter delivered feature");
  const head = git("rev-parse", "HEAD");
  const violation = await statusTool.execute("test", { mode: "frozen-diff", repo, base, head },
    undefined, undefined, { cwd: repo });
  expect(violation.isError).toBe(true);
  expect(violation.details.stderr).toContain("docs/features/search/prd.md");

  const check = await statusTool.execute("test", { mode: "frozen-diff", repo, base, head: base },
    undefined, undefined, { cwd: repo });
  expect(check.isError).toBeUndefined();
  expect(check.details.status).toBe("ok");
});

test("assigned candidate is checked in its recorded worktree through tool", async () => {
  const worktreeRoot = join(repo, ".worktrees");
  const worktree = join(worktreeRoot, "T02");
  writeFileSync(join(repo, ".gitignore"), ".worktrees/\n");
  git("add", ".gitignore");
  git("-c", "user.name=Test", "-c", "user.email=test@example.invalid",
    "commit", "-q", "-m", "ignore worktrees");
  mkdirSync(worktreeRoot);
  const base = git("rev-parse", "HEAD");
  git("worktree", "add", "-q", "-b", "impl/T02", worktree, base);
  const run = (...args) => {
    const result = spawnSync("git", ["-C", worktree, ...args], { encoding: "utf8" });
    if (result.status !== 0) throw new Error(result.stderr);
    return result.stdout.trim();
  };
  writeFileSync(join(worktree, "src.py"), "value = 1\n");
  run("add", "src.py");
  run("-c", "user.name=Test", "-c", "user.email=test@example.invalid",
    "commit", "-q", "-m", "implementation");
  const head = run("rev-parse", "HEAD");
  const plan = join(repo, "implementation-plan.md");
  writeFileSync(plan, readFileSync(plan, "utf8").trimEnd() +
    `\n- Assigned worktree: ${worktree}\n- Assigned branch: impl/T02\n`);
  const params = { mode: "protected-diff", plan, repo, base, head, task: "T02", worktreeRoot };
  const valid = await tool.execute("test", params, undefined, undefined, { cwd: repo });
  expect(valid.details.status).toBe("ok");
  const rejected = await tool.execute("test", { ...params, worktreeRoot: join(workspace, "other") },
    undefined, undefined, { cwd: repo });
  expect(rejected.isError).toBe(true);
  expect(rejected.details.stderr).toContain("must be <repo-root>/.worktrees");
});

test("out-of-plan protected diff treats empty worktreeRoot as absent", async () => {
  const result = await tool.execute("test",
    { mode: "protected-diff", plan: "implementation-plan.md", repo,
      base: "HEAD", head: "HEAD", worktreeRoot: "" },
    undefined, undefined, { cwd: repo });
  expect(result.isError).toBeUndefined();
  expect(result.details.status).toBe("ok");
});

test("protected diff fails closed when repo is null", async () => {
  const result = await tool.execute("test",
    { mode: "protected-diff", plan: "implementation-plan.md", repo: null,
      base: "HEAD", head: "HEAD", task: null },
    undefined, undefined, { cwd: repo });
  expect(result.isError).toBe(true);
  expect(result.details.message).toBe("Protected-diff mode requires repo, base, and head.");
});

test("registered tool admits ordinary changes but rejects protected edits", async () => {
  expect(tool.name).toBe("check_implementation_plan");
  mkdirSync(join(repo, "tests"));
  writeFileSync(join(repo, "tests/test_accept.py"), "assert False\n");
  git("add", "tests/test_accept.py");
  git("-c", "user.name=Test", "-c", "user.email=test@example.invalid",
      "commit", "-q", "-m", "acceptance");
  const base = git("rev-parse", "HEAD");

  mkdirSync(join(repo, "src"));
  writeFileSync(join(repo, "src/main.py"), "value = 1\n");
  git("add", "src/main.py");
  git("-c", "user.name=Test", "-c", "user.email=test@example.invalid",
      "commit", "-q", "-m", "implementation");
  const allowedHead = git("rev-parse", "HEAD");
  const parameters = { mode: "protected-diff", plan: "implementation-plan.md", repo,
    base, head: allowedHead, task: "T02" };
  const allowed = await tool.execute("test", parameters, undefined, undefined, { cwd: repo });
  expect(allowed.isError).toBeUndefined();
  expect(allowed.details.status).toBe("ok");
  const withoutTask = await tool.execute("test", { ...parameters, task: null },
    undefined, undefined, { cwd: repo });
  expect(withoutTask.isError).toBeUndefined();
  expect(withoutTask.details.status).toBe("ok");

  writeFileSync(join(repo, "tests/test_accept.py"), "assert True\n");
  git("add", "tests/test_accept.py");
  git("-c", "user.name=Test", "-c", "user.email=test@example.invalid",
      "commit", "-q", "-m", "alter protected test");
  const forbiddenHead = git("rev-parse", "HEAD");
  const violation = await tool.execute("test", { ...parameters, base: allowedHead,
    head: forbiddenHead }, undefined, undefined, { cwd: repo });
  expect(violation.isError).toBe(true);
  expect(violation.details.status).toBe("error");
  expect(violation.details.stderr).toContain("tests/test_accept.py");
  expect(violation.details.stderr).toContain("T01");

  const documentation = await tool.execute("test", { ...parameters, base: allowedHead,
    head: forbiddenHead, task: undefined }, undefined, undefined, { cwd: repo });
  expect(documentation.isError).toBe(true);
  expect(documentation.details.stderr).toContain("tests/test_accept.py");
});

function decisionRequest() {
  return {
    version: 1, kind: "decision", title: "Choose export storage",
    context: "Exports must remain downloadable for seven days.",
    question: "Use object storage or local disk?", blocking: true,
    intentBasis: [{
      source: "PRD", reference: "docs/features/export/prd.md#retention",
      relevance: "Requires seven-day download availability.",
    }],
    options: [
      {
        label: "Object storage", strengths: ["Survives worker replacement."],
        weaknesses: ["Adds a service dependency."],
        downstream: "Add bucket lifecycle configuration.",
      },
      {
        label: "Local disk", strengths: ["No external service."],
        weaknesses: ["Worker replacement loses exports."],
        downstream: "Pin downloads to the producing worker.",
      },
    ],
    recommendation: { option: "Object storage", rationale: "Preserves retention across worker replacement." },
    maintainability: "Bucket lifecycle rules avoid a custom cleanup scheduler.",
  };
}


test("developer request renders the decision and its consequential tradeoffs", async () => {
  const result = await requestTool.execute("test", requestTool.parameters.parse(decisionRequest()),
    undefined, undefined, { cwd: repo });
  expect(result.isError).toBeUndefined();
  expect(result.details.status).toBe("ok");
  expect(result.details.request.kind).toBe("decision");
  const markdown = result.content[0].text;
  expect(markdown).toContain("Use object storage or local disk?");
  expect(markdown).toContain("Adds a service dependency.");
  expect(markdown).toContain("Pin downloads to the producing worker.");
  expect(markdown).toContain("Preserves retention across worker replacement.");
  expect(markdown).toContain("Bucket lifecycle rules avoid a custom cleanup scheduler.");
  expect(markdown).toContain("docs/features/export/prd.md#retention");
});

test("developer request preserves context larger than the platform argv limit", async () => {
  const limit = spawnSync("getconf", ["ARG_MAX"], { encoding: "utf8" });
  if (limit.error || limit.status !== 0) throw limit.error ?? new Error(limit.stderr);
  const argumentLimit = Number(limit.stdout.trim());
  expect(Number.isSafeInteger(argumentLimit) && argumentLimit > 0).toBe(true);
  const request = decisionRequest();
  request.context = "Context start " + "a".repeat(argumentLimit + 1024) + " context end";
  const result = await requestTool.execute("test", request,
    undefined, undefined, { cwd: repo });
  expect(result.isError).toBeUndefined();
  expect(result.details.status).toBe("ok");
  expect(result.content[0].text).toContain(request.context);
});

test("developer request cancellation fails cleanly while stdin is pending", async () => {
  for (const alreadyAborted of [true, false]) {
    const controller = new AbortController();
    if (alreadyAborted) controller.abort();
    const request = decisionRequest();
    request.context = "a".repeat(1024 * 1024);
    const pending = requestTool.execute("test", request,
      controller.signal, undefined, { cwd: repo });
    if (!alreadyAborted) controller.abort();
    const result = await pending;
    expect(result.isError).toBe(true);
    expect(result.details.status).toBe("error");
    expect(result.details.exitCode).toBeNull();
    expect(result.details.stdout).toBe("");
  }
});

test("developer request rejects a decision without enough options", async () => {
  const request = decisionRequest();
  request.options = request.options.slice(0, 1);
  const result = await requestTool.execute("test", request,
    undefined, undefined, { cwd: repo });
  expect(result.isError).toBe(true);
  expect(result.details.status).toBe("error");
  expect(result.details.exitCode).not.toBe(0);
  expect(result.details.stderr).toContain("options");
  expect(result.details.message).toBe(result.details.stderr.trim());
  expect(result.content[0].text).toBe(result.details.message);
});

test("developer request treats null and empty optional values as absent", async () => {
  const request = {
    version: 1, kind: "input", title: "Supply retention duration",
    context: "The export PRD does not define retention.",
    question: "How long should exports remain downloadable?",
    blocking: false, needed: "Retention duration in days.",
    intentBasisUnavailableReason: "No approved retention requirement is available.",
  };
  const baseline = await requestTool.execute("test", requestTool.parameters.parse(request),
    undefined, undefined, { cwd: repo });
  expect(baseline.details.status).toBe("ok");
  for (const value of [null, "", [], {}]) {
    const fields = Object.fromEntries([
      "intentBasis", "options", "recommendation", "maintainability", "acceptance", "requiredAction",
    ].map(key => [key, value]));
    const result = await requestTool.execute("test", requestTool.parameters.parse({ ...request, ...fields }),
      undefined, undefined, { cwd: repo });
    expect(result.isError).toBeUndefined();
    expect(result.details.status).toBe("ok");
    expect(result.content[0].text).toBe(baseline.content[0].text);
  }
});

test("developer request schema rejects nonempty placeholders and malformed fields", () => {
  const request = decisionRequest();
  for (const fields of [
    { maintainability: ["not empty"] },
    { acceptance: [null] },
    { needed: [42] },
    { intentBasisUnavailableReason: { reason: "not empty" } },
    { options: [{ label: "Missing tradeoffs" }] },
    { recommendation: { option: "Object storage", rationale: 42 } },
    { intentBasis: [{ source: "PRD", reference: "retention", relevance: false }] },
    { blocking: "true" },
    { unexpected: true },
  ]) {
    expect(requestTool.parameters.safeParse({ ...request, ...fields }).success).toBe(false);
  }
});

function seedSessions() {
  const sessions = join(workspace, "sessions");
  const folder = join(sessions, "-work-app", "2026-09-20_a");
  mkdirSync(folder, { recursive: true });
  const lines = entries => entries.map(entry => JSON.stringify(entry)).join("\n") + "\n";
  writeFileSync(`${folder}.jsonl`, lines([
    { type: "session", cwd: "/work/app" },
    { type: "message", message: { role: "assistant", content: [{ type: "toolCall", name: "task",
      arguments: { tasks: [{ name: "Rev1", agent: "review-skill-agent", task: "t" }] } }] } },
  ]));
  writeFileSync(join(folder, "Rev1.jsonl"), lines([
    { type: "session_init", agent: "review-skill-agent", timestamp: "2026-09-20T01:00:00Z" },
    { type: "message", message: { role: "assistant", content: [{ type: "text", text: "Friction: slow" }] } },
  ]));
  return sessions;
}

test("agent-run collection treats null and empty optional values as absent", async () => {
  const sessions = seedSessions();
  for (const fields of [{}, { until: null, project: null }, { until: "", project: "" }]) {
    const result = await runsTool.execute("test", runsTool.parameters.parse(
      { agent: "review-skill-agent", since: "2026-09-01", sessions, ...fields }),
      undefined, undefined, { cwd: repo });
    expect(result.isError).toBeUndefined();
    expect(result.details.status).toBe("ok");
    const [run] = result.details.report.runs;
    expect(result.details.report.runs).toHaveLength(1);
    expect(run.run).toBe("Rev1");
    expect(run.parent.dispatchLine).toBe(2);
    expect(run.friction.map(item => item.text)).toEqual(["slow"]);
  }
  const scoped = await runsTool.execute("test",
    { agent: "review-skill-agent", since: "2026-09-01", project: "/work/other", sessions },
    undefined, undefined, { cwd: repo });
  expect(scoped.details.report.runs).toEqual([]);
});

test("agent-run collection reports collector errors and rejects unknown fields", async () => {
  const sessions = seedSessions();
  const result = await runsTool.execute("test", { agent: "task", since: "2026-09-01", sessions },
    undefined, undefined, { cwd: repo });
  expect(result.isError).toBe(true);
  expect(result.details.exitCode).toBe(1);
  expect(result.details.message).toContain("unknown Playbook agent 'task'");
  const empty = await runsTool.execute("test", { agent: "review-skill-agent", since: "" },
    undefined, undefined, { cwd: repo });
  expect(empty.details.message).toBe("Agent-run collection requires non-empty agent and since.");
  expect(runsTool.parameters.safeParse(
    { agent: "review-skill-agent", since: "2026-09-01", mode: "json" }).success).toBe(false);
});
