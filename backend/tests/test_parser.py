import unittest
from app.services.parser import CircuitParser
from app.utils.exceptions import CircuitParseError

class TestCircuitParser(unittest.TestCase):
    """测试电路解析器"""
    
    def setUp(self):
        self.parser = CircuitParser()
    
    def test_parse_simple_and(self):
        """测试解析简单AND表达式"""
        circuit = self.parser.parse_expression("A AND B")
        
        # 验证输入
        self.assertEqual(len(circuit.inputs), 2)
        self.assertIn('a', circuit.inputs)
        self.assertIn('b', circuit.inputs)
        
        # 验证门
        self.assertEqual(len(circuit.gates), 1)
        gate = list(circuit.gates.values())[0]
        self.assertEqual(gate.type, 'AND')
        self.assertEqual(len(gate.inputs), 2)
        
        # 验证连接
        self.assertEqual(len(circuit.connections), 2)
    
    def test_parse_complex_expression(self):
        """测试解析复杂表达式"""
        circuit = self.parser.parse_expression("(A AND B) OR (NOT C)")
        
        # 验证输入
        self.assertEqual(len(circuit.inputs), 3)
        
        # 验证门数量(AND, OR, NOT)
        self.assertEqual(len(circuit.gates), 3)
        
        # 验证连接
        self.assertGreater(len(circuit.connections), 3)
    
    def test_invalid_expression(self):
        """测试无效表达式"""
        with self.assertRaises(CircuitParseError):
            self.parser.parse_expression("A AND AND B")
    
    def test_empty_expression(self):
        """测试空表达式"""
        with self.assertRaises(CircuitParseError):
            self.parser.parse_expression("")
    
    def test_single_input(self):
        """测试单个输入"""
        circuit = self.parser.parse_expression("A")
        self.assertEqual(len(circuit.inputs), 1)
        self.assertEqual(len(circuit.gates), 0)
    
    def test_nested_expressions(self):
        """测试嵌套表达式"""
        circuit = self.parser.parse_expression("((A AND B) OR C) AND (NOT D)")
        self.assertEqual(len(circuit.inputs), 4)
        self.assertGreaterEqual(len(circuit.gates), 4) 