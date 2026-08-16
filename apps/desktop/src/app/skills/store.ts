import { Codecs, persistentAtom } from '@/lib/persisted'

// Per-view sort direction for the Capabilities lists — persisted so each tab
// remembers most/least-used across navigations and restarts.
export const $skillsSortDesc = persistentAtom('jacky.desktop.capabilities.skillsSortDesc', true, Codecs.bool)
export const $toolsetsSortDesc = persistentAtom('jacky.desktop.capabilities.toolsetsSortDesc', true, Codecs.bool)
