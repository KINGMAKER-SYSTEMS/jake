# Railway Deployment Guide

## Phase 1: Deploy with File Storage (Current Implementation)

This guide will deploy your Warner Campaign Manager to Railway with persistent file storage. Database migration (Phase 2) will come later.

### Prerequisites

1. **Install Railway CLI**
   ```bash
   npm install -g @railway/cli
   ```

2. **Verify Docker is installed** (optional, for local testing)
   ```bash
   docker --version
   ```

### Step 1: Initialize Railway Project

```bash
# Login to Railway
railway login

# Initialize project in this directory
railway init

# When prompted:
# - Project name: warner-campaign-manager
# - Environment: production
```

### Step 2: Add Persistent Volume

Railway volumes persist data across deployments. This is where your campaigns, cache, and config will live.

```bash
# Add a volume mounted at /app/data_volume
railway volume create --name campaign-data --mount /app/data_volume
```

### Step 3: Set Environment Variables

```bash
# Generate a secure secret key
SECRET_KEY=$(python -c 'import secrets; print(secrets.token_hex(32))')

# Set it in Railway
railway variables set SECRET_KEY="$SECRET_KEY"
```

### Step 4: Deploy

```bash
# Deploy to Railway
railway up

# Railway will:
# 1. Build the Docker image from your Dockerfile
# 2. Install Python dependencies
# 3. Start the Flask app on a public URL
```

### Step 5: Get Your Public URL

```bash
# Show deployment info
railway status

# Open in browser
railway open
```

Your app will be available at `https://your-app-name.up.railway.app`

### Step 6: Copy Existing Data to Volume

You need to upload your existing campaign data to the Railway volume. Use Railway CLI's shell access:

```bash
# Open a shell in the running container
railway shell

# From another terminal, use scp or railway's file upload
# Or manually recreate campaigns through the web UI
```

**Alternative**: Start fresh on Railway and migrate campaigns through the UI.

### Step 7: Verify Deployment

Visit your Railway URL and check:
- ✅ Campaign list loads
- ✅ Can create a new campaign
- ✅ Can add creators to a campaign
- ✅ Refresh stats works (yt-dlp scraping)
- ✅ Data persists after redeploy (`railway up` again)

---

## Configuration

### Environment Variables (automatically set by Railway)

| Variable | Value | Purpose |
|----------|-------|---------|
| `PORT` | Auto-set by Railway | HTTP port |
| `RAILWAY_ENVIRONMENT` | `production` | Enables production mode |
| `SECRET_KEY` | Your generated key | Flask session security |

### Directory Mapping (local → Railway)

| Local Path | Railway Path |
|------------|--------------|
| `campaign_manager/campaigns/` | `/app/data_volume/campaigns/` |
| `cache/` | `/app/data_volume/cache/` |
| `config/` | `/app/data_volume/config/` |
| `campaign_manager/internal_cache/` | `/app/data_volume/internal_cache/` |

---

## Custom Domain (Optional)

```bash
# Add your custom domain
railway domain add campaigns.yoursite.com

# Railway will provide DNS instructions
# Add a CNAME record pointing to your Railway URL
```

---

## Monitoring & Logs

```bash
# View live logs
railway logs

# Follow logs in real-time
railway logs --follow
```

---

## Redeploy After Code Changes

```bash
# After making code changes locally
railway up

# Railway automatically rebuilds and redeploys
# Volume data persists across deploys
```

---

## Troubleshooting

### App won't start
```bash
# Check logs
railway logs

# Common issues:
# - Missing SECRET_KEY → set it with `railway variables set`
# - Volume not mounted → verify with `railway volume list`
# - Port conflict → Railway sets PORT automatically
```

### Can't access campaigns
```bash
# Verify volume is mounted
railway shell
ls -la /app/data_volume/campaigns/

# If empty, data hasn't been copied yet
```

### yt-dlp errors
```bash
# Verify yt-dlp is installed in container
railway shell
yt-dlp --version

# Should show version 2024.10.0 or newer
```

### Cache not persisting
```bash
# Check CACHE_DIR environment variable
railway shell
echo $CACHE_DIR

# Should be empty (uses /app/data_volume/cache by default on Railway)
```

---

## Next Steps: Phase 2 (Database Migration)

After verifying Phase 1 works, we'll:
1. Add Railway Postgres (`railway add --plugin postgresql`)
2. Create database schema (`campaign_manager/db.py`)
3. Write migration script to import JSON → Postgres
4. Update web_dashboard.py to use database instead of files
5. Redeploy

See the deployment plan at `.claude/plans/elegant-moseying-goblet.md` for details.

---

## Costs

Railway free tier includes:
- 500 execution hours/month
- 1 GB volume storage (campaigns + cache should be <100 MB)
- 100 GB bandwidth

For your usage, this should stay within free tier. If you exceed limits, Railway will pause deployments until next month (or you can upgrade to $5/month hobby plan).

---

## Rollback

If something goes wrong:

```bash
# View deployment history
railway deployments

# Rollback to previous deployment
railway rollback <deployment-id>
```

---

## Support

Railway docs: https://docs.railway.app
Railway Discord: https://discord.gg/railway

Your app config:
- Dockerfile: `/Dockerfile`
- Railway config: `/railway.toml`
- Environment template: `/.env.example`
