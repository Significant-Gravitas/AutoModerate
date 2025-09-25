# AutoModerate GCP Deployment

This folder contains GCP-specific deployment configurations for AutoModerate.

## Files

- `Dockerfile` - Cloud Run optimized Docker image (no PostgreSQL)
- `cloudbuild.yaml` - Cloud Build configuration for CI/CD
- `.gitignore` - Prevents accidental commit of environment files

## Setup

### 1. Cloud SQL Setup
Create PostgreSQL instance in Cloud SQL and note the connection string:
```
postgresql://user:pass@/automoderate?host=/cloudsql/PROJECT:REGION:INSTANCE
```

### 2. Environment Variables (Public Repo Safe)
**DO NOT** create environment files in a public repository. Instead, use one of these secure methods:

**Option A: Cloud Build Substitution Variables** (Recommended)
Set environment variables directly in Cloud Build trigger configuration:
- `_DATABASE_URL`: Your Cloud SQL connection string
- `_OPENAI_API_KEY`: Your OpenAI API key
- `_SECRET_KEY`: Secure random string for Flask sessions
- `_ADMIN_EMAIL`: Admin user email
- `_ADMIN_PASSWORD`: Admin user password

**Option B: Secret Manager** (Most Secure)
Store sensitive values in GCP Secret Manager and reference in `cloudbuild.yaml`:
```yaml
availableSecrets:
  secretManager:
  - versionName: projects/PROJECT_ID/secrets/openai-api-key/versions/latest
    env: 'OPENAI_API_KEY'
```

**Option C: Cloud Run Environment Variables**
Set environment variables directly in Cloud Run service configuration.

### 3. Cloud Build Triggers
Create separate triggers for dev and prod branches:

**Dev Trigger (dev branch):**
- Branch: `dev`
- Build config: `deploy/cloudbuild.yaml`
- Substitution variables:
  - `_ENV=dev`
  - `_FLASK_CONFIG=development`
  - `_DATABASE_URL=your-dev-cloud-sql-connection`
  - `_OPENAI_API_KEY=your-dev-api-key`
  - `_SECRET_KEY=your-dev-secret-key`

**Prod Trigger (main branch):**
- Branch: `main`
- Build config: `deploy/cloudbuild.yaml`
- Substitution variables:
  - `_ENV=prod`
  - `_FLASK_CONFIG=production`
  - `_DATABASE_URL=your-prod-cloud-sql-connection`
  - `_OPENAI_API_KEY=your-prod-api-key`
  - `_SECRET_KEY=your-prod-secret-key`

## Services

- **Dev**: `automoderate-dev` → `automod-dev.agpt.co`
- **Prod**: `automoderate-prod` → `automod.agpt.co`