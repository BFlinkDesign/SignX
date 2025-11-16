"""Locust load testing scenarios for CalcuSign API.

Target SLOs:
- <200ms p95 for derives
- <1s for report generation
- 100 concurrent users
"""

import random
from locust import HttpUser, task, between


class CalcuSignUser(HttpUser):
    """Simulated user for CalcuSign load testing."""
    
    wait_time = between(1, 3)  # 1-3 seconds between tasks
    
    def on_start(self):
        """Set up user session: create a test project."""
        self.project_id = None
        
        # Create project
        project_data = {
            "account_id": f"load_test_account_{random.randint(1, 1000)}",
            "name": f"Load Test Project {random.randint(1, 10000)}",
            "customer": "Load Test Customer",
            "created_by": f"load_test_user_{random.randint(1, 1000)}",
        }
        
        resp = self.client.post("/projects/", json=project_data, catch_response=True)
        if resp.status_code == 200:
            data = resp.json()
            self.project_id = data.get("result", {}).get("project_id")
            resp.success()
        else:
            resp.failure(f"Failed to create project: {resp.status_code}")
    
    @task(3)
    def create_project(self):
        """Create a new project (30% of tasks)."""
        project_data = {
            "account_id": f"test_account_{random.randint(1, 1000)}",
            "name": f"Project {random.randint(1, 10000)}",
            "created_by": f"user_{random.randint(1, 1000)}",
        }
        
        with self.client.post(
            "/projects/",
            json=project_data,
            catch_response=True,
            name="POST /projects/"
        ) as resp:
            if resp.status_code == 200:
                resp.success()
            else:
                resp.failure(f"Status {resp.status_code}")
    
    @task(5)
    def derive_cabinet(self):
        """Derive cabinet properties (50% of tasks)."""
        cabinet_data = {
            "sign": {
                "height_ft": random.uniform(8, 12),
                "width_ft": random.uniform(6, 10),
            },
            "board": {
                "layers": [
                    {"material": "aluminum", "thickness_in": 0.125},
                ]
            },
        }
        
        with self.client.post(
            "/cabinets/derive",
            json=cabinet_data,
            catch_response=True,
            name="POST /cabinets/derive"
        ) as resp:
            if resp.status_code in (200, 422):
                resp.success()
            else:
                resp.failure(f"Status {resp.status_code}")
    
    @task(4)
    def get_pole_options(self):
        """Get pole options (40% of tasks)."""
        options_data = {
            "loads": {"moment_kips_ft": random.uniform(50, 200)},
            "preferences": {},
        }
        
        with self.client.post(
            "/poles/options",
            json=options_data,
            catch_response=True,
            name="POST /poles/options"
        ) as resp:
            if resp.status_code in (200, 422):
                resp.success()
            else:
                resp.failure(f"Status {resp.status_code}")
    
    @task(3)
    def design_foundation(self):
        """Design foundation (30% of tasks)."""
        foundation_data = {
            "module": "signage.direct_burial_2pole",
            "loads": {"force_kips": random.uniform(30, 100)},
        }
        
        with self.client.post(
            "/footing/design",
            json=foundation_data,
            catch_response=True,
            name="POST /footing/design"
        ) as resp:
            if resp.status_code in (200, 422):
                resp.success()
            else:
                resp.failure(f"Status {resp.status_code}")
    
    @task(2)
    def get_project(self):
        """Retrieve project (20% of tasks)."""
        if self.project_id:
            with self.client.get(
                f"/projects/{self.project_id}",
                catch_response=True,
                name="GET /projects/{id}"
            ) as resp:
                if resp.status_code in (200, 404):
                    resp.success()
                else:
                    resp.failure(f"Status {resp.status_code}")
    
    @task(1)
    def list_projects(self):
        """List projects (10% of tasks)."""
        with self.client.get(
            "/projects/",
            catch_response=True,
            name="GET /projects/"
        ) as resp:
            if resp.status_code == 200:
                resp.success()
            else:
                resp.failure(f"Status {resp.status_code}")
    
    @task(1)
    def submit_project(self):
        """Submit project (10% of tasks)."""
        if self.project_id:
            with self.client.post(
                f"/projects/{self.project_id}/submit",
                json={"actor": "load_test_user"},
                headers={"Idempotency-Key": f"test_key_{random.randint(1, 1000)}"},
                catch_response=True,
                name="POST /projects/{id}/submit"
            ) as resp:
                if resp.status_code in (200, 422):
                    resp.success()
                else:
                    resp.failure(f"Status {resp.status_code}")
    
    @task(1)
    def health_check(self):
        """Health check (10% of tasks)."""
        with self.client.get("/health", catch_response=True, name="GET /health") as resp:
            if resp.status_code == 200:
                resp.success()
            else:
                resp.failure(f"Status {resp.status_code}")


class ReportGenerationUser(HttpUser):
    """Specialized user for report generation load testing."""
    
    wait_time = between(2, 5)
    weight = 1  # 10% of users
    
    @task
    def generate_report(self):
        """Generate PDF report (target: <1s)."""
        payload = {
            "module": "signage.single_pole",
            "config": {
                "request": {
                    "sign": {"height_ft": random.uniform(8, 12), "width_ft": random.uniform(6, 10)},
                    "site": {"v_design_mph": 90},
                },
                "selected": {
                    "pole": {"name": "4x6", "material": "steel"},
                    "foundation": {"depth_ft": 6.0},
                },
                "loads": {"moment_kip_ft": random.uniform(100, 200)},
            },
            "files": [],
            "cost_snapshot": {"total": random.uniform(3000, 8000)},
        }
        
        with self.client.post(
            "/projects/dummy/report",
            json=payload,
            catch_response=True,
            name="POST /projects/{id}/report"
        ) as resp:
            # Note: report generation may be async
            if resp.status_code in (200, 202):
                resp.success()
            else:
                resp.failure(f"Status {resp.status_code}")

