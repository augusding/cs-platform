"""
压测文件。
运行：
  locust -f tests/locustfile.py --headless -u 50 -r 5 --run-time 3m \
         --host http://localhost:8080 \
         --html tests/load_report.html

目标：50 并发下 p95 < 5s，error rate < 1%。
运行前请把下面的 TEST_TOKEN / TEST_BOT_ID 替换为真实值。
"""
import os

from locust import HttpUser, between, task

TEST_TOKEN = os.getenv("LOCUST_TOKEN", "YOUR_ACCESS_TOKEN")
TEST_BOT_ID = os.getenv("LOCUST_BOT_ID", "YOUR_BOT_ID")


class CSUser(HttpUser):
    wait_time = between(1, 3)

    @task(3)
    def health_check(self):
        self.client.get("/health")

    @task(5)
    def get_bots(self):
        self.client.get(
            "/api/bots",
            headers={"Authorization": f"Bearer {TEST_TOKEN}"},
        )

    @task(2)
    def billing_plans(self):
        self.client.get("/api/billing/plans")

    @task(1)
    def get_stats(self):
        self.client.get(
            "/api/admin/stats",
            headers={"Authorization": f"Bearer {TEST_TOKEN}"},
        )
