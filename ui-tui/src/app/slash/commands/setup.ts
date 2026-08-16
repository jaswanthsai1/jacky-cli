import { withInkSuspended } from '@jacky/ink'

import { launchJackyCommand } from '../../../lib/externalCli.js'
import { runExternalSetup } from '../../setupHandoff.js'
import type { SlashCommand } from '../types.js'

export const setupCommands: SlashCommand[] = [
  {
    help: 'run full setup wizard (launches `jacky setup`)',
    name: 'setup',
    run: (arg, ctx) =>
      void runExternalSetup({
        args: ['setup', ...arg.split(/\s+/).filter(Boolean)],
        ctx,
        done: 'setup complete — starting session…',
        launcher: launchJackyCommand,
        suspend: withInkSuspended
      })
  }
]
