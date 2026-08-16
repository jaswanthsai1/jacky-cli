/**
 * Window text size (zoom).
 *
 * The main process owns the zoom level and persists it (see electron/zoom.ts
 * for the scale). The renderer only mirrors the current percent for the
 * settings UI: preset clicks go to the main process over IPC, and every
 * change comes back through onChanged, including ones made with the
 * Ctrl/Cmd +/-/0 shortcuts or the View menu, so the UI never drifts.
 */

import { atom } from 'nanostores'

export const $zoomPercent = atom<number>(100)

export function setZoomPercent(percent: number): void {
  window.jackyDesktop?.zoom?.setPercent(percent)
}

if (typeof window !== 'undefined' && window.jackyDesktop?.zoom) {
  void window.jackyDesktop.zoom.get().then(({ percent }) => $zoomPercent.set(percent))
  window.jackyDesktop.zoom.onChanged(({ percent }) => $zoomPercent.set(percent))
}
