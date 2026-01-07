from app import app, db, User, Election
from sqlalchemy import text

def test_connection():
    with app.app_context():
        try:
            # Test raw SQL connection
            result = db.session.execute(text('SELECT 1'))
            print("✓ Database connection successful!")
            
            # Test table access
            user_count = User.query.count()
            print(f"✓ Found {user_count} users in database")
            
            election_count = Election.query.count()
            print(f"✓ Found {election_count} elections in database")
            
            # Test admin user
            admin = User.query.filter_by(email='admin@voting.com').first()
            if admin:
                print(f"✓ Admin user found: {admin.full_name}")
            
            print("\n All database tests passed!")
            
        except Exception as e:
            print(f" Database connection failed: {e}")

if __name__ == '__main__':
    test_connection()