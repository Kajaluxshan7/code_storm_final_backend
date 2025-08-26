"""
Database Connection Tests
Test PostgreSQL database connectivity and operations
"""
import pytest
from sqlalchemy import text
from sqlalchemy.exc import OperationalError

from app.core.database import engine, SessionLocal, get_db
from app.core.config import settings


class TestDatabaseConnection:
    """Test database connection and basic operations"""
    
    def test_database_connection(self):
        """Test basic database connectivity"""
        try:
            with engine.connect() as connection:
                result = connection.execute(text("SELECT 1"))
                assert result.fetchone()[0] == 1
        except OperationalError as e:
            pytest.fail(f"Database connection failed: {e}")
    
    def test_database_session(self):
        """Test database session creation"""
        db = SessionLocal()
        try:
            result = db.execute(text("SELECT version()"))
            version = result.fetchone()[0]
            assert "PostgreSQL" in version
        finally:
            db.close()
    
    def test_get_db_dependency(self):
        """Test database dependency injection"""
        db_generator = get_db()
        db = next(db_generator)
        
        try:
            result = db.execute(text("SELECT current_database()"))
            db_name = result.fetchone()[0]
            assert db_name is not None
        finally:
            next(db_generator, None)  # Close the generator
    
    @pytest.mark.asyncio
    async def test_database_settings(self):
        """Test database configuration settings"""
        assert settings.DB_HOST is not None
        assert settings.DB_PORT is not None
        assert settings.DB_USER is not None
        assert settings.DB_NAME is not None
        assert settings.DATABASE_URL is not None
        
        # Verify DATABASE_URL format
        assert "postgresql://" in settings.DATABASE_URL
        assert settings.DB_HOST in settings.DATABASE_URL
        assert str(settings.DB_PORT) in settings.DATABASE_URL
    
    def test_database_table_creation(self, db_session):
        """Test table creation and basic CRUD operations"""
        # This test uses the test database session from conftest.py
        
        # Test creating a simple table
        db_session.execute(text("""
            CREATE TABLE IF NOT EXISTS test_table (
                id SERIAL PRIMARY KEY,
                name VARCHAR(100) NOT NULL,
                created_at TIMESTAMP DEFAULT CURRENT_TIMESTAMP
            )
        """))
        db_session.commit()
        
        # Test inserting data
        db_session.execute(text("""
            INSERT INTO test_table (name) VALUES ('test_record')
        """))
        db_session.commit()
        
        # Test querying data
        result = db_session.execute(text("""
            SELECT name FROM test_table WHERE name = 'test_record'
        """))
        record = result.fetchone()
        assert record is not None
        assert record[0] == 'test_record'
        
        # Test cleanup
        db_session.execute(text("DROP TABLE IF EXISTS test_table"))
        db_session.commit()


class TestDatabasePerformance:
    """Test database performance and connection pooling"""
    
    def test_connection_pool(self):
        """Test connection pooling functionality"""
        connections = []
        
        try:
            # Create multiple connections
            for _ in range(5):
                conn = engine.connect()
                connections.append(conn)
                
                # Test each connection
                result = conn.execute(text("SELECT 1"))
                assert result.fetchone()[0] == 1
                
        finally:
            # Close all connections
            for conn in connections:
                conn.close()
    
    def test_concurrent_sessions(self):
        """Test multiple concurrent database sessions"""
        sessions = []
        
        try:
            # Create multiple sessions
            for _ in range(3):
                session = SessionLocal()
                sessions.append(session)
                
                # Test each session
                result = session.execute(text("SELECT current_timestamp"))
                assert result.fetchone()[0] is not None
                
        finally:
            # Close all sessions
            for session in sessions:
                session.close()
