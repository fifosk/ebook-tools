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
  const serverPort = parsePort(env.VITE_DEV_PORT) ?? 5173;
  const hmrHost = env.VITE_DEV_HMR_HOST;
  const hmrConfig = hmrHost ? { host: hmrHost } : undefined;

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
      port: serverPort,
      strictPort: true,
      hmr: hmrConfig,
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

  if (!certPath || !keyPath) {
    console.warn("[WARN] HTTPS requested but VITE_DEV_HTTPS_CERT or VITE_DEV_HTTPS_KEY is missing; falling back to HTTP.");
    return undefined;
  }

  const certFile = resolveFilePath(certPath, 'VITE_DEV_HTTPS_CERT', true);
  const keyFile = resolveFilePath(keyPath, 'VITE_DEV_HTTPS_KEY', true);
  if (!certFile || !keyFile) {
    return undefined;
  }

  const config: HttpsServerOptions = {
    cert: fs.readFileSync(certFile),
    key: fs.readFileSync(keyFile)
  };

  if (env.VITE_DEV_HTTPS_CA) {
    const caFile = resolveFilePath(env.VITE_DEV_HTTPS_CA, 'VITE_DEV_HTTPS_CA', true);
    if (caFile) {
      config.ca = fs.readFileSync(caFile);
    }
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

function parsePort(value: string | undefined): number | undefined {
  if (!value) return undefined;
  const parsed = Number.parseInt(value, 10);
  return Number.isFinite(parsed) ? parsed : undefined;
}

function resolveFilePath(target: string, envKey: string, allowMissing = false): string | undefined {
  const resolved = path.resolve(target);
  if (!fs.existsSync(resolved)) {
    if (allowMissing) {
      console.warn(`[WARN] ${envKey} -> file does not exist: ${resolved}. HTTPS disabled.`);
      return undefined;
    }
    throw new Error(`${envKey} -> file does not exist: ${resolved}`);
  }
  return resolved;
}
