"""Test API endpoints with trained model."""
import sys
import requests
import json
from pathlib import Path

# Add src to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.core.logging import setup_logging

logger = setup_logging()

API_BASE_URL = "http://localhost:8000"


def test_health():
    """Test health endpoint."""
    logger.info("Testing /health endpoint...")
    try:
        response = requests.get(f"{API_BASE_URL}/health", timeout=5)
        response.raise_for_status()
        logger.info(f"✓ Health check passed: {response.json()}")
        return True
    except Exception as e:
        logger.error(f"✗ Health check failed: {e}")
        return False


def test_ready():
    """Test readiness endpoint."""
    logger.info("Testing /ready endpoint...")
    try:
        response = requests.get(f"{API_BASE_URL}/ready", timeout=5)
        if response.status_code == 200:
            logger.info(f"✓ Ready check passed: {response.json()}")
            return True
        else:
            logger.warning(f"⚠ Service not ready: {response.json()}")
            return False
    except Exception as e:
        logger.error(f"✗ Ready check failed: {e}")
        return False


def test_predict_discount():
    """Test prediction endpoint."""
    logger.info("Testing /v1/predict_discount endpoint...")
    
    test_cases = [
        {
            "actual_price": 100.0,
            "category": "Electronics",
            "rating": 4.5,
            "rating_count": 1000,
        },
        {
            "actual_price": 50.0,
            "category": "Clothing",
            "rating": 3.8,
        },
        {
            "actual_price": 200.0,
            "category": "Home & Kitchen",
        },
    ]
    
    results = []
    for i, test_case in enumerate(test_cases, 1):
        try:
            logger.info(f"  Test case {i}: {test_case}")
            response = requests.post(
                f"{API_BASE_URL}/v1/predict_discount",
                json=test_case,
                timeout=10
            )
            response.raise_for_status()
            result = response.json()
            logger.info(f"    ✓ Prediction: {result['predicted_discount']:.2f}% (confidence: {result['confidence_score']:.2f})")
            results.append(result)
        except Exception as e:
            logger.error(f"    ✗ Failed: {e}")
            results.append({"error": str(e)})
    
    return results


def test_explain():
    """Test explanation endpoint."""
    logger.info("Testing /v1/explain endpoint...")
    
    test_case = {
        "actual_price": 100.0,
        "category": "Electronics",
        "rating": 4.5,
    }
    
    try:
        response = requests.post(
            f"{API_BASE_URL}/v1/explain",
            json=test_case,
            timeout=10
        )
        response.raise_for_status()
        result = response.json()
        logger.info(f"✓ Explanation generated")
        logger.info(f"  Prediction: {result['predicted_discount']:.2f}%")
        logger.info(f"  Top features in explanation: {list(result.get('explanation', {}).get('feature_importance', {}).keys())[:3]}")
        return result
    except Exception as e:
        logger.error(f"✗ Explanation failed: {e}")
        return None


def main():
    """Run all API tests."""
    logger.info("=" * 60)
    logger.info("API TESTING")
    logger.info("=" * 60)
    
    # Check if API is running
    if not test_health():
        logger.error("API is not running. Please start it with: docker-compose up -d")
        return
    
    # Test readiness
    test_ready()
    
    # Test prediction
    logger.info("\n" + "-" * 60)
    predictions = test_predict_discount()
    
    # Test explanation
    logger.info("\n" + "-" * 60)
    explanation = test_explain()
    
    # Summary
    logger.info("\n" + "=" * 60)
    logger.info("TEST SUMMARY")
    logger.info("=" * 60)
    logger.info(f"Predictions tested: {len(predictions)}")
    logger.info(f"Explanation tested: {'✓' if explanation else '✗'}")
    
    # Save results
    results = {
        'predictions': predictions,
        'explanation': explanation,
    }
    
    output_path = "models/api_test_results.json"
    Path(output_path).parent.mkdir(parents=True, exist_ok=True)
    with open(output_path, 'w') as f:
        json.dump(results, f, indent=2)
    
    logger.info(f"\nTest results saved to: {output_path}")


if __name__ == "__main__":
    main()

