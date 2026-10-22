import unittest
from app import app, db, User, Course

class CourseHubTests(unittest.TestCase):
    def setUp(self):
        app.config.update(TESTING=True, SQLALCHEMY_DATABASE_URI="sqlite://")
        with app.app_context():
            db.drop_all()
            db.create_all()
            db.session.add(Course(title="Test Course", description="A test course", category="Testing", level="Beginner", instructor="Test", duration_hours=2))
            db.session.commit()
        self.client = app.test_client()

    def tearDown(self):
        with app.app_context():
            db.session.remove()
            db.drop_all()

    def test_home_loads(self):
        response = self.client.get("/")
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"CourseHub", response.data)

    def test_register_and_login(self):
        response = self.client.post("/register", data={"name":"Test Student","email":"student@example.com","password":"strongpass123"}, follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        response = self.client.post("/login", data={"email":"student@example.com","password":"strongpass123"}, follow_redirects=True)
        self.assertEqual(response.status_code, 200)
        self.assertIn(b"My courses", response.data)

if __name__ == "__main__":
    unittest.main()
