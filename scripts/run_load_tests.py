"""Script to run load tests with different configurations."""
import subprocess
import sys
import json
import time
from pathlib import Path
from datetime import datetime


def run_locust_test(users: int, spawn_rate: int, duration: str, host: str = "http://localhost:8000"):
    """Run a Locust load test."""
    print(f"\n{'='*60}")
    print(f"Running load test: {users} users, spawn rate: {spawn_rate}/s, duration: {duration}")
    print(f"{'='*60}\n")
    
    output_file = f"reports/locust_report_{users}users_{datetime.now().strftime('%Y%m%d_%H%M%S')}.html"
    Path("reports").mkdir(exist_ok=True)
    
    cmd = [
        "locust",
        "-f", "tests/load/locustfile.py",
        "--host", host,
        "--users", str(users),
        "--spawn-rate", str(spawn_rate),
        "--run-time", duration,
        "--headless",
        "--html", output_file,
        "--csv", f"reports/locust_{users}users",
        "--loglevel", "INFO"
    ]
    
    try:
        result = subprocess.run(cmd, check=True, capture_output=True, text=True)
        print(f"✓ Load test completed: {output_file}")
        return output_file
    except subprocess.CalledProcessError as e:
        print(f"✗ Load test failed: {e}")
        print(f"Error output: {e.stderr}")
        return None


def main():
    """Run load tests at different scales."""
    print("="*60)
    print("E-commerce ML Intelligence System - Load Testing")
    print("="*60)
    
    # Test scenarios
    scenarios = [
        {"name": "Low Load", "users": 10, "spawn_rate": 2, "duration": "2m"},
        {"name": "Medium Load", "users": 50, "spawn_rate": 5, "duration": "3m"},
        {"name": "High Load", "users": 200, "spawn_rate": 10, "duration": "5m"},
        {"name": "Stress Test", "users": 500, "spawn_rate": 20, "duration": "5m"},
    ]
    
    results = []
    
    for scenario in scenarios:
        print(f"\n📊 Scenario: {scenario['name']}")
        start_time = time.time()
        
        report_file = run_locust_test(
            users=scenario["users"],
            spawn_rate=scenario["spawn_rate"],
            duration=scenario["duration"]
        )
        
        elapsed = time.time() - start_time
        
        if report_file:
            results.append({
                "scenario": scenario["name"],
                "users": scenario["users"],
                "spawn_rate": scenario["spawn_rate"],
                "duration": scenario["duration"],
                "report_file": report_file,
                "elapsed_time": elapsed
            })
        
        # Wait between tests
        if scenario != scenarios[-1]:
            print("\n⏳ Waiting 30 seconds before next test...")
            time.sleep(30)
    
    # Summary
    print("\n" + "="*60)
    print("Load Testing Summary")
    print("="*60)
    
    for result in results:
        print(f"\n{result['scenario']}:")
        print(f"  Users: {result['users']}")
        print(f"  Report: {result['report_file']}")
        print(f"  Duration: {result['elapsed_time']:.1f}s")
    
    # Save results
    results_file = f"reports/load_test_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
    with open(results_file, "w") as f:
        json.dump(results, f, indent=2)
    
    print(f"\n✓ Results saved to: {results_file}")
    print("\n" + "="*60)


if __name__ == "__main__":
    main()



