import { defineConfig } from "@hey-api/openapi-ts";

export default defineConfig({
  input: "./openapi.json",
  output: {
    path: "./src/lib/api/generated",
    postProcess: ["prettier"],
  },
  plugins: [
    { name: "@hey-api/client-fetch", runtimeConfigPath: "./src/lib/api/client.ts" },
    "@hey-api/sdk",
    "@hey-api/typescript",
    "@tanstack/react-query",
  ],
});
