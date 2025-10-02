import os
from flask import current_app, g
from pymongo import MongoClient
from pymongo.errors import ConnectionFailure, ConfigurationError

def get_db():
    if 'db' not in g:
        mongo_uri = os.environ.get('MONGO_URI')
        if not mongo_uri:
            raise ValueError('MONGO_URI is not configured in the application settings')
        try:
            client = MongoClient(mongo_uri, serverSelectionTimeoutMS=5000)
            # Test the connection
            client.admin.command('ping')
            g.db = client.get_default_database()
        except (ConnectionFailure, ConfigurationError) as e:
            current_app.logger.error(f'Failed to connect to MongoDB: {str(e)}')
            raise
    return g.db

def close_db(e=None):
    db = g.pop('db', None)
    if db is not None:
        db.client.close()

def init_app(app):
    """Register database functions with the Flask app."""
    # Ensure MONGO_URI is set in the app config
    if not app.config.get('MONGO_URI'):
        app.config['MONGO_URI'] = os.getenv('MONGO_URI')
    
    app.teardown_appcontext(close_db)

