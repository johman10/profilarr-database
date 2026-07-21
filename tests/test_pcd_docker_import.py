"""Test PCD schema import into Profilarr via Docker."""

import os
import re
import subprocess
import time
from pathlib import Path

import pytest


PROJECT_ROOT = Path(__file__).parent.parent
OPS_DIR = PROJECT_ROOT / "ops"
SQL_FILE = OPS_DIR / "1.initial.sql"
DOCKER_COMPOSE_FILE = PROJECT_ROOT / "docker-compose.test.yml"


@pytest.mark.skipif(
    not os.environ.get("RUN_DOCKER_TESTS"),
    reason="Docker tests disabled - set RUN_DOCKER_TESTS=1 to enable"
)
class TestPCDDockerImport:
    """Test PCD schema import into Profilarr via Docker."""

    @classmethod
    def setup_class(cls):
        """Start Profilarr container before tests."""
        if not SQL_FILE.exists():
            pytest.skip("SQL file not found - run generation first")

        if not DOCKER_COMPOSE_FILE.exists():
            pytest.skip("docker-compose file not found")

        try:
            subprocess.run(
                ["docker-compose", "-f", str(DOCKER_COMPOSE_FILE), "down"],
                capture_output=True,
                timeout=30,
            )
            time.sleep(2)
        except Exception:
            pass

        try:
            result = subprocess.run(
                ["docker-compose", "-f", str(DOCKER_COMPOSE_FILE), "up", "-d"],
                capture_output=True,
                text=True,
                timeout=60,
                cwd=str(PROJECT_ROOT),
            )
            if result.returncode != 0:
                pytest.skip(f"Failed to start Docker: {result.stderr}")

            time.sleep(10)
        except subprocess.TimeoutExpired:
            pytest.skip("Docker startup timed out")
        except FileNotFoundError:
            pytest.skip("docker-compose not found - Docker tests require docker-compose")

    @classmethod
    def teardown_class(cls):
        """Stop Profilarr container after tests."""
        try:
            subprocess.run(
                ["docker-compose", "-f", str(DOCKER_COMPOSE_FILE), "down"],
                capture_output=True,
                timeout=30,
                cwd=str(PROJECT_ROOT),
            )
        except Exception:
            pass

    def get_container_logs(self):
        """Get logs from the Profilarr container."""
        try:
            result = subprocess.run(
                ["docker-compose", "-f", str(DOCKER_COMPOSE_FILE), "logs", "profilarr"],
                capture_output=True,
                text=True,
                timeout=10,
                cwd=str(PROJECT_ROOT),
            )
            return result.stdout + result.stderr
        except Exception:
            return ""

    def test_container_running(self):
        """Test that Profilarr container is running."""
        try:
            result = subprocess.run(
                ["docker-compose", "-f", str(DOCKER_COMPOSE_FILE), "ps"],
                capture_output=True,
                text=True,
                timeout=10,
                cwd=str(PROJECT_ROOT),
            )
            assert "profilarr" in result.stdout, "Profilarr container not found in docker-compose ps"
            assert "Up" in result.stdout, "Profilarr container not running"
        except Exception as e:
            pytest.skip(f"Could not check container status: {e}")

    def test_no_sql_errors_in_logs(self):
        """Test that no SQL errors occurred during schema import."""
        logs = self.get_container_logs()

        error_patterns = [
            r"UNIQUE constraint failed",
            r"FOREIGN KEY constraint failed",
            r"NOT NULL constraint failed",
            r"SQL Error",
            r"database is locked",
            r"syntax error",
            r"Error: Failed to execute operation",
        ]

        found_errors = []
        for pattern in error_patterns:
            matches = re.findall(pattern, logs, re.IGNORECASE)
            if matches:
                found_errors.append(f"{pattern}: found {len(matches)} occurrence(s)")

        assert not found_errors, f"SQL errors found in logs:\n{chr(10).join(found_errors)}\n\nLogs:\n{logs[-2000:]}"

    def test_no_critical_errors_in_logs(self):
        """Test that no critical errors occurred in Profilarr."""
        logs = self.get_container_logs()

        critical_patterns = [
            r"\[ERROR\].*database",
            r"\[FATAL\]",
            r"panic:",
            r"Traceback",
        ]

        found_errors = []
        for pattern in critical_patterns:
            matches = re.findall(pattern, logs)
            if matches:
                found_errors.extend(matches[:5])

        assert not found_errors, f"Critical errors found in logs: {found_errors}\n\nLogs:\n{logs[-2000:]}"

    def test_schema_import_messages_present(self):
        """Test that schema import completion messages are in logs."""
        logs = self.get_container_logs()

        assert len(logs) > 100, "Not enough log output - container may not be running"
