#!/usr/bin/env node
// Jacky CLI npm shim.
//
// npm can't run Python directly, so this script is the thing that actually
// lands on PATH as `jacky`. It makes sure a real Python (3.11+) install of
// jacky-cli exists in a persistent venv under the user's home directory,
// then execs straight into that venv's own `jacky` console-script,
// forwarding argv and exit code untouched.
//
// No external npm dependencies — only Node's built-ins.
'use strict';

const { spawnSync } = require('child_process');
const fs = require('fs');
const os = require('os');
const path = require('path');

const PKG = require('../package.json');
const PKG_VERSION = PKG.version;

const IS_WINDOWS = process.platform === 'win32';

// Must match jacky_cli/jacky_constants.py's _get_platform_default_jacky_home()
// on Windows: %LOCALAPPDATA%\jacky (falling back to ~/AppData/Local/jacky if
// LOCALAPPDATA isn't set). If these two ever diverge, anything the npm
// shim's venv writes (skills/config/sessions) becomes invisible to the
// actual Python app. POSIX stays ~/.jacky, unchanged.
function getJackyHome() {
  if (IS_WINDOWS) {
    const localAppData = process.env.LOCALAPPDATA || path.join(os.homedir(), 'AppData', 'Local');
    return path.join(localAppData, 'jacky');
  }
  return path.join(os.homedir(), '.jacky');
}

const JACKY_HOME = getJackyHome();
const VENV_DIR = path.join(JACKY_HOME, 'venv');
const MARKER_FILE = path.join(VENV_DIR, '.jacky-npm-version');
const VENV_BIN_DIR = path.join(VENV_DIR, IS_WINDOWS ? 'Scripts' : 'bin');
const VENV_PYTHON = path.join(VENV_BIN_DIR, IS_WINDOWS ? 'python.exe' : 'python');
const VENV_JACKY = path.join(VENV_BIN_DIR, IS_WINDOWS ? 'jacky.exe' : 'jacky');

// jacky-cli is now published to PyPI (pypi.org/project/jacky-cli/), so this
// shim installs the exact matching version from there instead of bundling a
// private copy of the Python source in the npm tarball. The bundled-source
// approach (npm/pysrc/, npm/scripts/prepack.js) is kept around as dead code
// for now rather than deleted outright, but is no longer used on this path —
// it silently went stale relative to the real source tree the one time it
// mattered (a version-drift fix landed in jacky_cli/__init__.py, PyPI got
// republished, but the bundled pysrc/ copy and the npm package were never
// re-synced), so a fresh, un-cacheable pip install straight from PyPI is the
// version of this that can't drift.
const PYPI_SPEC = `jacky-cli==${PKG_VERSION}`;

const MIN_PY_MAJOR = 3;
const MIN_PY_MINOR = 11;
// KEEP IN SYNC with pyproject.toml's `requires-python = ">=3.11,<3.14"`.
// MAX_PY_MINOR is the last minor version still accepted (i.e. the upper
// bound is exclusive of MAX_PY_MINOR + 1). No single-source-of-truth read
// is done here (this script must run before any Python is available), so
// this is a hardcoded mirror of the pyproject.toml bound.
const MAX_PY_MINOR = 13;

function log(msg) {
  process.stderr.write(`[jacky] ${msg}\n`);
}

function fail(msg) {
  process.stderr.write(`\n[jacky] ERROR: ${msg}\n`);
}

// --- Python discovery -------------------------------------------------

function tryVersion(cmd, args) {
  const result = spawnSync(cmd, [...args, '--version'], { encoding: 'utf8' });
  if (result.error || result.status !== 0) return null;
  const out = `${result.stdout || ''}${result.stderr || ''}`;
  const m = out.match(/Python (\d+)\.(\d+)\.(\d+)/);
  if (!m) return null;
  const major = parseInt(m[1], 10);
  const minor = parseInt(m[2], 10);
  const atLeastMin = major > MIN_PY_MAJOR || (major === MIN_PY_MAJOR && minor >= MIN_PY_MINOR);
  const atMostMax = major < MIN_PY_MAJOR || (major === MIN_PY_MAJOR && minor <= MAX_PY_MINOR);
  if (atLeastMin && atMostMax) {
    return { cmd, args, major, minor };
  }
  return null;
}

function findPython() {
  const candidates = IS_WINDOWS
    ? [
        // Prefer explicit version pins on Windows so the `py` launcher
        // can't hand us an out-of-range interpreter (e.g. `py -3` resolving
        // to 3.14 when 3.14 is installed alongside an in-range version).
        ['py', ['-3.13']],
        ['py', ['-3.12']],
        ['py', ['-3.11']],
        ['py', ['-3']],
        ['python', []],
        ['python3', []],
      ]
    : [
        ['python3', []],
        ['python', []],
      ];
  for (const [cmd, args] of candidates) {
    const found = tryVersion(cmd, args);
    if (found) return found;
  }
  return null;
}

function printNoPythonError() {
  fail(
    `Python ${MIN_PY_MAJOR}.${MIN_PY_MINOR}-${MIN_PY_MAJOR}.${MAX_PY_MINOR} is required to run Jacky, but no ` +
      `matching interpreter was found on your PATH (only a version outside that range, or nothing at all).`
  );
  process.stderr.write(`
Install a Python between ${MIN_PY_MAJOR}.${MIN_PY_MINOR} and ${MIN_PY_MAJOR}.${MAX_PY_MINOR} inclusive, then re-run \`jacky\` (or \`npm install -g ${PKG.name}\` again):

  * Official installers:      https://www.python.org/downloads/
  * Debian/Ubuntu:            sudo apt update && sudo apt install python3.11 python3.11-venv
  * Fedora:                   sudo dnf install python3.11
  * macOS (Homebrew):         brew install python@3.11
  * Windows:                  winget install Python.Python.3.11
                               (or the Microsoft Store "Python 3.11" package)

After installing, make sure \`python3\` (or \`py -3\` on Windows) resolves to
the new interpreter in a fresh terminal, then try again.
`);
}

// --- venv setup ---------------------------------------------------------

function readMarker() {
  try {
    return fs.readFileSync(MARKER_FILE, 'utf8').trim();
  } catch {
    return null;
  }
}

function setupIsCurrent() {
  if (!fs.existsSync(VENV_JACKY)) return false;
  return readMarker() === PKG_VERSION;
}

function createVenv(python) {
  log(`creating virtual environment at ${VENV_DIR} ...`);
  fs.mkdirSync(JACKY_HOME, { recursive: true });
  const result = spawnSync(python.cmd, [...python.args, '-m', 'venv', VENV_DIR], {
    stdio: 'inherit',
  });
  if (result.error || result.status !== 0) {
    fail(`Failed to create the Python virtual environment at ${VENV_DIR}.`);
    process.stderr.write(`
This usually means the venv module is missing (on Debian/Ubuntu install it
with \`sudo apt install python3-venv\` / \`python3.11-venv\`), or that
${VENV_DIR}'s parent directory isn't writable. Fix the issue above and
re-run \`jacky\`.
`);
    return false;
  }
  return true;
}

function pipInstall() {
  log(`installing ${PYPI_SPEC} from PyPI into the virtual environment (this can take a minute) ...`);
  const result = spawnSync(
    VENV_PYTHON,
    ['-m', 'pip', 'install', '--upgrade', '--quiet', '--disable-pip-version-check', '--no-cache-dir', PYPI_SPEC],
    { stdio: 'inherit' }
  );
  if (result.error || result.status !== 0) {
    fail('pip install failed. See the output above for details.');
    return false;
  }
  return true;
}

function runSetup() {
  const python = findPython();
  if (!python) {
    printNoPythonError();
    return false;
  }
  log(`using ${python.cmd} (Python ${python.major}.${python.minor})`);

  if (!fs.existsSync(VENV_JACKY)) {
    // Wipe any half-created venv from a previous failed attempt before
    // trying again, so venv creation doesn't error on an existing dir.
    if (fs.existsSync(VENV_DIR) && !fs.existsSync(VENV_PYTHON)) {
      fs.rmSync(VENV_DIR, { recursive: true, force: true });
    }
    if (!fs.existsSync(VENV_DIR) && !createVenv(python)) return false;
  }

  if (!pipInstall()) return false;

  fs.writeFileSync(MARKER_FILE, `${PKG_VERSION}\n`);
  log(`jacky-cli ${PKG_VERSION} is ready.`);
  return true;
}

// --- exec into the venv's jacky -----------------------------------------

function execJacky(argv) {
  const result = spawnSync(VENV_JACKY, argv, { stdio: 'inherit' });
  if (result.error) {
    fail(`Failed to run ${VENV_JACKY}: ${result.error.message}`);
    process.exit(1);
  }
  // Forward the child's exit code (or its signal, if it was killed by one).
  if (result.signal) {
    process.kill(process.pid, result.signal);
    return;
  }
  process.exit(result.status === null ? 1 : result.status);
}

// --- entry point ----------------------------------------------------

function main() {
  const isPostinstall = process.argv.includes('--jacky-npm-setup');

  if (isPostinstall) {
    // Called from the "postinstall" npm lifecycle script. Only set things
    // up; there's no user command to forward yet.
    const ok = runSetup();
    process.exit(ok ? 0 : 1);
  }

  // Cheap self-heal check on every normal invocation: if postinstall was
  // skipped (e.g. `npm install --ignore-scripts`) or the venv was deleted,
  // set it up now instead of failing.
  if (!setupIsCurrent()) {
    if (!runSetup()) {
      process.exit(1);
    }
  }

  execJacky(process.argv.slice(2));
}

main();
