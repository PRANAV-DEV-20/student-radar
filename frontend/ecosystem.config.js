module.exports = {
  apps: [
    {
      name: "my-local-app",
      script: "node_modules/next/dist/bin/next",
      args: "start -p 3000",
      cwd: "frontend",
      autorestart: true,
      env: {
        NODE_ENV: "production"
      }
    },
    {
      name: "cloudflare-tunnel",
      script: "cloudflared",
      args: "tunnel --url http://localhost:3000",
      autorestart: true
    }
  ]
};
