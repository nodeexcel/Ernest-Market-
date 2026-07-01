/** @type {import('pm2').StartOptions[]} */
const apps = [
  {
    name: 'ernest-api',
    cwd: '/home/node/ernest-market/Ernest-Market-',
    script: 'venv/bin/uvicorn',
    args: 'api.main:app --host 0.0.0.0 --port 20150',
    interpreter: 'none',
    autorestart: true,
    max_restarts: 10,
    min_uptime: '10s',
  },
  {
    name: 'ernest-frontend',
    cwd: '/home/node/ernest-market/Ernest-Market-/frontend',
    script: 'npm',
    args: 'run preview',
    interpreter: 'none',
    autorestart: true,
    max_restarts: 10,
    min_uptime: '10s',
  },
  {
    name: 'ernest-scan-once',
    cwd: '/home/node/ernest-market/Ernest-Market-',
    script: 'venv/bin/python',
    args: 'main.py --once',
    interpreter: 'none',
    autorestart: false,
    cron_restart: '*/5 * * * *',
  },
];

module.exports = { apps };
