from typing import Dict, List, Optional
import logging

class LogicGate:
    """逻辑门类"""
    
    def __init__(
        self,
        gate_id: str,
        gate_type: str,
        delay: float,
        inputs: List[str],
        output: str
    ):
        """
        初始化逻辑门
        
        Args:
            gate_id: 门的唯一标识符
            gate_type: 门类型(AND/OR/NOT等)
            delay: 门延迟(ns)
            inputs: 输入端口列表
            output: 输出端口标识符
        """
        self.id = gate_id
        self.type = gate_type
        self.delay = delay
        self.inputs = inputs
        self.output = output
        
    def compute_output(self, input_values: Dict[str, int]) -> int:
        """
        计算逻辑门的输出值
        
        Args:
            input_values: 输入端口ID到值(0/1)的映射
            
        Returns:
            输出值(0/1)
        """
        # 确保所有输入都有值
        for input_id in self.inputs:
            if input_id not in input_values:
                raise ValueError(f"输入 {input_id} 没有值")
        
        # 根据门类型计算输出
        if self.type == "AND":
            # AND门: 所有输入为1时输出为1，否则为0
            return 1 if all(input_values[input_id] == 1 for input_id in self.inputs) else 0
        
        elif self.type == "OR":
            # OR门: 任一输入为1时输出为1，否则为0
            return 1 if any(input_values[input_id] == 1 for input_id in self.inputs) else 0
        
        elif self.type == "NOT":
            # NOT门: 输入为0时输出为1，输入为1时输出为0
            if len(self.inputs) != 1:
                raise ValueError(f"NOT门应该只有一个输入，但 {self.id} 有 {len(self.inputs)} 个输入")
            return 1 - input_values[self.inputs[0]]
        
        else:
            raise ValueError(f"不支持的门类型: {self.type}")

class Circuit:
    """电路类"""
    
    def __init__(self, name: str):
        """
        初始化电路
        
        Args:
            name: 电路名称
        """
        self.name = name
        self.gates: Dict[str, LogicGate] = {}
        self.inputs: Dict[str, Dict] = {}
        self.outputs: Dict[str, Dict] = {}
        self.connections: List[Dict] = []
    
    def add_gate(self, gate: LogicGate) -> None:
        """
        添加逻辑门
        
        Args:
            gate: LogicGate实例
        """
        self.gates[gate.id] = gate
    
    def add_input(self, input_id: str, name: str, initial_value: int) -> None:
        """
        添加输入端口
        
        Args:
            input_id: 输入端口ID
            name: 显示名称
            initial_value: 初始值
        """
        self.inputs[input_id] = {
            "name": name,
            "initial_value": initial_value
        }
    
    def add_output(self, output_id: str, name: str, source: str) -> None:
        """
        添加输出端口
        
        Args:
            output_id: 输出端口ID
            name: 显示名称
            source: 数据来源
        """
        self.outputs[output_id] = {
            "name": name,
            "source": source
        }
    
    def add_connection(self, from_id: str, to_id: str, delay: float) -> None:
        """
        添加连接
        
        Args:
            from_id: 起始端口/门ID
            to_id: 目标端口/门ID
            delay: 连线延迟
        """
        self.connections.append({
            "from": from_id,
            "to": to_id,
            "delay": delay
        })
    
    def compute_circuit(self, input_values: Dict[str, int] = None) -> Dict[str, int]:
        """
        计算整个电路的输出值
        
        Args:
            input_values: 输入端口ID到值的映射，如果为None则使用初始值
            
        Returns:
            包含所有门和输出的计算结果的字典
        """
        # 如果没有提供输入值，使用初始值
        if input_values is None:
            input_values = {input_id: data["initial_value"] 
                           for input_id, data in self.inputs.items()}
        else:
            # 验证输入值
            for input_id in input_values:
                if input_id not in self.inputs:
                    raise ValueError(f"未知的输入ID: {input_id}")
        
        # 计算结果字典，初始包含输入值
        results = input_values.copy()
        
        # 创建拓扑排序
        sorted_gates = self._topological_sort()
        
        # 按拓扑顺序计算每个门的输出
        for gate_id in sorted_gates:
            gate = self.gates[gate_id]
            gate_inputs = {}
            
            # 获取该门的所有输入值
            for input_id in gate.inputs:
                # 如果输入是另一个门的输出
                if input_id in results:
                    gate_inputs[input_id] = results[input_id]
                else:
                    raise ValueError(f"无法计算门 {gate_id} 的输入 {input_id} 的值")
            
            # 计算该门的输出
            results[gate_id] = gate.compute_output(gate_inputs)
        
        # 计算电路输出
        output_results = {}
        for output_id, output_data in self.outputs.items():
            source_id = output_data["source"]
            if source_id in results:
                output_results[output_id] = results[source_id]
            else:
                raise ValueError(f"无法计算输出 {output_id} 的值，未找到源 {source_id}")
        
        # 添加输出结果
        results.update(output_results)
        
        return results
    
    def _topological_sort(self) -> List[str]:
        """
        对电路中的门进行拓扑排序，确保计算顺序正确
        
        Returns:
            排序后的门ID列表
        """
        # 构建邻接表
        graph = {gate_id: [] for gate_id in self.gates}
        in_degree = {gate_id: 0 for gate_id in self.gates}
        
        # 计算入度和建立邻接关系
        for conn in self.connections:
            from_id, to_id = conn["from"], conn["to"]
            
            # 只考虑门之间的连接
            if from_id in self.gates and to_id in self.gates:
                graph[from_id].append(to_id)
                in_degree[to_id] += 1
        
        # 拓扑排序
        queue = [gate_id for gate_id, degree in in_degree.items() if degree == 0]
        sorted_gates = []
        
        while queue:
            gate_id = queue.pop(0)
            sorted_gates.append(gate_id)
            
            for neighbor in graph[gate_id]:
                in_degree[neighbor] -= 1
                if in_degree[neighbor] == 0:
                    queue.append(neighbor)
        
        # 检查是否有环
        if len(sorted_gates) != len(self.gates):
            raise ValueError("电路中存在环路，无法进行拓扑排序")
            
        return sorted_gates
    
    @classmethod
    def from_dict(cls, data: Dict) -> 'Circuit':
        """
        从字典创建电路实例
        
        Args:
            data: 电路数据字典
            
        Returns:
            Circuit实例
        """
        logger = logging.getLogger(__name__)
        
        # 验证数据结构
        if not isinstance(data, dict):
            logger.error(f"数据不是字典类型: {type(data)}")
            raise ValueError("数据必须是字典类型")
        
        if "circuit" not in data:
            logger.error("数据缺少circuit字段")
            raise ValueError("数据缺少circuit字段")
        
        circuit_data = data["circuit"]
        required_fields = ["name", "gates", "inputs", "outputs", "connections"]
        for field in required_fields:
            if field not in circuit_data:
                logger.error(f"电路数据缺少{field}字段")
                raise ValueError(f"电路数据缺少{field}字段")
        
        # 创建电路实例
        try:
            circuit = cls(circuit_data["name"])
            
            # 添加门
            for gate_data in circuit_data["gates"]:
                # 验证门数据
                required_gate_fields = ["id", "type", "delay", "inputs", "output"]
                for field in required_gate_fields:
                    if field not in gate_data:
                        logger.error(f"门数据缺少{field}字段: {gate_data}")
                        raise ValueError(f"门数据缺少{field}字段")
                
                gate = LogicGate(
                    gate_data["id"],
                    gate_data["type"],
                    gate_data["delay"],
                    gate_data["inputs"],
                    gate_data["output"]
                )
                circuit.add_gate(gate)
            
            # 添加输入端口
            for input_data in circuit_data["inputs"]:
                # 验证输入数据
                required_input_fields = ["id", "name", "initial_value"]
                for field in required_input_fields:
                    if field not in input_data:
                        logger.error(f"输入数据缺少{field}字段: {input_data}")
                        raise ValueError(f"输入数据缺少{field}字段")
                
                circuit.add_input(
                    input_data["id"],
                    input_data["name"],
                    input_data["initial_value"]
                )
            
            # 添加输出端口
            for output_data in circuit_data["outputs"]:
                # 验证输出数据
                required_output_fields = ["id", "name", "source"]
                for field in required_output_fields:
                    if field not in output_data:
                        logger.error(f"输出数据缺少{field}字段: {output_data}")
                        raise ValueError(f"输出数据缺少{field}字段")
                
                circuit.add_output(
                    output_data["id"],
                    output_data["name"],
                    output_data["source"]
                )
            
            # 添加连接
            for conn_data in circuit_data["connections"]:
                # 验证连接数据
                required_conn_fields = ["from", "to", "delay"]
                for field in required_conn_fields:
                    if field not in conn_data:
                        logger.error(f"连接数据缺少{field}字段: {conn_data}")
                        raise ValueError(f"连接数据缺少{field}字段")
                
                circuit.add_connection(
                    conn_data["from"],
                    conn_data["to"],
                    conn_data["delay"]
                )
            
            return circuit
        except Exception as e:
            logger.error(f"创建电路实例失败: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
            raise ValueError(f"创建电路实例失败: {str(e)}") 