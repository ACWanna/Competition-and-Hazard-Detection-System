import os
from flask import Flask
from flask_cors import CORS
from flask_sqlalchemy import SQLAlchemy
from flask_migrate import Migrate
from config import Config
import logging
from logging.handlers import RotatingFileHandler

# 初始化扩展
db = SQLAlchemy()
migrate = Migrate()

def create_app(config_name=None):
    """
    创建Flask应用实例
    
    Args:
        config_name: 配置名称
        
    Returns:
        Flask应用实例
    """
    app = Flask(__name__)
    
    # 配置应用
    if config_name is None:
        config_name = os.environ.get('FLASK_CONFIG', 'development')

    # 根据配置名称加载对应的配置类
    if config_name == 'development':
        from config import DevelopmentConfig
        app.config.from_object(DevelopmentConfig)
    elif config_name == 'testing':
        from config import TestingConfig
        app.config.from_object(TestingConfig)
    elif config_name == 'production':
        from config import ProductionConfig
        app.config.from_object(ProductionConfig)
    else:
        from config import Config
        app.config.from_object(Config)
    
    # 配置日志
    # 确保日志目录存在
    if not os.path.exists('logs'):
        os.mkdir('logs')

    # 创建文件日志处理器 - 增加文件大小和备份数量
    file_handler = RotatingFileHandler('logs/app.log', maxBytes=10485760, backupCount=20)  # 10MB一个文件，最多20个备份
    file_handler.setFormatter(logging.Formatter(
        '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'
    ))
    file_handler.setLevel(logging.DEBUG)  # 改为DEBUG级别记录更多日志
    
    # 添加控制台日志处理器，方便调试
    console_handler = logging.StreamHandler()
    console_handler.setFormatter(logging.Formatter(
        '%(asctime)s %(levelname)s: %(message)s [in %(pathname)s:%(lineno)d]'
    ))
    console_handler.setLevel(logging.DEBUG)

    # 添加到应用和根日志器
    app.logger.addHandler(file_handler)
    app.logger.addHandler(console_handler)
    app.logger.setLevel(logging.DEBUG)  # 改为DEBUG级别

    # 配置根日志器，确保所有模块的日志都能被捕获
    root_logger = logging.getLogger()
    root_logger.addHandler(file_handler)
    root_logger.addHandler(console_handler)
    root_logger.setLevel(logging.DEBUG)  # 改为DEBUG级别

    app.logger.info('应用启动')
    
    # 初始化扩展
    db.init_app(app)
    migrate.init_app(app, db)
    CORS(app)
    
    # 注册蓝图
    from app.api import bp as api_bp
    app.register_blueprint(api_bp, url_prefix='/api')
    
    # 添加根路由
    @app.route('/')
    def index():
        return {
            "status": "success",
            "message": "组合逻辑电路竞争与冒险检测系统API服务",
            "version": "1.0",
            "api_docs": "/api/"
        }
    
    # 导入模型以确保它们被注册
    from app.models import database
    
    return app 