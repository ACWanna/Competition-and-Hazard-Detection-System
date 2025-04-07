import os
from datetime import timedelta

class Config:
    """Flask应用基础配置类"""
    
    # Flask配置
    SECRET_KEY = os.environ.get('SECRET_KEY') or 'dev-key'
    
    # 数据库配置 - 使用SQLite
    SQLALCHEMY_DATABASE_URI = os.environ.get('DATABASE_URL') or \
        'sqlite:///app.db'
    SQLALCHEMY_TRACK_MODIFICATIONS = False
    
    # 跨域配置
    CORS_HEADERS = 'Content-Type'

class DevelopmentConfig(Config):
    """开发环境配置"""
    DEBUG = True
    # 开发环境可以使用内存数据库加速开发
    # SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'

class TestingConfig(Config):
    """测试环境配置"""
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'
    
class ProductionConfig(Config):
    """生产环境配置"""
    DEBUG = False
    TESTING = False
    # 生产环境可以使用更安全的密钥
    SECRET_KEY = os.environ.get('SECRET_KEY') or os.urandom(24) 