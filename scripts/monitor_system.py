#!/usr/bin/env python3
"""Lightweight system monitoring script - Bird's Eye View."""
import requests
import json
import time
import subprocess
from datetime import datetime
from typing import Dict, Any, Optional
from collections import defaultdict
import sys

API_BASE_URL = "http://localhost:8000"


def get_health_status() -> Dict[str, Any]:
    """Get health status from API."""
    try:
        response = requests.get(f"{API_BASE_URL}/health", timeout=5)
        return {
            "status": "healthy" if response.status_code == 200 else "unhealthy",
            "status_code": response.status_code,
            "response_time_ms": response.elapsed.total_seconds() * 1000,
        }
    except Exception as e:
        return {
            "status": "unreachable",
            "error": str(e),
        }


def get_ready_status() -> Dict[str, Any]:
    """Get readiness status from API."""
    try:
        response = requests.get(f"{API_BASE_URL}/ready", timeout=5)
        data = response.json() if response.status_code == 200 else {}
        return {
            "status": "ready" if response.status_code == 200 else "not_ready",
            "status_code": response.status_code,
            "details": data,
        }
    except Exception as e:
        return {
            "status": "unreachable",
            "error": str(e),
        }


def get_metrics() -> Dict[str, Any]:
    """Get Prometheus metrics from API."""
    try:
        response = requests.get(f"{API_BASE_URL}/metrics", timeout=10)
        if response.status_code != 200:
            return {"error": f"Status code: {response.status_code}"}
        
        metrics = {}
        for line in response.text.split('\n'):
            if line.startswith('#') or not line.strip():
                continue
            
            # Parse Prometheus metrics format
            if '{' in line:
                # Metric with labels: metric_name{label="value"} value
                parts = line.split(' ')
                if len(parts) >= 2:
                    metric_part = parts[0]
                    value = parts[-1]
                    metric_name = metric_part.split('{')[0]
                    try:
                        metrics[metric_name] = float(value)
                    except ValueError:
                        pass
            else:
                # Simple metric: metric_name value
                parts = line.split(' ')
                if len(parts) >= 2:
                    metric_name = parts[0]
                    value = parts[-1]
                    try:
                        metrics[metric_name] = float(value)
                    except ValueError:
                        pass
        
        return metrics
    except Exception as e:
        return {"error": str(e)}


def get_container_stats() -> Dict[str, Any]:
    """Get Docker container statistics."""
    containers = ["ecommerce-api", "ecommerce-postgres", "ecommerce-qdrant", "ecommerce-ollama"]
    stats = {}
    
    for container in containers:
        try:
            result = subprocess.run(
                ["docker", "stats", "--no-stream", "--format", "json", container],
                capture_output=True,
                text=True,
                timeout=5
            )
            if result.returncode == 0 and result.stdout.strip():
                data = json.loads(result.stdout.strip())
                stats[container] = {
                    "cpu_percent": data.get("CPUPerc", "0%").replace("%", ""),
                    "memory_usage": data.get("MemUsage", "N/A"),
                    "memory_percent": data.get("MemPerc", "0%").replace("%", ""),
                    "network_io": data.get("NetIO", "N/A"),
                    "block_io": data.get("BlockIO", "N/A"),
                }
            else:
                stats[container] = {"status": "not_running"}
        except Exception as e:
            stats[container] = {"error": str(e)}
    
    return stats


def get_database_connections() -> Dict[str, Any]:
    """Get database connection pool stats."""
    try:
        # Try to get connection stats from PostgreSQL
        result = subprocess.run(
            ["docker", "exec", "ecommerce-postgres", "psql", "-U", "app", "-d", "ecommerce", "-t", "-c", 
             "SELECT count(*) FROM pg_stat_activity WHERE datname = 'ecommerce';"],
            capture_output=True,
            text=True,
            timeout=5
        )
        if result.returncode == 0 and result.stdout.strip():
            try:
                # Parse the output (should be just a number)
                connections = int(result.stdout.strip())
                max_connections = 300  # From config: pool_size=100 + max_overflow=200
                return {
                    "active_connections": connections,
                    "max_connections": max_connections,
                    "utilization_percent": round((connections / max_connections) * 100, 1),
                }
            except (ValueError, IndexError):
                pass
    except Exception:
        pass
    
    # Fallback: Try to get from API metrics if available
    return {"note": "Connection stats require direct DB access"}


def format_metrics_summary(metrics: Dict[str, Any]) -> Dict[str, Any]:
    """Format metrics into a readable summary."""
    summary = {
        "http_requests": {},
        "response_times": {},
        "system": {},
    }
    
    # HTTP Requests
    http_total = metrics.get("http_requests_total", 0)
    summary["http_requests"]["total"] = int(http_total)
    
    # Response times (if available)
    duration_count = metrics.get("http_request_duration_seconds_count", 0)
    duration_sum = metrics.get("http_request_duration_seconds_sum", 0)
    if duration_count > 0:
        avg_duration = duration_sum / duration_count
        summary["response_times"]["average_ms"] = round(avg_duration * 1000, 2)
        summary["response_times"]["total_requests"] = int(duration_count)
    
    # System metrics
    summary["system"]["process_memory_bytes"] = metrics.get("process_resident_memory_bytes", 0)
    summary["system"]["process_cpu_seconds"] = metrics.get("process_cpu_seconds_total", 0)
    
    return summary


def print_dashboard(health: Dict, ready: Dict, metrics: Dict, containers: Dict, db_conn: Dict):
    """Print a formatted dashboard."""
    print("\n" + "="*80)
    print(" " * 25 + "SYSTEM MONITORING DASHBOARD")
    print("="*80)
    print(f"Timestamp: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print()
    
    # Health Status
    print("📊 HEALTH STATUS")
    print("-" * 80)
    print(f"  API Health:     {health.get('status', 'unknown').upper():<15} "
          f"(Response: {health.get('response_time_ms', 0):.2f}ms)")
    print(f"  API Readiness:  {ready.get('status', 'unknown').upper():<15}")
    if ready.get('details'):
        details = ready.get('details', {})
        checks = details.get('checks', {})
        # Convert boolean to readable status
        db_status = "✅ connected" if checks.get('database') else "❌ disconnected"
        qdrant_status = "✅ connected" if checks.get('qdrant') else "❌ disconnected"
        ollama_status = "✅ connected" if checks.get('ollama') else "❌ disconnected"
        model_status = "✅ loaded" if checks.get('model') else "❌ not loaded"
        print(f"    - Database:    {db_status}")
        print(f"    - Qdrant:      {qdrant_status}")
        print(f"    - Ollama:      {ollama_status}")
        print(f"    - Model:       {model_status}")
    print()
    
    # Container Stats
    print("🐳 CONTAINER STATUS")
    print("-" * 80)
    for container, stats in containers.items():
        container_name = container.replace("ecommerce-", "")
        if "error" in stats or "not_running" in stats.values():
            status = "❌ NOT RUNNING"
        else:
            cpu = stats.get("cpu_percent", "0")
            mem = stats.get("memory_percent", "0")
            status = f"✅ RUNNING (CPU: {cpu}%, Mem: {mem}%)"
        print(f"  {container_name:<20} {status}")
    print()
    
    # Database Connections
    print("💾 DATABASE CONNECTIONS")
    print("-" * 80)
    if "error" not in db_conn and "note" not in db_conn:
        active = db_conn.get("active_connections", 0)
        max_conn = db_conn.get("max_connections", 150)
        util = db_conn.get("utilization_percent", 0)
        print(f"  Active Connections: {active}/{max_conn} ({util}% utilization)")
        if util > 80:
            print(f"  ⚠️  WARNING: High connection pool utilization!")
        elif util > 60:
            print(f"  ⚠️  CAUTION: Moderate connection pool utilization")
    elif "note" in db_conn:
        print(f"  ℹ️  {db_conn.get('note')}")
        print(f"  Pool Config: 100 base + 200 overflow = 300 max connections")
    else:
        print(f"  ⚠️  Could not fetch connection stats")
        print(f"  Pool Config: 100 base + 200 overflow = 300 max connections")
    print()
    
    # API Metrics
    print("📈 API METRICS")
    print("-" * 80)
    metrics_summary = format_metrics_summary(metrics)
    
    if "error" not in metrics:
        # HTTP Requests
        http_req = metrics_summary.get("http_requests", {})
        print(f"  Total Requests:     {http_req.get('total', 0):,}")
        
        # Response Times
        resp_times = metrics_summary.get("response_times", {})
        if resp_times:
            print(f"  Avg Response Time:  {resp_times.get('average_ms', 0):.2f}ms")
            print(f"  Total Processed:    {resp_times.get('total_requests', 0):,}")
        
        # System Resources
        system = metrics_summary.get("system", {})
        if system.get("process_memory_bytes"):
            mem_mb = system["process_memory_bytes"] / (1024 * 1024)
            print(f"  Memory Usage:       {mem_mb:.2f} MB")
        if system.get("process_cpu_seconds"):
            print(f"  CPU Time:           {system['process_cpu_seconds']:.2f}s")
        
        # Endpoint-specific metrics
        endpoint_metrics = {}
        for key, value in metrics.items():
            if "http_requests_total" in key and "endpoint" in key:
                # Parse endpoint from labels if available
                endpoint_metrics[key] = value
        
        if endpoint_metrics:
            print(f"\n  Endpoint Requests:")
            for key, value in sorted(endpoint_metrics.items(), key=lambda x: x[1], reverse=True)[:5]:
                # Try to extract endpoint name
                if "endpoint=" in key:
                    endpoint = key.split('endpoint="')[1].split('"')[0]
                    print(f"    {endpoint:<30} {int(value):,}")
    else:
        print(f"  ⚠️  Error fetching metrics: {metrics.get('error', 'Unknown error')}")
    print()
    
    # Performance Warnings
    print("⚠️  PERFORMANCE WARNINGS")
    print("-" * 80)
    warnings = []
    
    if health.get("response_time_ms", 0) > 1000:
        warnings.append("High API response time (>1s)")
    
    if db_conn.get("utilization_percent", 0) > 80:
        warnings.append("High database connection pool utilization (>80%)")
    
    if metrics_summary.get("response_times", {}).get("average_ms", 0) > 5000:
        warnings.append("High average response time (>5s)")
    
    if not warnings:
        print("  ✅ No performance warnings")
    else:
        for warning in warnings:
            print(f"  ⚠️  {warning}")
    print()
    
    print("="*80)
    print()


def main():
    """Main monitoring function."""
    print("🔍 Collecting system metrics...")
    
    # Collect all metrics
    health = get_health_status()
    ready = get_ready_status()
    metrics = get_metrics()
    containers = get_container_stats()
    db_conn = get_database_connections()
    
    # Print dashboard
    print_dashboard(health, ready, metrics, containers, db_conn)
    
    # Optional: Save to file
    if len(sys.argv) > 1 and sys.argv[1] == "--save":
        output_file = f"reports/system_status_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        data = {
            "timestamp": datetime.now().isoformat(),
            "health": health,
            "ready": ready,
            "metrics": metrics,
            "containers": containers,
            "database_connections": db_conn,
        }
        with open(output_file, "w") as f:
            json.dump(data, f, indent=2)
        print(f"💾 Status saved to: {output_file}")


if __name__ == "__main__":
    main()

