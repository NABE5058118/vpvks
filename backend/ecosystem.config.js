module.exports = {
  apps: [{
    name: "backend",
    script: "python3",
    args: "server.py",
    instances: process.env.PM2_INSTANCES || 4,
    exec_mode: "cluster",
    env: {
      PORT: 8080,
      NODE_ENV: "production",
      PYTHONUNBUFFERED: "1"
    },
    error_file: "/app/logs/error.log",
    out_file: "/app/logs/out.log",
    log_file: "/app/logs/combined.log",
    time: true,
    autorestart: true,
    max_memory_restart: "500M",
    watch: false,
    merge_logs: true,
    log_date_format: "YYYY-MM-DD HH:mm:ss Z"
  }]
};
