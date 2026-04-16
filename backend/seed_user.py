"""
Script to seed database with a test user
"""
from app.database import SessionLocal, engine, Base
from app.models.user import User
from app.services.auth_service import hash_password

# Create tables
Base.metadata.create_all(bind=engine)

# Create session
db = SessionLocal()

try:
    # Check if user already exists
    existing_user = db.query(User).filter(User.email == "test@example.com").first()
    if existing_user:
        print("Test user already exists!")
    else:
        # Create test user
        test_user = User(
            username="testuser",
            email="test@example.com",
            hashed_password=hash_password("password123")
        )
        db.add(test_user)
        db.commit()
        print("✓ Test user created successfully!")
        print(f"  Email: test@example.com")
        print(f"  Password: password123")
finally:
    db.close()
