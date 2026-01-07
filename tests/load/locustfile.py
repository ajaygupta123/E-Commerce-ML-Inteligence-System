"""Locust load testing configuration."""
from locust import HttpUser, task, between
import random


class LightUser(HttpUser):
    """Light user - mostly reads, occasional predictions."""
    wait_time = between(2, 5)
    weight = 3  # 60% of users
    
    @task(5)
    def health_check(self):
        """Check health endpoint."""
        self.client.get("/health")
    
    @task(2)
    def predict_discount(self):
        """Make prediction."""
        self.client.post(
            "/v1/predict_discount",
            json={
                "category": random.choice(["Electronics", "Clothing", "Home", "Sports"]),
                "actual_price": random.uniform(50, 500),
                "rating": random.uniform(3.0, 5.0),
            }
        )
    
    @task(1)
    def answer_question(self):
        """Ask a question."""
        questions = [
            "What are the best products?",
            "Show me electronics",
            "What products are under 100?",
        ]
        self.client.post(
            "/v1/answer_question",
            json={
                "question": random.choice(questions),
                "top_k": 3,
            }
        )


class MediumUser(HttpUser):
    """Medium user - balanced read/write."""
    wait_time = between(1, 3)
    weight = 2  # 30% of users
    
    @task(3)
    def predict_discount(self):
        """Make prediction."""
        self.client.post(
            "/v1/predict_discount",
            json={
                "category": random.choice(["Electronics", "Clothing", "Home", "Sports"]),
                "actual_price": random.uniform(50, 500),
                "rating": random.uniform(3.0, 5.0),
                "rating_count": random.randint(10, 1000),
            }
        )
    
    @task(2)
    def explain_prediction(self):
        """Get explanation."""
        self.client.post(
            "/v1/explain",
            json={
                "category": random.choice(["Electronics", "Clothing", "Home"]),
                "actual_price": random.uniform(50, 500),
                "rating": random.uniform(3.0, 5.0),
            }
        )
    
    @task(2)
    def answer_question(self):
        """Ask a question."""
        questions = [
            "What are the best products?",
            "Compare these laptops",
            "Show me electronics under 500",
            "What products have high ratings?",
        ]
        self.client.post(
            "/v1/answer_question",
            json={
                "question": random.choice(questions),
                "top_k": 5,
            }
        )
    
    @task(1)
    def health_check(self):
        """Check health."""
        self.client.get("/health")


class HeavyUser(HttpUser):
    """Heavy user - lots of predictions and questions."""
    wait_time = between(0.5, 2)
    weight = 1  # 10% of users
    
    @task(5)
    def predict_discount(self):
        """Make many predictions."""
        self.client.post(
            "/v1/predict_discount",
            json={
                "category": random.choice(["Electronics", "Clothing", "Home", "Sports", "Books"]),
                "actual_price": random.uniform(20, 1000),
                "rating": random.uniform(2.0, 5.0),
                "rating_count": random.randint(0, 5000),
            }
        )
    
    @task(3)
    def explain_prediction(self):
        """Get many explanations."""
        self.client.post(
            "/v1/explain",
            json={
                "category": random.choice(["Electronics", "Clothing", "Home"]),
                "actual_price": random.uniform(50, 500),
                "rating": random.uniform(3.0, 5.0),
            }
        )
    
    @task(3)
    def answer_question(self):
        """Ask many questions."""
        questions = [
            "What are the best products?",
            "Compare these products",
            "Show me cheap electronics",
            "What products have good reviews?",
            "What is the price range?",
        ]
        self.client.post(
            "/v1/answer_question",
            json={
                "question": random.choice(questions),
                "top_k": random.randint(3, 10),
            }
        )
    
    @task(1)
    def health_check(self):
        """Check health."""
        self.client.get("/health")


# Legacy class for backward compatibility
class EcommerceUser(LightUser):
    """Legacy user class - alias for LightUser."""
    pass


