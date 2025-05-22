import os

class Config:
    SPATIAL_API_URL = os.getenv('SPATIAL_API_URL', 'http://localhost:4000/spatial-operation/')

class ProductionConfig(Config):
    DEBUG = False

class DevelopmentConfig(Config):
    DEBUG = True