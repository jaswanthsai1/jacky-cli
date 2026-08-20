import React from 'react';
import Link from '@docusaurus/Link';
import useBaseUrl from '@docusaurus/useBaseUrl';
import styles from './styles.module.css';

/**
 * Rich homepage hero — mascot banner, tagline, and primary CTAs.
 * Lives at docs/index.mdx (slug: "/"), imported like any other
 * Docusaurus MDX component (@site/src/components/...).
 */
export function HomepageHero(): React.ReactElement {
  const banner = useBaseUrl('img/jacky-banner.jpeg');
  return (
    <header className={styles.hero}>
      <div className={styles.heroCopy}>
        <div className={styles.eyebrow}>
          <span className={styles.eyebrowDot} />
          MIT licensed &middot; local or cloud &middot; open source
        </div>
        <h1 className={styles.heroTitle}>
          The AI CLI built for <span className={styles.grad}>hunting and building</span>
        </h1>
        <p className={styles.heroLede}>
          Jacky CLI is a self-improving agent CLI: a real tool-calling loop, a
          bundled offensive-security hunt methodology, and a skill system that
          writes and refines its own procedures as it works — running fully
          offline against local models or against any cloud provider you
          bring a key for.
        </p>
        <div className={styles.heroCtas}>
          <Link className={styles.btnPrimary} to="#quick-start">
            Get Started →
          </Link>
          <Link className={styles.btnSecondary} to="/methodology/">
            Hunt-Loop Methodology
          </Link>
          <Link className={styles.btnSecondary} to="https://github.com/jaswanthsai1/jacky-cli">
            View on GitHub
          </Link>
        </div>
      </div>
      <div className={styles.heroVisual}>
        <div className={styles.frame}>
          <img
            src={banner}
            alt="Jacky CLI mascot: a hooded AI hacker-bot with a glowing green terminal-prompt face, next to the word JACKY, tagline AI · CLI · AUTOMATE"
            width={1254}
            height={1254}
            loading="eager"
          />
        </div>
      </div>
    </header>
  );
}

interface Feature {
  icon: string;
  title: string;
  body: React.ReactNode;
}

const FEATURES: Feature[] = [
  {
    icon: '⇄',
    title: 'Dual local + cloud models',
    body: (
      <>
        Run fully offline against Ollama and any tool-calling-capable GGUF
        model — zero API cost, nothing leaves your machine — or point it at
        any OpenAI-compatible or Anthropic-compatible cloud provider with your
        own key. Switch with <code>jacky model</code>, no code changes.
      </>
    ),
  },
  {
    icon: '🎯',
    title: 'Bundled bug-hunt methodology',
    body: (
      <>
        Ships with a real offensive-security doctrine under <code>skills/</code>:
        scope → recon → rank → enumerate → test → validate → chain → report,
        plus finding-validation gates and evidence-hygiene discipline. See{' '}
        <Link to="/methodology/">the full methodology</Link>.
      </>
    ),
  },
  {
    icon: '🛠',
    title: 'Tool-calling agent loop',
    body: (
      <>
        40+ built-in tools, an MCP client for connecting any MCP server, a
        toolset system for scoping what&apos;s available per session, and a
        full terminal interface with streaming tool output.
      </>
    ),
  },
  {
    icon: '🧠',
    title: 'Self-improving skill system',
    body: (
      <>
        Agent-curated memory with periodic nudges. Autonomous skill creation
        after complex tasks — skills refine themselves during use. Compatible
        with the open <Link to="https://agentskills.io">agentskills.io</Link>{' '}
        standard.
      </>
    ),
  },
  {
    icon: '⌁',
    title: 'One-command install',
    body: (
      <>
        Clone the repo, run <code>./setup.sh</code>, and it creates the
        virtualenv, installs Jacky, links the <code>jacky</code> command onto
        your PATH — then actually runs <code>jacky --help</code> to prove the
        install works before declaring success.
      </>
    ),
  },
  {
    icon: '📡',
    title: 'Lives where you do',
    body: (
      <>
        CLI, Telegram, Discord, Slack, WhatsApp, Signal, Matrix, Teams, and
        20+ platforms from one gateway — plus scheduled cron automations that
        deliver anywhere.
      </>
    ),
  },
];

export function HomepageFeatures(): React.ReactElement {
  return (
    <section className={styles.section}>
      <div className={styles.sectionHead}>
        <div className={styles.kicker}>Capabilities</div>
        <h2>What Jacky actually does</h2>
        <p>No fluff — six things it ships with today.</p>
      </div>
      <div className={styles.featureGrid}>
        {FEATURES.map((f) => (
          <div className={styles.featureCard} key={f.title}>
            <div className={styles.featureIcon} aria-hidden="true">
              {f.icon}
            </div>
            <h3>{f.title}</h3>
            <p>{f.body}</p>
          </div>
        ))}
      </div>
    </section>
  );
}

const HUNT_STAGES = [
  'scope',
  'recon',
  'rank',
  'enumerate',
  'test',
  'validate',
  'chain',
  'report',
];

export function HomepageHuntLoop(): React.ReactElement {
  return (
    <section className={styles.section}>
      <div className={styles.sectionHead}>
        <div className={styles.kicker}>Methodology</div>
        <h2>The hunt loop</h2>
        <p>The bundled offensive-security doctrine, end to end.</p>
      </div>
      <div className={styles.loopRow}>
        {HUNT_STAGES.map((stage, i) => (
          <React.Fragment key={stage}>
            <span className={styles.stage}>{stage}</span>
            {i < HUNT_STAGES.length - 1 && (
              <span className={styles.arrow} aria-hidden="true">
                →
              </span>
            )}
          </React.Fragment>
        ))}
      </div>
      <p className={styles.loopNote}>
        Class playbooks cover SSRF, IDOR, XSS, SQLi, SSTI, auth bypass,
        business logic, race conditions, CORS, subdomain takeover, JWT/OAuth,
        API misconfiguration, cloud/K8s misconfiguration, and more — see the{' '}
        <Link to="/methodology/">full methodology index</Link>.
      </p>
    </section>
  );
}
