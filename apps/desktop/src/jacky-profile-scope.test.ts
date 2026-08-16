import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'

import {
  checkJackyUpdate,
  getActionStatus,
  getStatus,
  restartGateway,
  setApiRequestProfile,
  updateJacky
} from './jacky'

// Contract: every backend-targeted action helper must carry the active gateway
// profile, so a multi-profile / global-remote user's restart, status poll, and
// update hit the backend they're actually on — not the primary/default. The
// System-panel "restart does nothing" bug was these helpers dropping it.
describe('backend action helpers are profile-scoped', () => {
  const api = vi.fn(async (_req: { path: string; profile?: string }) => ({}) as never)

  beforeEach(() => {
    ;(window as { jackyDesktop?: unknown }).jackyDesktop = { api }
    api.mockClear()
  })

  afterEach(() => {
    setApiRequestProfile(null)
    delete (window as { jackyDesktop?: unknown }).jackyDesktop
  })

  const lastProfile = () => api.mock.calls.at(-1)?.[0].profile

  it('omits profile when none is active (single-profile users unaffected)', () => {
    void getStatus()
    expect(lastProfile()).toBeUndefined()
  })

  it('forwards the active profile to every backend action', () => {
    setApiRequestProfile('coder')

    void getStatus()
    void restartGateway()
    void updateJacky()
    void checkJackyUpdate()
    void getActionStatus('gateway-restart')

    for (const call of api.mock.calls) {
      expect(call[0].profile).toBe('coder')
    }
  })
})
