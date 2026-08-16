import { contextBridge, ipcRenderer, webUtils } from 'electron'

contextBridge.exposeInMainWorld('jackyDesktop', {
  getConnection: profile => ipcRenderer.invoke('jacky:connection', profile),
  revalidateConnection: () => ipcRenderer.invoke('jacky:connection:revalidate'),
  touchBackend: profile => ipcRenderer.invoke('jacky:backend:touch', profile),
  getGatewayWsUrl: profile => ipcRenderer.invoke('jacky:gateway:ws-url', profile),
  openSessionWindow: (sessionId, opts) => ipcRenderer.invoke('jacky:window:openSession', sessionId, opts),
  openNewSessionWindow: () => ipcRenderer.invoke('jacky:window:openNewSession'),
  petOverlay: {
    // Main renderer → main process: window lifecycle + drag. `request` is
    // `{ bounds, screen }`; resolves with the screen bounds it actually used.
    open: request => ipcRenderer.invoke('jacky:pet-overlay:open', request),
    close: () => ipcRenderer.invoke('jacky:pet-overlay:close'),
    setBounds: bounds => ipcRenderer.send('jacky:pet-overlay:set-bounds', bounds),
    setIgnoreMouse: ignore => ipcRenderer.send('jacky:pet-overlay:ignore-mouse', ignore),
    // Flip the overlay focusable (and focus it) while the composer needs keys.
    setFocusable: focusable => ipcRenderer.send('jacky:pet-overlay:set-focusable', focusable),
    // Main renderer → overlay (forwarded by main): push the latest pet state.
    pushState: payload => ipcRenderer.send('jacky:pet-overlay:state', payload),
    // Overlay → main renderer (forwarded by main): pop back in / composer submit.
    control: payload => ipcRenderer.send('jacky:pet-overlay:control', payload),
    // Overlay subscribes to state pushes.
    onState: callback => {
      const listener = (_event, payload) => callback(payload)
      ipcRenderer.on('jacky:pet-overlay:state', listener)

      return () => ipcRenderer.removeListener('jacky:pet-overlay:state', listener)
    },
    // Main renderer subscribes to overlay control messages.
    onControl: callback => {
      const listener = (_event, payload) => callback(payload)
      ipcRenderer.on('jacky:pet-overlay:control', listener)

      return () => ipcRenderer.removeListener('jacky:pet-overlay:control', listener)
    }
  },
  getBootProgress: () => ipcRenderer.invoke('jacky:boot-progress:get'),
  getConnectionConfig: profile => ipcRenderer.invoke('jacky:connection-config:get', profile),
  saveConnectionConfig: payload => ipcRenderer.invoke('jacky:connection-config:save', payload),
  applyConnectionConfig: payload => ipcRenderer.invoke('jacky:connection-config:apply', payload),
  testConnectionConfig: payload => ipcRenderer.invoke('jacky:connection-config:test', payload),
  probeConnectionConfig: remoteUrl => ipcRenderer.invoke('jacky:connection-config:probe', remoteUrl),
  oauthLoginConnectionConfig: remoteUrl => ipcRenderer.invoke('jacky:connection-config:oauth-login', remoteUrl),
  oauthLogoutConnectionConfig: remoteUrl => ipcRenderer.invoke('jacky:connection-config:oauth-logout', remoteUrl),
  // Jacky Cloud: one portal login powers discovery + silent per-agent sign-in
  // (cloud-auto-discovery Phase 3).
  cloud: {
    status: () => ipcRenderer.invoke('jacky:cloud:status'),
    login: () => ipcRenderer.invoke('jacky:cloud:login'),
    logout: () => ipcRenderer.invoke('jacky:cloud:logout'),
    discover: org => ipcRenderer.invoke('jacky:cloud:discover', org),
    agentSignIn: dashboardUrl => ipcRenderer.invoke('jacky:cloud:agent-sign-in', dashboardUrl)
  },
  profile: {
    get: () => ipcRenderer.invoke('jacky:profile:get'),
    set: name => ipcRenderer.invoke('jacky:profile:set', name)
  },
  api: request => ipcRenderer.invoke('jacky:api', request),
  notify: payload => ipcRenderer.invoke('jacky:notify', payload),
  requestMicrophoneAccess: () => ipcRenderer.invoke('jacky:requestMicrophoneAccess'),
  readFileDataUrl: filePath => ipcRenderer.invoke('jacky:readFileDataUrl', filePath),
  readFileText: filePath => ipcRenderer.invoke('jacky:readFileText', filePath),
  selectPaths: options => ipcRenderer.invoke('jacky:selectPaths', options),
  writeClipboard: text => ipcRenderer.invoke('jacky:writeClipboard', text),
  saveImageFromUrl: url => ipcRenderer.invoke('jacky:saveImageFromUrl', url),
  saveImageBuffer: (data, ext) => ipcRenderer.invoke('jacky:saveImageBuffer', { data, ext }),
  saveClipboardImage: () => ipcRenderer.invoke('jacky:saveClipboardImage'),
  getPathForFile: file => {
    try {
      return webUtils.getPathForFile(file) || ''
    } catch {
      return ''
    }
  },
  normalizePreviewTarget: (target, baseDir) => ipcRenderer.invoke('jacky:normalizePreviewTarget', target, baseDir),
  watchPreviewFile: url => ipcRenderer.invoke('jacky:watchPreviewFile', url),
  stopPreviewFileWatch: id => ipcRenderer.invoke('jacky:stopPreviewFileWatch', id),
  setTitleBarTheme: payload => ipcRenderer.send('jacky:titlebar-theme', payload),
  setNativeTheme: mode => ipcRenderer.send('jacky:native-theme', mode),
  setTranslucency: payload => ipcRenderer.send('jacky:translucency', payload),
  setPreviewShortcutActive: active => ipcRenderer.send('jacky:previewShortcutActive', Boolean(active)),
  openExternal: url => ipcRenderer.invoke('jacky:openExternal', url),
  openPreviewInBrowser: url => ipcRenderer.invoke('jacky:openPreviewInBrowser', url),
  fetchLinkTitle: url => ipcRenderer.invoke('jacky:fetchLinkTitle', url),
  sanitizeWorkspaceCwd: cwd => ipcRenderer.invoke('jacky:workspace:sanitize', cwd),
  settings: {
    getDefaultProjectDir: () => ipcRenderer.invoke('jacky:setting:defaultProjectDir:get'),
    setDefaultProjectDir: dir => ipcRenderer.invoke('jacky:setting:defaultProjectDir:set', dir),
    pickDefaultProjectDir: () => ipcRenderer.invoke('jacky:setting:defaultProjectDir:pick')
  },
  zoom: {
    // Current zoom of this window, as { level, percent }.
    get: () => ipcRenderer.invoke('jacky:zoom:get'),
    setPercent: percent => ipcRenderer.send('jacky:zoom:set-percent', percent),
    // Fires on every zoom change, including the Ctrl/Cmd +/-/0 shortcuts,
    // so the settings UI can stay in sync with the keyboard.
    onChanged: callback => {
      const listener = (_event, payload) => callback(payload)
      ipcRenderer.on('jacky:zoom:changed', listener)

      return () => ipcRenderer.removeListener('jacky:zoom:changed', listener)
    }
  },
  revealLogs: () => ipcRenderer.invoke('jacky:logs:reveal'),
  getRecentLogs: () => ipcRenderer.invoke('jacky:logs:recent'),
  readDir: dirPath => ipcRenderer.invoke('jacky:fs:readDir', dirPath),
  gitRoot: startPath => ipcRenderer.invoke('jacky:fs:gitRoot', startPath),
  revealPath: targetPath => ipcRenderer.invoke('jacky:fs:reveal', targetPath),
  renamePath: (targetPath, newName) => ipcRenderer.invoke('jacky:fs:rename', targetPath, newName),
  writeTextFile: (filePath, content) => ipcRenderer.invoke('jacky:fs:writeText', filePath, content),
  trashPath: targetPath => ipcRenderer.invoke('jacky:fs:trash', targetPath),
  git: {
    worktreeList: repoPath => ipcRenderer.invoke('jacky:git:worktreeList', repoPath),
    worktreeAdd: (repoPath, options) => ipcRenderer.invoke('jacky:git:worktreeAdd', repoPath, options),
    worktreeRemove: (repoPath, worktreePath, options) =>
      ipcRenderer.invoke('jacky:git:worktreeRemove', repoPath, worktreePath, options),
    branchSwitch: (repoPath, branch) => ipcRenderer.invoke('jacky:git:branchSwitch', repoPath, branch),
    branchList: repoPath => ipcRenderer.invoke('jacky:git:branchList', repoPath),
    repoStatus: repoPath => ipcRenderer.invoke('jacky:git:repoStatus', repoPath),
    fileDiff: (repoPath, filePath) => ipcRenderer.invoke('jacky:git:fileDiff', repoPath, filePath),
    scanRepos: (roots, options) => ipcRenderer.invoke('jacky:git:scanRepos', roots, options),
    review: {
      list: (repoPath, scope, baseRef) => ipcRenderer.invoke('jacky:git:review:list', repoPath, scope, baseRef),
      diff: (repoPath, filePath, scope, baseRef, staged) =>
        ipcRenderer.invoke('jacky:git:review:diff', repoPath, filePath, scope, baseRef, staged),
      stage: (repoPath, filePath) => ipcRenderer.invoke('jacky:git:review:stage', repoPath, filePath),
      unstage: (repoPath, filePath) => ipcRenderer.invoke('jacky:git:review:unstage', repoPath, filePath),
      revert: (repoPath, filePath) => ipcRenderer.invoke('jacky:git:review:revert', repoPath, filePath),
      revParse: (repoPath, ref) => ipcRenderer.invoke('jacky:git:review:revParse', repoPath, ref),
      commit: (repoPath, message, push) => ipcRenderer.invoke('jacky:git:review:commit', repoPath, message, push),
      commitContext: repoPath => ipcRenderer.invoke('jacky:git:review:commitContext', repoPath),
      push: repoPath => ipcRenderer.invoke('jacky:git:review:push', repoPath),
      shipInfo: repoPath => ipcRenderer.invoke('jacky:git:review:shipInfo', repoPath),
      createPr: repoPath => ipcRenderer.invoke('jacky:git:review:createPr', repoPath)
    }
  },
  terminal: {
    dispose: id => ipcRenderer.invoke('jacky:terminal:dispose', id),
    resize: (id, size) => ipcRenderer.invoke('jacky:terminal:resize', id, size),
    start: options => ipcRenderer.invoke('jacky:terminal:start', options),
    write: (id, data) => ipcRenderer.invoke('jacky:terminal:write', id, data),
    onData: (id, callback) => {
      const channel = `jacky:terminal:${id}:data`
      const listener = (_event, payload) => callback(payload)
      ipcRenderer.on(channel, listener)

      return () => ipcRenderer.removeListener(channel, listener)
    },
    onExit: (id, callback) => {
      const channel = `jacky:terminal:${id}:exit`
      const listener = (_event, payload) => callback(payload)
      ipcRenderer.on(channel, listener)

      return () => ipcRenderer.removeListener(channel, listener)
    }
  },
  onClosePreviewRequested: callback => {
    const listener = () => callback()
    ipcRenderer.on('jacky:close-preview-requested', listener)

    return () => ipcRenderer.removeListener('jacky:close-preview-requested', listener)
  },
  onOpenUpdatesRequested: callback => {
    const listener = () => callback()
    ipcRenderer.on('jacky:open-updates', listener)

    return () => ipcRenderer.removeListener('jacky:open-updates', listener)
  },
  onDeepLink: callback => {
    const listener = (_event, payload) => callback(payload)
    ipcRenderer.on('jacky:deep-link', listener)

    return () => ipcRenderer.removeListener('jacky:deep-link', listener)
  },
  signalDeepLinkReady: () => ipcRenderer.invoke('jacky:deep-link-ready'),
  onWindowStateChanged: callback => {
    const listener = (_event, payload) => callback(payload)
    ipcRenderer.on('jacky:window-state-changed', listener)

    return () => ipcRenderer.removeListener('jacky:window-state-changed', listener)
  },
  onFocusSession: callback => {
    const listener = (_event, sessionId) => callback(sessionId)
    ipcRenderer.on('jacky:focus-session', listener)

    return () => ipcRenderer.removeListener('jacky:focus-session', listener)
  },
  onNotificationAction: callback => {
    const listener = (_event, payload) => callback(payload)
    ipcRenderer.on('jacky:notification-action', listener)

    return () => ipcRenderer.removeListener('jacky:notification-action', listener)
  },
  onPreviewFileChanged: callback => {
    const listener = (_event, payload) => callback(payload)
    ipcRenderer.on('jacky:preview-file-changed', listener)

    return () => ipcRenderer.removeListener('jacky:preview-file-changed', listener)
  },
  onBackendExit: callback => {
    const listener = (_event, payload) => callback(payload)
    ipcRenderer.on('jacky:backend-exit', listener)

    return () => ipcRenderer.removeListener('jacky:backend-exit', listener)
  },
  // Soft gateway-mode apply finished tearing down the primary backend. Renderer
  // should wipe session lists + re-dial without a window reload.
  onConnectionApplied: callback => {
    const listener = () => callback()
    ipcRenderer.on('jacky:connection:applied', listener)

    return () => ipcRenderer.removeListener('jacky:connection:applied', listener)
  },
  onPowerResume: callback => {
    const listener = () => callback()
    ipcRenderer.on('jacky:power-resume', listener)

    return () => ipcRenderer.removeListener('jacky:power-resume', listener)
  },
  onBootProgress: callback => {
    const listener = (_event, payload) => callback(payload)
    ipcRenderer.on('jacky:boot-progress', listener)

    return () => ipcRenderer.removeListener('jacky:boot-progress', listener)
  },
  // First-launch bootstrap progress -- emitted by the install.ps1 stage
  // runner in main.ts (apps/desktop/electron/bootstrap-runner.ts).
  // Renderer's install overlay subscribes to live events and queries the
  // current snapshot via getBootstrapState() to recover after a devtools
  // reload mid-bootstrap.
  getBootstrapState: () => ipcRenderer.invoke('jacky:bootstrap:get'),
  resetBootstrap: () => ipcRenderer.invoke('jacky:bootstrap:reset'),
  repairBootstrap: () => ipcRenderer.invoke('jacky:bootstrap:repair'),
  cancelBootstrap: () => ipcRenderer.invoke('jacky:bootstrap:cancel'),
  onBootstrapEvent: callback => {
    const listener = (_event, payload) => callback(payload)
    ipcRenderer.on('jacky:bootstrap:event', listener)

    return () => ipcRenderer.removeListener('jacky:bootstrap:event', listener)
  },
  getVersion: () => ipcRenderer.invoke('jacky:version'),
  getRemoteDisplayReason: () => ipcRenderer.invoke('jacky:get-remote-display-reason'),
  uninstall: {
    summary: () => ipcRenderer.invoke('jacky:uninstall:summary'),
    run: mode => ipcRenderer.invoke('jacky:uninstall:run', { mode })
  },
  updates: {
    check: () => ipcRenderer.invoke('jacky:updates:check'),
    apply: opts => ipcRenderer.invoke('jacky:updates:apply', opts),
    getBranch: () => ipcRenderer.invoke('jacky:updates:branch:get'),
    setBranch: name => ipcRenderer.invoke('jacky:updates:branch:set', name),
    onProgress: callback => {
      const listener = (_event, payload) => callback(payload)
      ipcRenderer.on('jacky:updates:progress', listener)

      return () => ipcRenderer.removeListener('jacky:updates:progress', listener)
    }
  },
  themes: {
    fetchMarketplace: id => ipcRenderer.invoke('jacky:vscode-theme:fetch', id),
    searchMarketplace: query => ipcRenderer.invoke('jacky:vscode-theme:search', query)
  }
})
