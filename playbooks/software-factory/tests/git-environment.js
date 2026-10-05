// Git hooks export repository overrides that otherwise redirect temporary fixtures.
for (const key of Object.keys(process.env)) {
  if (key.startsWith("GIT_")) delete process.env[key];
}
