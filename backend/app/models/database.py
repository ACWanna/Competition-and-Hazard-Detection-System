from datetime import datetime, UTC
from app import db

class Circuit(db.Model):
    """电路数据模型"""
    __tablename__ = 'circuits'
    
    id = db.Column(db.Integer, primary_key=True)
    name = db.Column(db.String(100), nullable=False)
    expression = db.Column(db.Text, nullable=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(UTC))
    updated_at = db.Column(db.DateTime, default=lambda: datetime.now(UTC), onupdate=lambda: datetime.now(UTC))
    
    # 关联的门
    gates = db.relationship('Gate', backref='circuit', lazy=True, cascade='all, delete-orphan')
    # 关联的检测结果
    detection_results = db.relationship('DetectionResult', backref='circuit', lazy=True, cascade='all, delete-orphan')

class Gate(db.Model):
    """逻辑门数据模型"""
    __tablename__ = 'gates'
    
    id = db.Column(db.Integer, primary_key=True)
    gate_id = db.Column(db.String(50), nullable=False)  # 如 'g1', 'g2'
    type = db.Column(db.String(10), nullable=False)     # 'AND', 'OR', 'NOT'
    delay = db.Column(db.Float, nullable=False)
    circuit_id = db.Column(db.Integer, db.ForeignKey('circuits.id'), nullable=False)
    
    # 门的输入输出关系存储在connections表中

class Connection(db.Model):
    """连接关系数据模型"""
    __tablename__ = 'connections'
    
    id = db.Column(db.Integer, primary_key=True)
    from_id = db.Column(db.String(50), nullable=False)  # 起始端口/门ID
    to_id = db.Column(db.String(50), nullable=False)    # 目标端口/门ID
    delay = db.Column(db.Float, nullable=False)
    circuit_id = db.Column(db.Integer, db.ForeignKey('circuits.id'), nullable=False)

class DetectionResult(db.Model):
    """检测结果数据模型"""
    __tablename__ = 'detection_results'
    
    id = db.Column(db.Integer, primary_key=True)
    circuit_id = db.Column(db.Integer, db.ForeignKey('circuits.id'), nullable=False)
    result_type = db.Column(db.String(20), nullable=False)  # 'race_condition' 或 'hazard'
    description = db.Column(db.Text, nullable=False)
    details = db.Column(db.JSON, nullable=True)
    created_at = db.Column(db.DateTime, default=lambda: datetime.now(UTC)) 