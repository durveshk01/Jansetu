# Deployment notes

Local commands and Docker Compose setup are in the root README. The no-cost demo target is Koyeb's single free web instance plus a Neon Free Postgres database. Koyeb Free has 512 MB RAM, 0.1 vCPU, 2 GB SSD, one service per organization, and scales down after one hour without traffic; Neon Free currently advertises 1 GB database storage and 100 compute hours per project each month. These limits are for a small demo, not production availability.

The Koyeb service should deploy from the public `durveshk01/Jansetu` repository with work directory `backend`, Python buildpack, and Procfile start command. Set `DATABASE_URL` to the Neon pooled PostgreSQL URL, `SECRET_KEY` to a random secret, `CORS_ORIGINS` to the Vercel frontend origin, `SEED_DEMO_DATA=false`, and `UPLOAD_DIR=/tmp/jansetu-uploads`. Local file uploads on Koyeb are ephemeral: production uploads need an external object store. Do not set a payment method or select a paid instance/plan. No Koyeb or Neon account is connected to this workspace yet, so these services have not been provisioned.

For production, use managed PostgreSQL/PostGIS, private object storage, HTTPS ingress, strict CORS, secret management, backups, migration review, and observability. Do not publish demo credentials or fictional scheme/complaint records.
