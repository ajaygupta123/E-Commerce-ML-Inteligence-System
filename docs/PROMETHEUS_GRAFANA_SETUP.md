# Prometheus & Grafana Setup Guide (Future)

## Overview

Adding Prometheus and Grafana later is **straightforward** - it's primarily configuration changes since all the monitoring infrastructure is already in place.

## Current State

✅ **Already Implemented:**
- Prometheus metrics endpoint (`/metrics`) - ✅ Working
- Metrics middleware collecting data - ✅ Working
- Health and readiness endpoints - ✅ Working
- Prometheus config file exists - ✅ `observability/prometheus/prometheus.yml`
- Grafana dashboard JSON exists - ✅ `observability/grafana/dashboards/api_metrics.json`

## What's Needed (5-10 minutes)

### Step 1: Add Services to docker-compose.yml

Just uncomment/add these services:

```yaml
  prometheus:
    image: prom/prometheus:latest
    container_name: ecommerce-prometheus
    ports:
      - "9090:9090"
    volumes:
      - ./observability/prometheus/prometheus.yml:/etc/prometheus/prometheus.yml:ro
      - prometheus_data:/prometheus
    command:
      - '--config.file=/etc/prometheus/prometheus.yml'
      - '--storage.tsdb.path=/prometheus'
      - '--storage.tsdb.retention.time=30d'
    depends_on:
      - api
    restart: unless-stopped

  grafana:
    image: grafana/grafana:latest
    container_name: ecommerce-grafana
    ports:
      - "3000:3000"
    environment:
      - GF_SECURITY_ADMIN_USER=admin
      - GF_SECURITY_ADMIN_PASSWORD=admin
      - GF_USERS_ALLOW_SIGN_UP=false
    volumes:
      - grafana_data:/var/lib/grafana
      - ./observability/grafana/dashboards:/etc/grafana/provisioning/dashboards:ro
      - ./observability/grafana/datasources:/etc/grafana/provisioning/datasources:ro
    depends_on:
      - prometheus
    restart: unless-stopped

volumes:
  # ... existing volumes ...
  prometheus_data:
  grafana_data:
```

### Step 2: Create Grafana Datasource Config

Create `observability/grafana/datasources/prometheus.yml`:

```yaml
apiVersion: 1

datasources:
  - name: Prometheus
    type: prometheus
    access: proxy
    url: http://prometheus:9090
    isDefault: true
    editable: true
```

### Step 3: Create Grafana Dashboard Provisioning

Create `observability/grafana/provisioning/dashboards/dashboards.yml`:

```yaml
apiVersion: 1

providers:
  - name: 'Default'
    orgId: 1
    folder: ''
    type: file
    disableDeletion: false
    updateIntervalSeconds: 10
    allowUiUpdates: true
    options:
      path: /etc/grafana/provisioning/dashboards
      foldersFromFilesStructure: true
```

### Step 4: Start Services

```bash
docker-compose up -d prometheus grafana
```

### Step 5: Access Dashboards

- **Prometheus**: http://localhost:9090
- **Grafana**: http://localhost:3000
  - Username: `admin`
  - Password: `admin`

## Why It's Easy

### 1. Metrics Already Exposed

The API already exposes Prometheus metrics at `/metrics`:
- HTTP request counts
- Response times (histograms)
- System metrics (CPU, memory)
- Custom business metrics

**No code changes needed!**

### 2. Configuration Files Ready

- ✅ `observability/prometheus/prometheus.yml` - Already configured to scrape API
- ✅ `observability/grafana/dashboards/api_metrics.json` - Dashboard template exists

### 3. Docker Compose Pattern

Just add two services - standard Docker Compose pattern, no special setup.

### 4. No Application Changes

The application doesn't need any changes because:
- Metrics endpoint already exists
- Metrics are already being collected
- Format is already Prometheus-compatible

## Estimated Time

- **Setup**: 5-10 minutes
- **Testing**: 5 minutes
- **Total**: ~15 minutes

## Migration Path

### Current (Lightweight Monitoring)

```bash
# Use existing lightweight monitoring
make monitor
curl http://localhost:8000/v1/system_status
```

### Future (Prometheus + Grafana)

```bash
# Add to docker-compose.yml (5 min)
# Start services
docker-compose up -d prometheus grafana

# Access dashboards
open http://localhost:3000
```

**Both can coexist!** The lightweight monitoring script will continue to work.

## Benefits of Adding Later

1. **No Breaking Changes**: Current monitoring continues to work
2. **Gradual Migration**: Can test Prometheus/Grafana alongside existing monitoring
3. **Better Visualization**: Grafana provides better charts and dashboards
4. **Historical Data**: Prometheus stores metrics for historical analysis
5. **Alerting**: Can add Prometheus alerting rules later

## What Gets Better

| Feature | Current (Lightweight) | With Prometheus/Grafana |
|---------|----------------------|-------------------------|
| **Real-time View** | ✅ Yes | ✅ Yes |
| **Historical Data** | ❌ No | ✅ Yes (30 days) |
| **Visualization** | ✅ Text dashboard | ✅ Rich charts/graphs |
| **Alerting** | ⚠️ Manual checks | ✅ Automated alerts |
| **Multi-metric Queries** | ⚠️ Limited | ✅ Advanced queries |
| **Dashboard Sharing** | ❌ No | ✅ Yes |

## Quick Start Script (Future)

When ready, you can create a quick setup script:

```bash
#!/bin/bash
# scripts/setup_prometheus_grafana.sh

echo "Adding Prometheus and Grafana..."

# Add services to docker-compose.yml (automated or manual)
# Create datasource config
# Create dashboard provisioning
# Start services

docker-compose up -d prometheus grafana

echo "✅ Prometheus: http://localhost:9090"
echo "✅ Grafana: http://localhost:3000 (admin/admin)"
```

## Summary

**Adding Prometheus & Grafana later is:**
- ✅ **Easy**: Just config changes (5-10 min)
- ✅ **Non-breaking**: Current monitoring continues to work
- ✅ **Well-prepared**: All infrastructure already in place
- ✅ **Optional**: Can add when needed for better visualization

**It's essentially:**
1. Add 2 services to docker-compose.yml
2. Create 2 config files (datasource + dashboard provisioning)
3. Start services
4. Done!

No code changes, no application modifications, just Docker Compose configuration.

