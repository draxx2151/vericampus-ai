import unittest
from app.main import health_check, read_root, app

class TestMainBackend(unittest.TestCase):
    def test_health_endpoint(self):
        response = health_check()
        self.assertEqual(response["status"], "ok")
        self.assertEqual(response["message"], "VeriCampus AI backend is running")

    def test_root_endpoint(self):
        response = read_root()
        self.assertEqual(response["status"], "ok")
        self.assertIn("VeriCampus", response["message"])

    def test_app_metadata(self):
        self.assertEqual(app.title, "VeriCampus AI Backend API")

if __name__ == '__main__':
    unittest.main()
