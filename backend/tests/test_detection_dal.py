import unittest
from datetime import datetime
from app import create_app, db
from app.models.database import Circuit, DetectionResult
from app.dal.detection_dal import DetectionDAL
from config import Config

class TestConfig(Config):
    TESTING = True
    SQLALCHEMY_DATABASE_URI = 'sqlite:///:memory:'

class TestDetectionDAL(unittest.TestCase):
    """测试检测结果数据访问层"""
    
    def setUp(self):
        self.app = create_app(TestConfig)
        self.app_context = self.app.app_context()
        self.app_context.push()
        db.create_all()
        
        # 创建测试电路
        self.circuit = Circuit(
            name="test_circuit",
            expression="A AND B"
        )
        db.session.add(self.circuit)
        db.session.commit()
    
    def tearDown(self):
        db.session.remove()
        db.drop_all()
        self.app_context.pop()
    
    def test_add_race_condition(self):
        """测试添加竞争条件结果"""
        result = DetectionDAL.add_race_condition(
            circuit=self.circuit,
            gate_id="g1",
            input1="in1",
            input2="in2",
            delay1=1.0,
            delay2=1.1
        )
        
        self.assertEqual(result.circuit_id, self.circuit.id)
        self.assertEqual(result.result_type, "race_condition")
        self.assertIn("g1", result.description)
        self.assertEqual(result.details["gate_id"], "g1")
    
    def test_add_hazard(self):
        """测试添加冒险结果"""
        paths = [["in1", "g1", "out1"], ["in2", "g2", "out1"]]
        result = DetectionDAL.add_hazard(
            circuit=self.circuit,
            output_id="out1",
            paths=paths,
            max_delay=3.0,
            min_delay=1.0
        )
        
        self.assertEqual(result.circuit_id, self.circuit.id)
        self.assertEqual(result.result_type, "hazard")
        self.assertIn("out1", result.description)
        self.assertEqual(result.details["delay_difference"], 2.0)
    
    def test_get_circuit_results(self):
        """测试获取电路检测结果"""
        # 添加多个检测结果
        DetectionDAL.add_race_condition(
            circuit=self.circuit,
            gate_id="g1",
            input1="in1",
            input2="in2",
            delay1=1.0,
            delay2=1.1
        )
        
        DetectionDAL.add_hazard(
            circuit=self.circuit,
            output_id="out1",
            paths=[["in1", "g1", "out1"]],
            max_delay=3.0,
            min_delay=1.0
        )
        
        results = DetectionDAL.get_circuit_results(self.circuit.id)
        self.assertEqual(len(results), 2)
    
    def test_get_latest_result(self):
        """测试获取最新检测结果"""
        # 添加两个检测结果
        DetectionDAL.add_race_condition(
            circuit=self.circuit,
            gate_id="g1",
            input1="in1",
            input2="in2",
            delay1=1.0,
            delay2=1.1
        )
        
        latest = DetectionDAL.add_hazard(
            circuit=self.circuit,
            output_id="out1",
            paths=[["in1", "g1", "out1"]],
            max_delay=3.0,
            min_delay=1.0
        )
        
        result = DetectionDAL.get_latest_result(self.circuit.id)
        self.assertEqual(result.id, latest.id)
        self.assertEqual(result.result_type, "hazard") 