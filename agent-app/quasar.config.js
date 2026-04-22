/* eslint-env node */
const { configure } = require('quasar/wrappers')
try {
  require('dotenv').config({ path: `.env.${process.env.NODE_ENV || 'development'}` })
} catch {
  /* dotenv optional — use process.env / CI */
}

module.exports = configure(function (/* ctx */) {
  return {
    boot: [
      'axios',
      'capacitor',
      'auth-guard',
      'errorLogger',
    ],

    css: [
      'app.scss',
    ],

    extras: [
      'material-icons',
      'material-symbols-outlined',
    ],

    build: {
      target: {
        browser: ['es2019', 'edge88', 'firefox78', 'chrome87', 'safari13.1'],
        node: 'node20',
      },
      vueRouterMode: 'hash',
      typescript: {
        strict: true,
        vueShim: true,
      },
      env: {
        API_URL: process.env.API_URL || 'http://localhost:8000/api/v1',
        GOOGLE_CLIENT_ID: process.env.GOOGLE_CLIENT_ID || '',
        // Sentry — leave blank in dev to skip initialisation
        SENTRY_DSN: process.env.SENTRY_DSN || '',
        SENTRY_ENVIRONMENT: process.env.SENTRY_ENVIRONMENT || 'development',
        SENTRY_RELEASE: process.env.GIT_COMMIT || '',
        SENTRY_TRACES_SAMPLE_RATE: process.env.SENTRY_TRACES_SAMPLE_RATE || '0.05',
      },
    },

    devServer: {
      open: false,
      port: 5176,
    },

    framework: {
      config: {
        brand: {
          primary:   '#2B2D6E',
          secondary: '#FF3D7F',
          accent:    '#FF3D7F',
          dark:      '#1A1B44',
          positive:  '#21BA45',
          negative:  '#DB2828',
          info:      '#31CCEC',
          warning:   '#F2C037',
        },
        notify: {
          position: 'top',
          timeout: 3000,
        },
        loading: {},
      },
      plugins: [
        'Notify',
        'Dialog',
        'Loading',
        'LocalStorage',
        'BottomSheet',
      ],
    },

    animations: 'all',

    ssr: {
      pwa: false,
      prodPort: 3000,
      middlewares: [
        'render',
      ],
    },

    pwa: {
      workboxMode: 'generateSW',
    },

    capacitor: {
      hideSplashScreenOnAppReady: true,
      iosStatusBarPadding: true,
    },

    electron: {
      inspectPort: 5858,
      bundler: 'packager',
    },
  }
})
