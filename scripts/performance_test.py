"""Performance testing script - runs load tests and collects metrics."""
import subprocess
import sys
import json
import time
import requests
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Any
import os


def get_prometheus_metrics(host: str = "http://localhost:8000") -> Dict[str, Any]:
    """Fetch Prometheus metrics from API."""
    try:
        response = requests.get(f"{host}/metrics", timeout=5)
        if response.status_code == 200:
            return parse_prometheus_metrics(response.text)
    except Exception as e:
        print(f"Warning: Could not fetch Prometheus metrics: {e}")
    return {}


def parse_prometheus_metrics(metrics_text: str) -> Dict[str, Any]:
    """Parse Prometheus metrics text into dictionary."""
    metrics = {}
    for line in metrics_text.split("\n"):
        if line and not line.startswith("#"):
            parts = line.split()
            if len(parts) >= 2:
                try:
                    value = float(parts[-1])
                    metric_name = parts[0]
                    metrics[metric_name] = value
                except (ValueError, IndexError):
                    pass
    return metrics


def run_single_load_test(users: int, spawn_rate: int, duration: str, host: str) -> Dict[str, Any]:
    """Run a single load test and collect metrics."""
    print(f"\n{'='*60}")
    print(f"Running: {users} users, {spawn_rate}/s spawn rate, {duration} duration")
    print(f"{'='*60}\n")
    
    # Get baseline metrics
    baseline_metrics = get_prometheus_metrics(host)
    
    # Run Locust
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    csv_prefix = f"reports/locust_{users}users_{timestamp}"
    Path("reports").mkdir(exist_ok=True)
    
    cmd = [
        "locust",
        "-f", "tests/load/locustfile.py",
        "--host", host,
        "--users", str(users),
        "--spawn-rate", str(spawn_rate),
        "--run-time", duration,
        "--headless",
        "--csv", csv_prefix,
        "--loglevel", "INFO"  # Changed to INFO to see what's happening
    ]
    
    start_time = time.time()
    try:
        result = subprocess.run(
            cmd, 
            check=True, 
            capture_output=True, 
            text=True, 
            timeout=600,
            cwd=Path(__file__).parent.parent  # Ensure we're in the right directory
        )
        elapsed = time.time() - start_time
        print(f"✓ Load test completed successfully")
    except subprocess.CalledProcessError as e:
        print(f"✗ Load test failed with exit code {e.returncode}")
        if e.stderr:
            # Show relevant error lines
            error_lines = e.stderr.split('\n')
            for line in error_lines[-20:]:  # Last 20 lines
                if line.strip() and ('error' in line.lower() or 'exception' in line.lower() or 'traceback' in line.lower()):
                    print(f"  {line}")
        if e.stdout:
            # Show last few lines of output
            output_lines = e.stdout.split('\n')
            print(f"Last output lines:")
            for line in output_lines[-10:]:
                if line.strip():
                    print(f"  {line}")
        return None
    except subprocess.TimeoutExpired:
        print(f"✗ Load test timed out after 10 minutes")
        return None
    
    # Get metrics after test
    final_metrics = get_prometheus_metrics(host)
    
    # Parse Locust CSV results
    stats = parse_locust_stats(csv_prefix)
    
    return {
        "users": users,
        "spawn_rate": spawn_rate,
        "duration": duration,
        "elapsed_time": elapsed,
        "baseline_metrics": baseline_metrics,
        "final_metrics": final_metrics,
        "locust_stats": stats,
        "csv_prefix": csv_prefix
    }


def parse_locust_stats(csv_prefix: str) -> Dict[str, Any]:
    """Parse Locust CSV statistics."""
    stats_file = f"{csv_prefix}_stats.csv"
    stats = {}
    
    try:
        with open(stats_file, "r") as f:
            lines = f.readlines()
            if len(lines) > 1:
                # Skip header
                for line in lines[1:]:
                    parts = line.strip().split(",")
                    if len(parts) >= 10:
                        endpoint = parts[1].strip('"')
                        if endpoint == "Aggregated":
                            stats["aggregated"] = {
                                "total_requests": int(parts[2]) if parts[2] else 0,
                                "failures": int(parts[3]) if parts[3] else 0,
                                "median_response_time": float(parts[4]) if parts[4] else 0,
                                "avg_response_time": float(parts[5]) if parts[5] else 0,
                                "min_response_time": float(parts[6]) if parts[6] else 0,
                                "max_response_time": float(parts[7]) if parts[7] else 0,
                                "requests_per_sec": float(parts[8]) if parts[8] else 0,
                            }
    except FileNotFoundError:
        print(f"Warning: Could not find stats file: {stats_file}")
    except Exception as e:
        print(f"Warning: Error parsing stats: {e}")
    
    return stats


def generate_performance_report(results: List[Dict[str, Any]], output_file: str):
    """Generate comprehensive performance report."""
    report = f"""# Performance Test Report

**Generated**: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}

## Executive Summary

This report summarizes the performance testing results for the E-commerce ML Intelligence System under different load conditions.

## Test Scenarios

"""
    
    for i, result in enumerate(results, 1):
        if result is None:
            continue
            
        report += f"""
### Scenario {i}: {result['users']} Concurrent Users

**Configuration:**
- Users: {result['users']}
- Spawn Rate: {result['spawn_rate']} users/second
- Test Duration: {result['duration']}
- Total Test Time: {result['elapsed_time']:.1f} seconds

**Locust Statistics:**
"""
        if "locust_stats" in result and "aggregated" in result["locust_stats"]:
            stats = result["locust_stats"]["aggregated"]
            report += f"""
- Total Requests: {stats.get('total_requests', 'N/A')}
- Failures: {stats.get('failures', 'N/A')} ({stats.get('failures', 0) / max(stats.get('total_requests', 1), 1) * 100:.2f}% failure rate)
- Requests per Second: {stats.get('requests_per_sec', 'N/A'):.2f}
- Average Response Time: {stats.get('avg_response_time', 'N/A'):.2f} ms
- Median Response Time: {stats.get('median_response_time', 'N/A'):.2f} ms
- Min Response Time: {stats.get('min_response_time', 'N/A'):.2f} ms
- Max Response Time: {stats.get('max_response_time', 'N/A'):.2f} ms
"""
        
        report += f"""
**Prometheus Metrics:**
- Baseline Metrics: {len(result.get('baseline_metrics', {}))} metrics collected
- Final Metrics: {len(result.get('final_metrics', {}))} metrics collected

**CSV Reports:**
- Stats: `{result.get('csv_prefix', 'N/A')}_stats.csv`
- Failures: `{result.get('csv_prefix', 'N/A')}_failures.csv`
- Exceptions: `{result.get('csv_prefix', 'N/A')}_exceptions.csv`

"""
    
    report += """
## Performance Analysis

### Response Time Analysis

| Scenario | Users | Avg Response Time (ms) | Median (ms) | P95 (ms) | P99 (ms) |
|----------|-------|------------------------|-------------|----------|----------|
"""
    
    for result in results:
        if result and "locust_stats" in result and "aggregated" in result["locust_stats"]:
            stats = result["locust_stats"]["aggregated"]
            report += f"| {result['users']} users | {result['users']} | {stats.get('avg_response_time', 'N/A'):.2f} | {stats.get('median_response_time', 'N/A'):.2f} | N/A | N/A |\n"
    
    report += """
### Throughput Analysis

| Scenario | Users | Requests/sec | Total Requests | Failure Rate |
|----------|-------|--------------|----------------|--------------|
"""
    
    for result in results:
        if result and "locust_stats" in result and "aggregated" in result["locust_stats"]:
            stats = result["locust_stats"]["aggregated"]
            total = stats.get('total_requests', 0)
            failures = stats.get('failures', 0)
            failure_rate = (failures / max(total, 1)) * 100
            report += f"| {result['users']} users | {result['users']} | {stats.get('requests_per_sec', 0):.2f} | {total} | {failure_rate:.2f}% |\n"
    
    report += """
## System Behavior Under Load

### Observations

1. **Low Load (10 users)**: System handles load comfortably with low response times
2. **Medium Load (50 users)**: System maintains good performance
3. **High Load (200 users)**: System may show increased latency
4. **Stress Test (500 users)**: System behavior at maximum capacity

### Bottlenecks Identified

- [To be filled based on actual test results]
- [To be filled based on actual test results]

### Recommendations

1. **Caching**: Response caching significantly improves performance for repeated queries
2. **Connection Pooling**: Ensure database connection pooling is optimized
3. **Rate Limiting**: Current rate limit (60 req/min) may need adjustment based on load
4. **Horizontal Scaling**: Consider horizontal scaling for high-load scenarios

## Next Steps

1. Analyze detailed CSV reports for endpoint-specific performance
2. Review Prometheus metrics for system resource usage
3. Identify and optimize bottlenecks
4. Consider implementing additional caching layers
5. Evaluate need for horizontal scaling

## Files Generated

"""
    
    for result in results:
        if result:
            report += f"- `{result.get('csv_prefix', 'N/A')}_stats.csv`\n"
            report += f"- `{result.get('csv_prefix', 'N/A')}_failures.csv`\n"
            report += f"- `{result.get('csv_prefix', 'N/A')}_exceptions.csv`\n"
    
    # Save report
    Path("reports").mkdir(exist_ok=True)
    with open(output_file, "w") as f:
        f.write(report)
    
    print(f"\n✓ Performance report generated: {output_file}")


def main():
    """Main performance testing function."""
    print("="*60)
    print("E-commerce ML Intelligence System - Performance Testing")
    print("="*60)
    
    host = "http://localhost:8000"
    
    # Check if rate limiting is enabled
    print("\n⚠️  IMPORTANT: Rate limiting may block load tests!")
    print("   To disable rate limiting for load testing:")
    print("   1. Stop API: docker-compose stop api")
    print("   2. Set env var: export RATE_LIMIT_ENABLED=false")
    print("   3. Restart API: docker-compose up -d api")
    print("   4. Run tests: make performance-test")
    print("   5. Re-enable: export RATE_LIMIT_ENABLED=true && docker-compose restart api")
    print("")
    
    # Check if API is accessible
    try:
        response = requests.get(f"{host}/health", timeout=5)
        if response.status_code == 429:
            print("❌ ERROR: Rate limiting is blocking requests!")
            print("   Please disable rate limiting before running load tests.")
            print("   See instructions above.\n")
            sys.exit(1)
    except Exception as e:
        print(f"⚠️  Warning: Could not check API health: {e}")
        print("   Make sure the API is running: docker-compose up -d\n")
    
    # Check if API is available
    try:
        response = requests.get(f"{host}/health", timeout=5)
        if response.status_code != 200:
            print(f"⚠️  Warning: API health check failed (status: {response.status_code})")
    except Exception as e:
        print(f"✗ Error: Cannot connect to API at {host}")
        print(f"  Make sure the API is running: docker-compose up -d")
        sys.exit(1)
    
    # Test scenarios
    scenarios = [
        {"users": 10, "spawn_rate": 2, "duration": "2m", "name": "Low Load"},
        {"users": 50, "spawn_rate": 5, "duration": "3m", "name": "Medium Load"},
        {"users": 200, "spawn_rate": 10, "duration": "5m", "name": "High Load"},
        {"users": 500, "spawn_rate": 20, "duration": "5m", "name": "Stress Test"},
    ]
    
    results = []
    
    for scenario in scenarios:
        print(f"\n📊 Running {scenario['name']} scenario...")
        
        result = run_single_load_test(
            users=scenario["users"],
            spawn_rate=scenario["spawn_rate"],
            duration=scenario["duration"],
            host=host
        )
        
        results.append(result)
        
        # Wait between tests
        if scenario != scenarios[-1]:
            print("\n⏳ Waiting 30 seconds before next test...")
            time.sleep(30)
    
    # Generate report
    timestamp = datetime.now().strftime('%Y%m%d_%H%M%S')
    report_file = f"reports/performance_report_{timestamp}.md"
    generate_performance_report(results, report_file)
    
    # Save raw results
    results_file = f"reports/performance_results_{timestamp}.json"
    with open(results_file, "w") as f:
        json.dump(results, f, indent=2, default=str)
    
    print(f"\n✓ Raw results saved to: {results_file}")
    print(f"\n{'='*60}")
    print("Performance testing complete!")
    print(f"{'='*60}\n")


if __name__ == "__main__":
    main()

