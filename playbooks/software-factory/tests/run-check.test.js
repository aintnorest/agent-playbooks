import { test, expect } from "bun:test";
import * as zod from "@oh-my-pi/omptype/zod";
import { spawnSync } from "node:child_process";
import { chmodSync, existsSync, mkdtempSync, mkdirSync, readFileSync, rmSync, unlinkSync, writeFileSync } from "node:fs";
import { tmpdir } from "node:os";
import { join } from "node:path";
import softwareFactory from "../omp-extension.ts";

let tool;
softwareFactory({ zod, registerTool: definition => { if (definition.name === "run_check") tool = definition; }, on() {}, registerCommand() {} });

for (const scenario of ["abort", "outer deadline"]) {
  test(`run_check kills the command process group on ${scenario}`, async () => {
    const cwd = mkdtempSync(join(tmpdir(), "playbook-cancel-"));
    const originalPath = process.env.PATH;
    const ready = join(cwd, "ready");
    const survivor = join(cwd, "survived");
    const controller = new AbortController();
    let result;
    try {
      if (scenario === "outer deadline") {
        // A stalled runtime ignores the inner deadline; exercise the real outer guard.
        const python = spawnSync("python3", ["-c", "import sys; print(sys.executable)"], { encoding: "utf8" }).stdout.trim();
        const bin = join(cwd, "bin");
        mkdirSync(bin);
        const shim = join(bin, "python3");
        writeFileSync(shim, `#!${python}\nimport os,sys\nargs=sys.argv[1:]\nargs[args.index('--timeout')+1]='30'\nos.execv(sys.executable,[sys.executable,*args])\n`);
        chmodSync(shim, 0o755);
        process.env.PATH = `${bin}:${originalPath}`;
      }
      const delay = scenario === "abort" ? 1 : 6;
      const pending = tool.execute("cancel", { command: `(sleep ${delay}; touch '${survivor}') & printf ready > '${ready}'; sleep 30`,
        cwd, timeout: scenario === "abort" ? 30 : 0.05 }, controller.signal, undefined, { cwd });
      const deadline = Date.now() + 3000;
      while (!existsSync(ready) && Date.now() < deadline) await Bun.sleep(10);
      expect(existsSync(ready)).toBe(true);
      if (scenario === "abort") controller.abort();
      result = await pending;
      expect(result.isError).toBe(true);
      expect(result.details.message).toContain(scenario === "abort" ? "aborted" : "deadline");
      expect(typeof result.details.logPath, JSON.stringify(result.details)).toBe("string");
      expect(readFileSync(result.details.logPath, "utf8")).toContain("process group killed");
      await Bun.sleep(1200);
      expect(existsSync(survivor)).toBe(false);
    } finally {
      controller.abort();
      process.env.PATH = originalPath;
      if (typeof result?.details.logPath === "string") unlinkSync(result.details.logPath);
      rmSync(cwd, { recursive: true, force: true });
    }
  }, 12_000);
}

test("run_check returns status and log for a single line exceeding transport capacity", async () => {
  const cwd = mkdtempSync(join(tmpdir(), "playbook-giant-log-"));
  let result;
  try {
    result = await tool.execute("large", { command: "python3 -c 'import sys; sys.stdout.write(\"x\"*(17*1024*1024)+\"END\")'",
      cwd, timeout: 10 }, undefined, undefined, { cwd });
    expect(result.isError).toBeUndefined();
    expect(result.details.status).toBe("passed");
    expect(result.details.exitCode).toBe(0);
    expect(Buffer.byteLength(result.details.tail)).toBe(65536);
    expect(result.details.tail.endsWith("END")).toBe(true);
    expect(readFileSync(result.details.logPath).byteLength).toBe(17 * 1024 * 1024 + 3);
  } finally {
    if (result?.details.logPath) unlinkSync(result.details.logPath);
    rmSync(cwd, { recursive: true, force: true });
  }
});
