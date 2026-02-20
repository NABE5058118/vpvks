module.exports = {
  apps: [{
    name: "bot",
    script: "python3",
    args: "main.py",
    instances: process.env.PM2_INSTANCES || 2,
    exec_mode: "cluster",
    env: {
      NODE_ENV: "production",
      PYTHONUNBUFFERED: "1"
    },
    error_file: "/app/logs/error.log",
    out_file: "/app/logs/out.log",
    log_file: "/app/logs/combined.log",
    time: true,
    autorestart: true,
    max_memory_restart: "256M",
    watch: false,
    merge_logs: true,
    log_date_format: "YYYY-MM-DD HH:mm:ss Z"
  }]
};
