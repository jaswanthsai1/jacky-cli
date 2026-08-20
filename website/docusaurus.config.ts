import {themes as prismThemes} from 'prism-react-renderer';
import type {Config} from '@docusaurus/types';
import type * as Preset from '@docusaurus/preset-classic';

const config: Config = {
  title: 'Jacky CLI',
  tagline: 'The AI CLI built for hunting and building',
  favicon: 'img/favicon.ico',

  // Deployed today at https://jaswanthsai1.github.io/jacky-cli/ (a GitHub
  // Pages *project* site), so `url` is the Pages domain and `baseUrl` is
  // the repo subpath. If this site is later pointed at a custom domain
  // (e.g. jacky-cli.dev) as a Pages *user/org* site or via Vercel/Netlify,
  // change BOTH of the following:
  //   1. `url`: the new domain, e.g. 'https://jacky-cli.dev'
  //   2. `baseUrl`: '/' (root — no more /jacky-cli/ subpath)
  // ...and add a `website/static/CNAME` file containing the domain (for
  // GitHub Pages specifically; not needed for Vercel/Netlify custom
  // domains, which are configured in their dashboards instead). Do NOT
  // add a CNAME file while still deploying to the jaswanthsai1.github.io
  // subpath — GitHub Pages will start redirecting the project site to the
  // (unconfigured) custom domain and break the current deployment.
  url: 'https://jaswanthsai1.github.io',
  baseUrl: '/jacky-cli/',

  organizationName: 'jaswanthsai1',
  projectName: 'jacky-cli',

  onBrokenLinks: 'warn',

  markdown: {
    mermaid: true,
    hooks: {
      onBrokenMarkdownLinks: 'warn',
    },
  },

  i18n: {
    defaultLocale: 'en',
    locales: ['en', 'zh-Hans'],
    localeConfigs: {
      en: {
        label: 'English',
      },
      'zh-Hans': {
        label: '简体中文',
        htmlLang: 'zh-Hans',
      },
    },
  },

  themes: [
    '@docusaurus/theme-mermaid',
    [
      require.resolve('@easyops-cn/docusaurus-search-local'),
      /** @type {import("@easyops-cn/docusaurus-search-local").PluginOptions} */
      ({
        hashed: true,
        language: ['en', 'zh'],
        indexBlog: false,
        docsRouteBasePath: '/',
        // Disabled: appends ?_highlight=... to URLs (before the #anchor),
        // which makes copy/pasted doc links ugly. Ctrl+F on the page is fine.
        highlightSearchTermsOnTargetPage: false,
        // Exclude the auto-generated per-skill catalog pages from search.
        // There are hundreds of them and they dominate results for generic
        // terms, drowning out the real user-guide / reference docs.
        // The two human-written catalog indexes (reference/skills-catalog,
        // reference/optional-skills-catalog) remain indexed.
        //
        // Note: ignoreFiles matches `route` (baseUrl stripped, no leading
        // slash). With baseUrl '/docs/', `/docs/user-guide/skills/bundled/x`
        // becomes 'user-guide/skills/bundled/x'.
        ignoreFiles: [
          /^user-guide\/skills\/bundled\//,
          /^user-guide\/skills\/optional\//,
        ],
      }),
    ],
  ],

  plugins: [
    [
      '@docusaurus/plugin-client-redirects',
      {
        // Static-host redirects for renamed doc pages (GitHub Pages can't
        // do server-side redirects). Paths are relative to baseUrl (/docs/).
        redirects: [
          {
            // Renamed in #44470 (Automation Blueprints terminology rebrand)
            from: '/guides/automation-templates',
            to: '/guides/automation-blueprints',
          },
          {
            // Moved when the Plugins subcategory was created under
            // Developer Guide > Extending (docs restructure, July 2026)
            from: '/guides/build-a-jacky-plugin',
            to: '/developer-guide/plugins',
          },
        ],
      },
    ],
  ],

  presets: [
    [
      'classic',
      {
        docs: {
          routeBasePath: '/',  // Docs at the root of /docs/
          sidebarPath: './sidebars.ts',
          editUrl: 'https://github.com/jaswanthsai1/jacky-cli/edit/main/website/',
        },
        blog: false,
        theme: {
          customCss: './src/css/custom.css',
        },
      } satisfies Preset.Options,
    ],
  ],

  themeConfig: {
    image: 'img/jacky-cli-banner.png',
    colorMode: {
      defaultMode: 'dark',
      respectPrefersColorScheme: true,
    },
    docs: {
      sidebar: {
        hideable: true,
        autoCollapseCategories: true,
      },
    },
    navbar: {
      title: 'Jacky CLI',
      logo: {
        alt: 'Jacky CLI — hooded AI hacker-bot mascot',
        src: 'img/logo.png',
      },
      items: [
        {
          type: 'docSidebar',
          sidebarId: 'docs',
          position: 'left',
          label: 'Docs',
        },
        {
          to: '/methodology/',
          label: 'Methodology',
          position: 'left',
        },
        {
          to: '/skills',
          label: 'Skills',
          position: 'left',
        },
        {
          to: '/#quick-start',
          label: 'Download',
          position: 'left',
        },
        {
          type: 'localeDropdown',
          position: 'right',
        },
        {
          to: '/',
          label: 'Home',
          position: 'right',
        },
        {
          href: 'https://github.com/jaswanthsai1/jacky-cli',
          label: 'GitHub',
          position: 'right',
        },
      ],
    },
    footer: {
      style: 'dark',
      links: [
        {
          title: 'Docs',
          items: [
            { label: 'Getting Started', to: '/getting-started/quickstart' },
            { label: 'Methodology', to: '/methodology/' },
            { label: 'User Guide', to: '/user-guide/cli' },
            { label: 'Developer Guide', to: '/developer-guide/architecture' },
            { label: 'Reference', to: '/reference/cli-commands' },
          ],
        },
        {
          title: 'Community',
          items: [
            { label: 'GitHub Issues', href: 'https://github.com/jaswanthsai1/jacky-cli/issues' },
            { label: 'Skills Hub', href: 'https://agentskills.io' },
          ],
        },
        {
          title: 'More',
          items: [
            { label: 'Quick Start', href: 'https://github.com/jaswanthsai1/jacky-cli#quick-start' },
            { label: 'GitHub', href: 'https://github.com/jaswanthsai1/jacky-cli' },
          ],
        },
      ],
      copyright: `Jacky CLI · a fork of <a href="https://github.com/NousResearch/hermes-agent">Hermes Agent</a> by Nous Research · MIT License · ${new Date().getFullYear()}`,
    },
    prism: {
      theme: prismThemes.github,
      darkTheme: prismThemes.dracula,
      additionalLanguages: ['bash', 'yaml', 'json', 'python', 'toml'],
    },
    mermaid: {
      theme: {light: 'neutral', dark: 'dark'},
    },
  } satisfies Preset.ThemeConfig,
};

export default config;
