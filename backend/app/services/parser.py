from typing import Dict, List, Tuple
from app.models.circuit import Circuit, LogicGate
from app.utils.exceptions import CircuitParseError
import logging

class CircuitParser:
    """电路解析器类"""
    
    def __init__(self):
        self.gate_id_counter = 0
        self.logger = logging.getLogger(__name__)
        
    def _generate_gate_id(self) -> str:
        """生成唯一的门ID"""
        self.gate_id_counter += 1
        return f"g{self.gate_id_counter}"
    
    def parse(self, expression: str) -> Circuit:
        """
        解析逻辑表达式并生成电路
        
        Args:
            expression: 逻辑表达式(如 "A AND B OR C")
            
        Returns:
            Circuit: 解析后的电路实例
        """
        if not expression:
            raise CircuitParseError("表达式不能为空")
            
        self.logger.info(f"开始解析表达式: '{expression}'")
            
        # 将表达式转换为标记列表
        tokens = self._tokenize(expression)
        self.logger.info(f"标记化结果: {tokens}")
        
        # 创建新电路
        circuit = Circuit("parsed_circuit")
        
        # 解析输入变量
        inputs = self._extract_inputs(tokens)
        self.logger.info(f"提取的输入变量: {inputs}")
        
        for var in inputs:
            circuit.add_input(var.lower(), var, 0)
        
        # 构建门电路
        output_id = self._build_gates(circuit, tokens)
        self.logger.info(f"构建完成，输出门ID: {output_id}")
        
        # 添加输出端口
        circuit.add_output("out1", "Y", output_id)
        
        # 打印电路结构
        self.logger.info(f"解析后的电路包含 {len(circuit.gates)} 个门:")
        for gate_id, gate in circuit.gates.items():
            self.logger.info(f"门 {gate_id}: 类型={gate.type}, 输入={gate.inputs}")
        
        self.logger.info(f"电路连接数量: {len(circuit.connections)}")
        for conn in circuit.connections:
            self.logger.info(f"连接: {conn['from']} -> {conn['to']}")
        
        return circuit
    
    def _tokenize(self, expression: str) -> List[str]:
        """
        将表达式转换为标记列表
        
        Args:
            expression: 逻辑表达式
            
        Returns:
            标记列表
        """
        # 替换操作符为标准格式
        expr = expression.upper().replace('AND', '&').replace('OR', '|').replace('NOT', '!')
        self.logger.debug(f"替换标准操作符: '{expr}'")
        
        # 分割标记
        tokens = []
        current = ''
        
        for char in expr:
            if char in '&|!()':
                if current:
                    tokens.append(current.strip())
                    current = ''
                tokens.append(char)
            elif char.isspace():
                if current:
                    tokens.append(current.strip())
                    current = ''
            else:
                current += char
                
        if current:
            tokens.append(current.strip())
            
        return tokens
    
    def _extract_inputs(self, tokens: List[str]) -> List[str]:
        """
        提取输入变量
        
        Args:
            tokens: 标记列表
            
        Returns:
            输入变量列表
        """
        inputs = set()
        for token in tokens:
            if token.isalpha() and token not in ['AND', 'OR', 'NOT']:
                inputs.add(token)
        return sorted(list(inputs))
    
    def _build_gates(self, circuit: Circuit, tokens: List[str]) -> str:
        """
        构建逻辑门电路
        
        Args:
            circuit: 电路实例
            tokens: 标记列表
            
        Returns:
            输出门的ID
        """
        # 实现简单的表达式解析
        # 这里使用递归下降解析器处理优先级
        # 当前实现仅支持基本的AND/OR/NOT操作
        
        stack = []
        operators = []
        
        for token in tokens:
            if token in ['&', '|']:
                while (operators and operators[-1] != '(' and 
                       self._precedence(operators[-1]) >= self._precedence(token)):
                    self._create_gate(circuit, operators.pop(), stack)
                operators.append(token)
            elif token == '!':
                operators.append(token)
            elif token == '(':
                operators.append(token)
            elif token == ')':
                while operators and operators[-1] != '(':
                    self._create_gate(circuit, operators.pop(), stack)
                if operators and operators[-1] == '(':
                    operators.pop()
            else:  # 操作数
                stack.append(token.lower())
        
        # 处理剩余的操作符
        while operators:
            self._create_gate(circuit, operators.pop(), stack)
        
        return stack[-1]
    
    def _precedence(self, operator: str) -> int:
        """返回操作符优先级"""
        if operator == '!':
            return 3
        elif operator == '&':
            return 2
        elif operator == '|':
            return 1
        return 0
    
    def _create_gate(self, circuit: Circuit, operator: str, stack: List[str]) -> None:
        """
        创建逻辑门并添加到电路
        
        Args:
            circuit: 电路实例
            operator: 操作符
            stack: 操作数栈
        """
        gate_id = self._generate_gate_id()
        self.logger.debug(f"创建门 {gate_id}, 操作符: {operator}, 当前栈: {stack}")
        
        if operator == '!':
            input_id = stack.pop()
            # 输出端口需修改
            gate = LogicGate(gate_id, 'NOT', 1.0, [input_id], gate_id) 
            circuit.add_gate(gate)
            circuit.add_connection(input_id, gate_id, 0.1)
            stack.append(gate_id)
            self.logger.info(f"创建NOT门 {gate_id}, 输入: {input_id}")
        else:
            input2 = stack.pop()
            input1 = stack.pop()
            gate_type = 'AND' if operator == '&' else 'OR'
            gate = LogicGate(gate_id, gate_type, 2.0, [input1, input2], gate_id)
            circuit.add_gate(gate)
            circuit.add_connection(input1, gate_id, 0.1)
            circuit.add_connection(input2, gate_id, 0.1)
            stack.append(gate_id)
            self.logger.info(f"创建{gate_type}门 {gate_id}, 输入: {input1}, {input2}") 