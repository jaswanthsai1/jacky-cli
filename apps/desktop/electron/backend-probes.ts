/**
 * backend-probes.ts
 *
 * Cheap "does this candidate backend actually work" checks used by
 * resolveJackyBackend (main.ts). The resolver walks a ladder of
 * candidates -- bootstrap marker, `jacky` on PATH, system Python with
 * jacky_cli installed -- and historically returned the first candidate
 * whose binary existed on disk. That assumption breaks when a user has
 * a pre-installed Python 3.11-3.13 (so findSystemPython() returns a
 * path) but no jacky_cli in its site-packages: the resolver hands back
 * a backend the spawn step can't actually run, and the user gets a
 * dead-on-arrival "ModuleNotFoundError: No module named 'jacky_cli'"
 * instead of the first-launch installer.
 *
 * These probes give the resolver a way to verify a candidate before
 * trusting it. Failure (non-zero exit, exception, timeout) means "skip
 * this rung, try the next one"; success means "spawn this for real."
 * Falling off the bottom of the ladder lands on the bootstrap-needed
 * sentinel, which is exactly what we want when nothing pre-existing
 * actually works.
 *
 * Both probes are deliberately fast and forgiving:
 *   - 5s timeout (a hung interpreter beats forever, but we still give
 *     slow disks / cold caches room to breathe)
 *   - stdio ignored (we only care about exit code; stdout/stderr are
 *     not surfaced to the user, just to recentJackyLog for forensics
 *     via the caller's catch block if it chooses)
 *   - any throw -> false (never propagate -- resolver wants a boolean)
 *
 * Kept in a standalone ts module so it can be unit-tested with
 * `node --test` without dragging in the electron runtime (same pattern
 * as bootstrap-platform.ts and hardening.ts).
 */

import { execFileSync } from 'node:child_process'

const PROBE_TIMEOUT_MS = 5000

/**
 * Return the Python snippet used to verify Jacky can import far enough to
 * launch the CLI. Kept exported for tests so dependency regressions are
 * caught without needing a real broken venv fixture.
 *
 * @returns {string}
 */
function jackyRuntimeImportProbe() {
  return 'import yaml; import dotenv; import jacky_cli.config'
}

/**
 * Return true iff the Jacky runtime import probe exits 0.
 *
 * Used to gate the "fallback to system Python with jacky_cli installed"
 * rung of resolveJackyBackend. Without this, a system Python 3.11-3.13
 * registered in PEP 514 makes findSystemPython() succeed regardless of
 * whether jacky_cli has actually been pip-installed into its
 * site-packages -- and the resolver returns a backend that immediately
 * dies on spawn.
 *
 * The probe intentionally imports jacky_cli.config, not just the top-level
 * package: a broken/empty Windows launcher venv can still see the source tree
 * through PYTHONPATH but lack PyYAML, then die on the first real CLI import.
 *
 * @param {string} pythonPath - Absolute path to a python.exe / python.
 * @param {object} [opts.env] - Additional environment for the probe.
 * @returns {boolean}
 */
function canImportJackyCli(pythonPath: string, opts: { env?: Record<string, string> } = {}) {
  if (!pythonPath) {
    return false
  }

  try {
    execFileSync(pythonPath, ['-c', jackyRuntimeImportProbe()], {
      env: { ...process.env, ...(opts.env || {}) },
      stdio: 'ignore',
      timeout: PROBE_TIMEOUT_MS,
      windowsHide: true
    })

    return true
  } catch {
    return false
  }
}

/**
 * Return true iff `<jackyCommand> --version` exits 0.
 *
 * Used to gate the "existing `jacky` on PATH" rung. Without this, a
 * stale jacky.cmd shim left behind by an uninstalled pip install (or
 * a half-built venv whose `jacky` entry-point points at a deleted
 * Python) survives findOnPath() and gets selected as the backend.
 *
 * We intentionally avoid invoking the command with the dashboard args
 * here -- `--version` is the cheapest "is this binary alive" smoke
 * test that every jacky_cli entry-point has supported since 0.1.
 *
 * @param {string} jackyCommand - Resolved absolute path to a jacky
 *   executable (or an interpreter+script wrapper).
 * @param {boolean} [opts.shell] - Whether to run through a shell. For
 *   .cmd/.bat shims on Windows execFileSync needs shell:true to find
 *   the cmd interpreter; mirrors the same flag isCommandScript() drives
 *   in resolveJackyBackend.
 * @returns {boolean}
 */
function verifyJackyCli(jackyCommand: string, opts?: { shell?: boolean }) {
  if (!jackyCommand) {
    return false
  }

  try {
    execFileSync(jackyCommand, ['--version'], {
      stdio: 'ignore',
      timeout: PROBE_TIMEOUT_MS,
      shell: Boolean(opts?.shell),
      windowsHide: true
    })

    return true
  } catch {
    return false
  }
}

export { canImportJackyCli, jackyRuntimeImportProbe, PROBE_TIMEOUT_MS, verifyJackyCli }
