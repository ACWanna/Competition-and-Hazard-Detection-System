import unittest
from app.models.circuit import Circuit, LogicGate
from app.services.detector import HazardDetector

class TestHazardDetector(unittest.TestCase):
    """测试竞争冒险检测器"""
    
    def setUp(self):
        # 创建测试电路
        self.circuit = Circuit("test_circuit")
        
        # 添加输入
        self.circuit.add_input("in1", "A", 0)
        self.circuit.add_input("in2", "B", 0)
        
        # 添加AND门
        gate = LogicGate("g1", "AND", 2.0, ["in1", "in2"], "g1")
        self.circuit.add_gate(gate)
        
        # 添加连接
        self.circuit.add_connection("in1", "g1", 0.1)
        self.circuit.add_connection("in2", "g1", 0.5)
        
        # 添加输出
        self.circuit.add_output("out1", "Y", "g1")
        
        self.detector = HazardDetector(self.circuit)
    
    def test_race_condition_detection(self):
        """测试竞争条件检测"""
        results = self.detector.detect_hazards()
        race_conditions = results["race_conditions"]
        
        # 验证是否检测到竞争条件
        self.assertEqual(len(race_conditions), 1)
        rc = race_conditions[0]
        self.assertEqual(rc["gate_id"], "g1")
        self.assertEqual(rc["gate_type"], "AND")
    
    def test_static_hazard_detection(self):
        """测试静态冒险检测"""
        # 添加另一条路径以创建可能的冒险
        gate2 = LogicGate("g2", "OR", 1.0, ["in1", "in2"], "g2")
        self.circuit.add_gate(gate2)
        self.circuit.add_connection("in1", "g2", 0.2)
        self.circuit.add_connection("in2", "g2", 0.3)
        
        gate3 = LogicGate("g3", "AND", 2.0, ["g1", "g2"], "g3")
        self.circuit.add_gate(gate3)
        self.circuit.add_connection("g1", "g3", 0.1)
        self.circuit.add_connection("g2", "g3", 0.1)
        
        self.circuit.add_output("out2", "Z", "g3")
        
        detector = HazardDetector(self.circuit)
        results = detector.detect_hazards()
        hazards = results["hazards"]
        
        # 验证是否检测到冒险
        self.assertGreater(len(hazards), 0)

    def test_no_hazards(self):
        """测试无冒险情况"""
        # 创建一个简单的无冒险电路
        circuit = Circuit("simple")
        circuit.add_input("in1", "A", 0)
        circuit.add_output("out1", "Y", "in1")
        
        detector = HazardDetector(circuit)
        results = detector.detect_hazards()
        
        self.assertEqual(len(results["race_conditions"]), 0)
        self.assertEqual(len(results["hazards"]), 0)

    def test_multiple_paths(self):
        """测试多路径情况"""
        # 添加一个具有多条路径的复杂电路
        gate4 = LogicGate("g4", "OR", 1.5, ["g2", "g3"], "g4")
        self.circuit.add_gate(gate4)
        self.circuit.add_connection("g2", "g4", 0.1)
        self.circuit.add_connection("g3", "g4", 0.1)
        self.circuit.add_output("out3", "W", "g4")
        
        results = self.detector.detect_hazards()
        self.assertGreater(len(results["hazards"]), 1) 