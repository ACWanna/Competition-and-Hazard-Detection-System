import unittest
import json
from app import create_app
from config import Config

class TestConfig(Config):
    TESTING = True

class TestAPI(unittest.TestCase):
    """测试API端点"""
    
    def setUp(self):
        self.app = create_app(TestConfig)
        self.client = self.app.test_client()
    
    def test_parse_circuit(self):
        """测试电路解析API"""
        response = self.client.post('/api/parse',
            json={"expression": "A AND B"})
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertEqual(data["status"], "success")
        self.assertIn("circuit", data)
        
        # 验证错误处理
        response = self.client.post('/api/parse',
            json={"wrong_key": "A AND B"})
        self.assertEqual(response.status_code, 400)
    
    def test_detect_hazards(self):
        """测试竞争冒险检测API"""
        circuit_data = {
            "circuit": {
                "name": "test",
                "gates": [{
                    "id": "g1",
                    "type": "AND",
                    "delay": 2.0,
                    "inputs": ["in1", "in2"],
                    "output": "g1"
                }],
                "inputs": {
                    "in1": {"name": "A", "initial_value": 0},
                    "in2": {"name": "B", "initial_value": 0}
                },
                "outputs": {
                    "out1": {"name": "Y", "source": "g1"}
                },
                "connections": [
                    {"from": "in1", "to": "g1", "delay": 0.1},
                    {"from": "in2", "to": "g1", "delay": 0.5}
                ]
            }
        }
        
        response = self.client.post('/api/detect',
            json=circuit_data)
        
        self.assertEqual(response.status_code, 200)
        data = json.loads(response.data)
        self.assertEqual(data["status"], "success")
        self.assertIn("results", data)
        
        # 验证错误处理
        response = self.client.post('/api/detect',
            json={"wrong_key": {}})
        self.assertEqual(response.status_code, 400) 