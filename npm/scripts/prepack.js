#!/usr/bin/env node
// Copies the Python source needed for `pip install <bundled-source>` into
// npm/pysrc/ so it can be shipped inside the npm tarball via the `files`
// field. Runs automatically as the "prepack" lifecycle script for both
// `npm pack` and `npm publish` — nothing to do by hand.
//
// Once jacky-cli is published to PyPI, this whole prepack step (and the
// pysrc bundling in package.json's `files`) can be deleted, and
// bin/jacky-npm.js can switch to `pip install jacky-cli==<version>`.
'use strict';

const fs = require('fs');
const path = require('path');

const NPM_DIR = path.resolve(__dirname, '..');
const REPO_ROOT = path.resolve(NPM_DIR, '..');
const DEST = path.join(NPM_DIR, 'pysrc');

// Directories from [tool.setuptools.packages.find] include=, plus the
// data-files / package-data roots (locales, optional-mcps, gateway/assets,
// plugins/**/dashboard/dist) and the packaging metadata pip needs
// (pyproject.toml, setup.py, README, LICENSE, MANIFEST.in).
const DIR_ENTRIES = [
  'agent',
  'tools',
  'jacky_cli',
  'gateway',
  'tui_gateway',
  'cron',
  'acp_adapter',
  'plugins',
  'providers',
  'locales',
  'optional-mcps',
  'skills',
  'optional-skills',
];

const FILE_ENTRIES = [
  'pyproject.toml',
  'setup.py',
  'MANIFEST.in',
  'README.md',
  'LICENSE',
];

// Anything matching these directory names is skipped everywhere in the
// tree (build artifacts / VCS / caches / vendored JS deps — never needed
// for `pip install`, and photon's sidecar node_modules alone is ~144MB).
const EXCLUDE_DIR_NAMES = new Set([
  'node_modules',
  '__pycache__',
  '.git',
  '.venv',
  'venv',
  '.pytest_cache',
  '.pytest-cache',
  '.mypy_cache',
  '.ruff_cache',
]);

function shouldSkip(srcPath) {
  const base = path.basename(srcPath);
  return EXCLUDE_DIR_NAMES.has(base);
}

function copyFiltered(src, dest) {
  fs.cpSync(src, dest, {
    recursive: true,
    dereference: true,
    filter: (srcPath) => !shouldSkip(srcPath),
  });
}

function main() {
  fs.rmSync(DEST, { recursive: true, force: true });
  fs.mkdirSync(DEST, { recursive: true });

  for (const dir of DIR_ENTRIES) {
    const src = path.join(REPO_ROOT, dir);
    if (!fs.existsSync(src)) continue;
    copyFiltered(src, path.join(DEST, dir));
  }

  for (const file of FILE_ENTRIES) {
    const src = path.join(REPO_ROOT, file);
    if (!fs.existsSync(src)) continue;
    fs.copyFileSync(src, path.join(DEST, file));
  }

  console.log(`[prepack] bundled Python source into ${path.relative(NPM_DIR, DEST)}/`);
}

main();
