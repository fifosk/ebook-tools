import fs from 'node:fs';
import path from 'node:path';
import type { ServerOptions as HttpsServerOptions } from 'node:https';

import react from '@vitejs/plugin-react';
import { defineConfig, loadEnv } from 'vite';

export default defineConfig(({ mode }) => {
  console.log("[DEBUG] config running, mode =", mode);

  // Load env vars from the same dir as this config file
  const env = loadEnv(mode, __dirname, "");
  const isExportBuild = mode === "export";

  console.log("[DEBUG] loaded env via loadEnv:", {
    https: env.VITE_DEV_HTTPS,
    cert: env.VITE_DEV_HTTPS_CERT,
    key: env.VITE_DEV_HTTPS_KEY,
    ca: env.VITE_DEV_HTTPS_CA
  });

  const httpsOptions = resolveHttpsOptions(env);

  const buildConfig = {
    // Silence chunk size warnings; the app bundles many shared components by design.
    chunkSizeWarningLimit: 1500,
    ...(isExportBuild
      ? {
          outDir: "export-dist",
          rollupOptions: {
            input: path.resolve(__dirname, "export.html")
          }
        }
      : {})
  };

  return {
    envDir: __dirname,
    base: isExportBuild ? "./" : "/",

    plugins: [react()],

    build: buildConfig,

    server: {
      host: true,
      https: httpsOptions
    },

    preview: {
      host: true,
      https: httpsOptions
    },

    resolve: {
      extensions: [
        '.ts', '.tsx',
        '.mts', '.cts',
        '.js', '.mjs',
        '.jsx', '.cjs',
        '.json'
      ]
    }
  };
});

function resolveHttpsOptions(env: Record<string, string>): HttpsServerOptions | undefined {
  console.log("[DEBUG] resolveHttpsOptions env:", env);

  const explicit = parseBooleanFlag(env.VITE_DEV_HTTPS);
  const certPath = env.VITE_DEV_HTTPS_CERT;
  const keyPath = env.VITE_DEV_HTTPS_KEY;

  const shouldEnable = explicit ?? Boolean(certPath && keyPath);
  if (!shouldEnable) {
    console.log("[DEBUG] HTTPS disabled.");
    return undefined;
  }

  const certFile = resolveFilePath(certPath, 'VITE_DEV_HTTPS_CERT');
  const keyFile = resolveFilePath(keyPath, 'VITE_DEV_HTTPS_KEY');

  const config: HttpsServerOptions = {
    cert: fs.readFileSync(certFile),
    key: fs.readFileSync(keyFile)
  };

  if (env.VITE_DEV_HTTPS_CA) {
    const caFile = resolveFilePath(env.VITE_DEV_HTTPS_CA, 'VITE_DEV_HTTPS_CA');
    config.ca = fs.readFileSync(caFile);
  }

  return config;
}

function parseBooleanFlag(value: string | undefined): boolean | undefined {
  if (!value) return undefined;
  const val = value.trim().toLowerCase();
  if (['1', 'true', 'yes', 'on'].includes(val)) return true;
  if (['0', 'false', 'no', 'off'].includes(val)) return false;
  throw new Error(`Invalid boolean '${value}'`);
}

function resolveFilePath(target: string, envKey: string): string {
  const resolved = path.resolve(target);
  if (!fs.existsSync(resolved)) {
    throw new Error(`${envKey} -> file does not exist: ${resolved}`);
  }
  return resolved;
}
