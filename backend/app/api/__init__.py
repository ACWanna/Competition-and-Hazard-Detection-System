from flask import Blueprint
from flask_restx import Api

bp = Blueprint('api', __name__)
api = Api(bp,
    title='电路检测API',
    version='1.0',
    description='组合逻辑电路竞争与冒险检测系统API'
)

from app.api import routes 