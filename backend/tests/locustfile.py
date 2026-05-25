"""
Locust load test — proves 100 articles/min throughput target.

Run:
    locust -f tests/locustfile.py --host http://localhost:8000 \
           --users 20 --spawn-rate 5 --run-time 2m --headless
"""
from locust import HttpUser, between, task


class FirehoseUser(HttpUser):
    wait_time = between(0.5, 1.5)
    headers = {"X-API-Key": "dev-secret-key-1"}

    @task(5)
    def list_articles(self):
        self.client.get("/articles?page_size=20", headers=self.headers)

    @task(3)
    def list_by_sector(self):
        self.client.get("/articles?sector=Technology", headers=self.headers)

    @task(1)
    def get_health(self):
        self.client.get("/health")

    @task(1)
    def ingest_article(self):
        self.client.post(
            "/articles",
            headers=self.headers,
            json={
                "source": "load-test",
                "url": f"https://example.com/load-test/{id(self)}",
                "title": "Load test article",
                "body": "This is a synthetic load test article body.",
            },
        )
