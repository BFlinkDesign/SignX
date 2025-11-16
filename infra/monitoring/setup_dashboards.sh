#!/bin/bash
# Monitoring Dashboard Setup Script
# Configures Grafana dashboards and alert rules

set -e

echo "=== Monitoring Dashboard Setup ==="
echo ""

# Wait for Grafana to be ready
echo "1. Waiting for Grafana to be ready..."
for i in {1..30}; do
    if curl -fsS http://localhost:3001/api/health > /dev/null 2>&1; then
        echo "   ✅ Grafana ready"
        break
    fi
    echo "   Waiting... ($i/30)"
    sleep 2
done

# Verify dashboard file exists
echo ""
echo "2. Verifying dashboard configuration..."
if [ -f "../services/api/monitoring/grafana_dashboard.json" ]; then
    echo "   ✅ Dashboard JSON exists"
else
    echo "   ⚠️  Dashboard JSON not found, skipping import"
fi

# Check Prometheus connectivity
echo ""
echo "3. Checking Prometheus connectivity..."
if curl -fsS http://localhost:9090/api/v1/targets > /dev/null 2>&1; then
    echo "   ✅ Prometheus accessible"
    
    # Check targets
    TARGETS=$(curl -s http://localhost:9090/api/v1/targets | jq -r '.data.activeTargets[] | select(.health == "up") | .labels.job' | wc -l)
    echo "   Active targets: $TARGETS"
else
    echo "   ⚠️  Prometheus not accessible (may not be deployed)"
fi

# Verify alert rules
echo ""
echo "4. Verifying alert rules..."
if [ -f "alerts.yml" ]; then
    echo "   ✅ Alert rules file exists"
    
    # Validate YAML syntax
    if command -v yamllint > /dev/null 2>&1; then
        if yamllint alerts.yml > /dev/null 2>&1; then
            echo "   ✅ Alert rules syntax valid"
        else
            echo "   ⚠️  Alert rules syntax issues"
        fi
    else
        echo "   ℹ️  yamllint not available, skipping syntax check"
    fi
else
    echo "   ⚠️  Alert rules file not found"
fi

# Check postgres_exporter
echo ""
echo "5. Checking postgres_exporter..."
if curl -fsS http://localhost:9187/metrics > /dev/null 2>&1; then
    echo "   ✅ postgres_exporter metrics available"
    
    # Check key metrics
    METRICS=$(curl -s http://localhost:9187/metrics | grep -c "^pg_" || echo "0")
    echo "   PostgreSQL metrics: $METRICS"
else
    echo "   ⚠️  postgres_exporter not accessible (may be unhealthy)"
fi

echo ""
echo "=== Monitoring Setup Complete ==="
echo ""
echo "Dashboard URLs:"
echo "- Grafana: http://localhost:3001"
echo "- Prometheus: http://localhost:9090"
echo "- Postgres Exporter: http://localhost:9187/metrics"
echo ""
echo "Next steps:"
echo "1. Import dashboards in Grafana UI"
echo "2. Configure alert rules in Prometheus"
echo "3. Test alert delivery"
echo "4. Document runbook procedures"

