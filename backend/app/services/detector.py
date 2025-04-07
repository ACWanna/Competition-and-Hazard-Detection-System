from typing import Dict, List, Set, Tuple, Optional, Any
from app.models.circuit import Circuit, LogicGate
import logging
import re

class HazardDetector:
    """竞争和冒险检测器"""
    
    def __init__(self, circuit: Circuit):
        """
        初始化检测器
        
        Args:
            circuit: 待检测的电路
        """
        self.circuit = circuit
        self.paths: Dict[str, List[List[str]]] = {}  # 存储从输入到输出的所有路径
        self.logger = logging.getLogger(__name__)
        
    def detect_hazards(self) -> Dict:
        """
        检测电路中的竞争和冒险
        
        Returns:
            包含检测结果的字典
        """
        self.logger.info(f"开始检测电路 '{self.circuit.name}' 中的竞争和冒险")
        
        try:
            race_conditions = self._detect_race_conditions()
            self.logger.info(f"检测到 {len(race_conditions)} 个竞争条件")
        except Exception as e:
            self.logger.error(f"检测竞争条件时出错: {str(e)}")
            import traceback
            self.logger.error(traceback.format_exc())
            race_conditions = []
            
        try:
            # 首先尝试基于表达式的冒险检测
            hazards = self._detect_hazards_by_expression()
            self.logger.info(f"通过表达式方法检测到 {len(hazards)} 个冒险")
            
            # 如果未检测到冒险，尝试使用直接检测方法
            if not hazards:
                self.logger.info("表达式方法未检测到冒险，尝试使用直接检测方法")
                hazards = self._check_direct_hazards()
                self.logger.info(f"通过直接检测方法检测到 {len(hazards)} 个冒险")
        except Exception as e:
            self.logger.error(f"检测冒险时出错: {str(e)}")
            import traceback
            self.logger.error(traceback.format_exc())
            hazards = []
            
        results = {
            "race_conditions": race_conditions,
            "hazards": hazards
        }
        return results
    
    def _detect_race_conditions(self) -> List[Dict]:
        """
        检测竞争条件
        
        Returns:
            竞争条件列表
        """
        race_conditions = []
        
        # 对每个门检查是否存在多个输入信号同时变化的情况
        for gate_id, gate in self.circuit.gates.items():
            if len(gate.inputs) > 1:
                # 计算到每个输入的所有路径延迟
                input_delays = self._calculate_input_delays(gate)
                
                # 检查是否存在延迟相近的输入路径
                for i, (input1, delay1) in enumerate(input_delays.items()):
                    for input2, delay2 in list(input_delays.items())[i+1:]:
                        if abs(delay1 - delay2) < 0.5:  # 延迟差小于0.5ns视为可能存在竞争
                            race_conditions.append({
                                "gate_id": gate_id,
                                "gate_type": gate.type,
                                "input1": input1,
                                "input2": input2,
                                "delay1": delay1,
                                "delay2": delay2
                            })
        
        return race_conditions
    
    def _detect_static_hazards(self) -> List[Dict]:
        """
        检测静态冒险
        
        Returns:
            静态冒险列表
        """
        hazards = []
        
        # 对每个输出检查是否存在多条路径且延迟差异较大
        for output_id, output in self.circuit.outputs.items():
            source = output["source"]
            paths = self._find_all_paths_to_gate(source)
            
            if len(paths) > 1:
                # 计算每条路径的总延迟
                path_delays = [self._calculate_path_delay(path) for path in paths]
                
                # 检查路径延迟差异
                max_delay = max(path_delays)
                min_delay = min(path_delays)
                
                if max_delay - min_delay > 1.0:  # 延迟差大于1ns视为可能存在冒险
                    hazards.append({
                        "output_id": output_id,
                        "paths": paths,
                        "max_delay": max_delay,
                        "min_delay": min_delay
                    })
        
        return hazards
    
    def _calculate_input_delays(self, gate: LogicGate) -> Dict[str, float]:
        """计算门输入的延迟"""
        delays = {}
        for input_id in gate.inputs:
            try:
                self.logger.debug(f"计算门 {gate.id} 的输入 {input_id} 的延迟")
                paths = self._find_all_paths_to_gate(input_id)
                if paths:
                    delays[input_id] = max(self._calculate_path_delay(path) for path in paths)
                    self.logger.debug(f"门 {gate.id} 的输入 {input_id} 的延迟为 {delays[input_id]}")
                else:
                    self.logger.warning(f"未找到到门 {gate.id} 的输入 {input_id} 的路径，设置延迟为0")
                    delays[input_id] = 0.0
            except Exception as e:
                self.logger.error(f"计算门 {gate.id} 的输入 {input_id} 的延迟时出错: {str(e)}")
                delays[input_id] = 0.0
        return delays
    
    def _find_all_paths_to_gate(self, gate_id: str) -> List[List[str]]:
        """查找到指定门的所有路径"""
        if gate_id in self.paths:
            return self.paths[gate_id]
            
        paths = []
        visited = set()
        max_depth = 100  # 防止无限递归
        
        def dfs(current: str, path: List[str], depth: int = 0) -> None:
            if depth > max_depth:
                self.logger.warning(f"DFS搜索达到最大深度 {max_depth}，可能存在循环")
                return
                
            if current in self.circuit.inputs:
                paths.append(path[:])
                return
                
            if current in visited:
                return
                
            visited.add(current)
            
            # 查找连接到当前门输入的所有连接
            for conn in self.circuit.connections:
                if conn["to"] == current:
                    dfs(conn["from"], [conn["from"]] + path, depth + 1)
                    
            visited.remove(current)
        
        try:
            self.logger.debug(f"查找到门 {gate_id} 的所有路径")
            dfs(gate_id, [gate_id])
            self.paths[gate_id] = paths
            self.logger.debug(f"找到 {len(paths)} 条到门 {gate_id} 的路径")
            return paths
        except Exception as e:
            self.logger.error(f"查找到门 {gate_id} 的路径时出错: {str(e)}")
            import traceback
            self.logger.error(traceback.format_exc())
            return []
    
    def _calculate_path_delay(self, path: List[str]) -> float:
        """计算路径总延迟"""
        try:
            total_delay = 0.0
            
            # 计算门延迟
            for gate_id in path:
                if gate_id in self.circuit.gates:
                    total_delay += self.circuit.gates[gate_id].delay
            
            # 计算连接延迟
            for i in range(len(path) - 1):
                connection_found = False
                for conn in self.circuit.connections:
                    if conn["from"] == path[i] and conn["to"] == path[i + 1]:
                        total_delay += conn["delay"]
                        connection_found = True
                        break
                
                if not connection_found:
                    self.logger.warning(f"未找到从 {path[i]} 到 {path[i+1]} 的连接")
                    
            self.logger.debug(f"路径 {' -> '.join(path)} 的总延迟为 {total_delay}")
            return total_delay
        except Exception as e:
            self.logger.error(f"计算路径 {path} 的延迟时出错: {str(e)}")
            import traceback
            self.logger.error(traceback.format_exc())
            return 0.0
    
    def _detect_hazards_by_expression(self) -> List[Dict]:
        """
        通过从后到前遍历电路并使用特殊变量分析来检测冒险
        
        Returns:
            冒险列表
        """
        hazards = []
        
        # 第一步：找出电路中所有的输入变量
        inputs = list(self.circuit.inputs.keys())
        input_names = {input_id: self.circuit.inputs[input_id]["name"] for input_id in inputs}
        
        self.logger.info(f"开始使用特殊变量方法检测电路中的冒险")
        self.logger.info(f"电路包含以下输入: {input_names}")
        
        # 查找所有输入变量中存在非电路的变量
        variables_with_negation = self._find_variables_with_negation()
        
        if not variables_with_negation:
            self.logger.info("未检测到任何变量及其反相同时存在于电路中，不存在冒险")
            return hazards
            
        self.logger.info(f"检测到以下变量及其反相同时存在于电路中: {[var['variable'] for var in variables_with_negation]}")
        
        # 对每个存在非形式的输入变量进行分析
        for var_info in variables_with_negation:
            variable = var_info["variable"]
            var_id = var_info["id"]
            
            self.logger.info(f"分析变量 {variable} 的冒险情况")
            
            # 获取所有其他输入变量
            other_inputs = [inp for inp in inputs if inp != var_id]
            
            # 生成其他输入变量的所有可能组合
            input_combinations = self._generate_all_input_combinations(other_inputs)
            
            self.logger.info(f"为变量 {variable} 生成了 {len(input_combinations)} 种输入组合")
            
            # 分析每种输入组合下变量产生的冒险
            hazard_found = False
            
            for input_combo in input_combinations:
                # 使用特殊变量分析冒险
                hazard_info = self._analyze_hazard_with_special_variable(var_id, variable, input_combo)
                if hazard_info:
                    hazards.append(hazard_info)
                    hazard_found = True
            
            if not hazard_found:
                self.logger.info(f"变量 {variable} 在所有输入组合下均未检测到冒险")
        
        self.logger.info(f"冒险检测完成，共发现 {len(hazards)} 个冒险")
        return hazards
    
    def _analyze_hazard_with_special_variable(self, var_id: str, variable_name: str, 
                                             other_inputs: Dict[str, int]) -> Optional[Dict]:
        """
        使用特殊变量分析电路中的冒险
        
        Args:
            var_id: 变量ID
            variable_name: 变量名称
            other_inputs: 其他输入变量的值
            
        Returns:
            冒险信息或None
        """
        # 创建用于检测冒险的特殊变量
        special_var = SpecialVariable(var_id, variable_name)
        
        # 创建输入值映射，将目标变量设为特殊变量
        input_values = other_inputs.copy()
        input_values[var_id] = special_var
        
        self.logger.info(f"开始分析变量 {variable_name} 在输入组合 {other_inputs} 下的冒险情况")
        self.logger.info(f"使用特殊变量 {special_var} 替代实际输入")
        
        # 按拓扑顺序逆序列出所有门
        sorted_gates = self._reverse_topological_sort()
        self.logger.info(f"逆拓扑排序结果: {sorted_gates}")
        
        # 初始化电路状态，包含输入值
        circuit_state = input_values.copy()
        self.logger.info(f"初始电路状态: {circuit_state}")
        
        # 分析当前电路连接情况
        self.logger.info("当前电路连接情况:")
        for conn in self.circuit.connections:
            self.logger.debug(f"  连接: {conn['from']} -> {conn['to']}")
        
        # 分析汇合点（一个门接收同一个变量的原值和反值的情况）
        convergence_points = []
        for gate_id in sorted_gates:
            gate = self.circuit.gates[gate_id]
            
            # 查找可能的连接到此门的路径
            paths_to_gate = self._find_all_paths_to_gate(gate_id)
            
            # 检查是否有路径包含目标变量和其反相
            direct_var_paths = []
            negated_var_paths = []
            
            for path in paths_to_gate:
                if var_id in path:
                    var_index = path.index(var_id)
                    # 检查变量后是否紧跟着NOT门，这表示这条路径上变量被反相了
                    if var_index + 1 < len(path):
                        next_gate_id = path[var_index + 1]
                        if next_gate_id in self.circuit.gates and self.circuit.gates[next_gate_id].type == "NOT":
                            negated_var_paths.append(path)
                        else:
                            direct_var_paths.append(path)
            
            if direct_var_paths and negated_var_paths:
                self.logger.info(f"门 {gate_id} 可能是变量 {variable_name} 的汇合点，同时有原始路径和非路径")
                convergence_points.append(gate_id)
        
        self.logger.info(f"找到的汇合点: {convergence_points}")
        
        # 初始化检测到的冒险
        hazard_gates = []
        
        # 从输出门向输入门遍历电路
        for gate_id in sorted_gates:
            gate = self.circuit.gates[gate_id]
            
            # 收集门的输入值
            gate_inputs = self._collect_gate_inputs(gate_id, circuit_state)
            self.logger.info(f"门 {gate_id}({gate.type}) 的输入值: {gate_inputs}")
            
            # 检查门输入是否包含互补信号（变量及其反相）
            hazard_detected = self._check_gate_for_hazard(gate_id, gate, gate_inputs)
            if hazard_detected:
                self.logger.info(f"在门 {gate_id} 检测到冒险: {hazard_detected}")
                hazard_gates.append({
                    "gate_id": gate_id,
                    "gate_type": gate.type,
                    "inputs": gate.inputs,
                    "hazard_type": hazard_detected["type"],
                    "critical": True,
                    "description": hazard_detected["description"]
                })
            else:
                self.logger.info(f"门 {gate_id} 未检测到冒险")
            
            # 计算门的输出，可能包含特殊变量
            output_value = self._compute_special_gate_output(gate, gate_inputs)
            circuit_state[gate_id] = output_value
            self.logger.info(f"门 {gate_id} 的输出值: {output_value}")
        
        self.logger.info(f"电路最终状态: {circuit_state}")
        
        # 增加对汇合点的额外检查
        if convergence_points and not hazard_gates:
            self.logger.warning(f"找到了汇合点 {convergence_points}，但未检测到冒险，可能是门输入值收集有问题")
            
            # 详细检查每个汇合点
            for gate_id in convergence_points:
                gate = self.circuit.gates[gate_id]
                self.logger.warning(f"汇合点 {gate_id} ({gate.type}) 的输入端口: {gate.inputs}")
                
                # 检查连接
                connections_to_gate = [conn for conn in self.circuit.connections if conn["to"] == gate_id]
                self.logger.warning(f"连接到汇合点 {gate_id} 的连接: {connections_to_gate}")
        
        # 如果检测到冒险，返回冒险信息
        if hazard_gates:
            hazard_type = hazard_gates[0]["hazard_type"]  # 使用第一个检测到的冒险类型
            self.logger.info(f"变量 {variable_name} 在输入组合 {other_inputs} 下存在 {hazard_type} 冒险")
            
            return {
                "variable": variable_name,
                "other_inputs": other_inputs,
                "hazard_type": hazard_type,
                "hazard_gates": hazard_gates,
                "description": f"变量 {variable_name} 可能导致 {hazard_type}，因为存在互补输入的门"
            }
        
        self.logger.info(f"变量 {variable_name} 在输入组合 {other_inputs} 下未检测到冒险")
        return None
    
    def _reverse_topological_sort(self) -> List[str]:
        """
        电路拓扑排序的逆序，从输出到输入
        
        Returns:
            逆拓扑排序的门ID列表
        """
        # 获取正向拓扑排序
        forward_sort = self._topological_sort()
        # 反转顺序
        return list(reversed(forward_sort))
    
    def _topological_sort(self) -> List[str]:
        """
        对电路中的门进行拓扑排序，确保计算顺序正确
        
        Returns:
            排序后的门ID列表
        """
        # 构建邻接表
        graph = {gate_id: [] for gate_id in self.circuit.gates}
        in_degree = {gate_id: 0 for gate_id in self.circuit.gates}
        
        # 计算入度和建立邻接关系
        for conn in self.circuit.connections:
            from_id, to_id = conn["from"], conn["to"]
            
            # 只考虑门之间的连接
            if from_id in self.circuit.gates and to_id in self.circuit.gates:
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
        if len(sorted_gates) != len(self.circuit.gates):
            raise ValueError("电路中存在环路，无法进行拓扑排序")
            
        return sorted_gates
    
    def _collect_gate_inputs(self, gate_id: str, circuit_state: Dict) -> Dict:
        """
        收集门的输入值
        
        Args:
            gate_id: 门ID
            circuit_state: 当前电路状态
            
        Returns:
            门的输入值映射
        """
        gate = self.circuit.gates[gate_id]
        gate_inputs = {}
        
        self.logger.debug(f"为门 {gate_id} 收集输入值，输入端口列表: {gate.inputs}")
        
        # 分析所有连接到此门的连接
        connections_to_gate = [conn for conn in self.circuit.connections if conn["to"] == gate_id]
        self.logger.debug(f"连接到门 {gate_id} 的连接数量: {len(connections_to_gate)}")
        for conn in connections_to_gate:
            self.logger.debug(f"  连接: {conn['from']} -> {gate_id}")
        
        # 创建门输入端口到信号来源的映射
        input_port_to_source = {}
        for conn in self.circuit.connections:
            if conn["to"] == gate_id:
                # 找出这个连接对应门的哪个输入端口
                for i, input_port in enumerate(gate.inputs):
                    if input_port not in input_port_to_source:  # 如果这个端口还没有分配信号源
                        input_port_to_source[input_port] = conn["from"]
                        break
        
        self.logger.debug(f"门 {gate_id} 的输入端口到信号源映射: {input_port_to_source}")
        
        # 如果输入端口映射不完整，这可能是问题所在
        if len(input_port_to_source) != len(gate.inputs):
            self.logger.warning(f"门 {gate_id} 的输入端口映射不完整 - 预期 {len(gate.inputs)} 个输入，但只找到 {len(input_port_to_source)} 个")
            missing_ports = [port for port in gate.inputs if port not in input_port_to_source]
            self.logger.warning(f"门 {gate_id} 的缺失输入端口: {missing_ports}")
        
        # 根据映射关系获取输入值
        for input_port, source_id in input_port_to_source.items():
            if source_id in circuit_state:
                gate_inputs[input_port] = circuit_state[source_id]
                self.logger.debug(f"门 {gate_id} 的输入端口 {input_port} 值为 {circuit_state[source_id]}，来源于 {source_id}")
            else:
                # 如果找不到源，使用默认值0
                gate_inputs[input_port] = 0
                self.logger.warning(f"门 {gate_id} 的输入端口 {input_port} 找不到源 {source_id} 的值，使用默认值0")
        
        # 检查是否所有输入端口都有值
        if len(gate_inputs) != len(gate.inputs):
            self.logger.warning(f"门 {gate_id} 的输入不完整 - 预期 {len(gate.inputs)} 个输入，但只有 {len(gate_inputs)} 个")
            missing_inputs = [port for port in gate.inputs if port not in gate_inputs]
            self.logger.warning(f"门 {gate_id} 的缺失输入: {missing_inputs}")
        
        return gate_inputs
    
    def _check_gate_for_hazard(self, gate_id: str, gate: 'LogicGate', gate_inputs: Dict) -> Optional[Dict]:
        """
        检查门是否存在冒险（接收到变量及其反相）
        
        Args:
            gate_id: 门ID
            gate: 门对象
            gate_inputs: 门的输入值
            
        Returns:
            冒险信息或None
        """
        # 如果门只有一个输入，不可能有冒险
        if len(gate.inputs) < 2:
            self.logger.debug(f"门 {gate_id} 只有一个输入，跳过冒险检测")
            return None
        
        # 检查是否存在变量及其反相同时作为输入
        special_vars = {}  # 变量ID -> 输入端口列表
        negated_vars = {}  # 变量ID -> 输入端口列表
        
        self.logger.debug(f"分析门 {gate_id} 的输入是否包含变量及其反相")
        
        for input_port, value in gate_inputs.items():
            # 如果是特殊变量
            if isinstance(value, SpecialVariable):
                var_id = value.var_id
                if var_id not in special_vars:
                    special_vars[var_id] = []
                special_vars[var_id].append(input_port)
                self.logger.debug(f"门 {gate_id} 的输入端口 {input_port} 包含特殊变量 {value}")
            # 如果是特殊变量的反相
            elif isinstance(value, NegatedVariable):
                var_id = value.var_id
                if var_id not in negated_vars:
                    negated_vars[var_id] = []
                negated_vars[var_id].append(input_port)
                self.logger.debug(f"门 {gate_id} 的输入端口 {input_port} 包含反相变量 {value}")
            else:
                self.logger.debug(f"门 {gate_id} 的输入端口 {input_port} 包含常规值 {value}")
        
        self.logger.debug(f"门 {gate_id} 的特殊变量: {special_vars}")
        self.logger.debug(f"门 {gate_id} 的反相变量: {negated_vars}")
        
        # 检查是否同时存在变量和其反相
        for var_id in special_vars:
            if var_id in negated_vars:
                # 确定冒险类型
                hazard_type = ""
                if gate.type == "AND":
                    hazard_type = "静态冒险-0"
                    description = f"门 {gate_id} (AND) 同时接收到变量 {var_id} 及其反相，可能产生静态冒险-0"
                elif gate.type == "OR":
                    hazard_type = "静态冒险-1"
                    description = f"门 {gate_id} (OR) 同时接收到变量 {var_id} 及其反相，可能产生静态冒险-1"
                else:
                    hazard_type = "动态冒险"
                    description = f"门 {gate_id} ({gate.type}) 同时接收到变量 {var_id} 及其反相，可能产生动态冒险"
                
                self.logger.info(f"门 {gate_id} 同时接收到变量 {var_id} 及其反相，检测到 {hazard_type}")
                
                return {
                    "type": hazard_type,
                    "description": description,
                    "variable_id": var_id,
                    "special_var_ports": special_vars[var_id],
                    "negated_var_ports": negated_vars[var_id]
                }
        
        return None
    
    def _compute_special_gate_output(self, gate: 'LogicGate', gate_inputs: Dict) -> Any:
        """
        计算门的输出，处理特殊变量
        
        Args:
            gate: 门对象
            gate_inputs: 门的输入值
            
        Returns:
            门的输出值，可能是常规值或特殊变量
        """
        # NOT门处理
        if gate.type == "NOT":
            if len(gate.inputs) != 1:
                self.logger.warning(f"NOT门应该只有一个输入，但有 {len(gate.inputs)} 个")
                return 0
                
            input_port = gate.inputs[0]
            input_value = gate_inputs.get(input_port, 0)
            
            # 如果输入是特殊变量，输出其反相
            if isinstance(input_value, SpecialVariable):
                self.logger.debug(f"NOT门 {gate.id} 输入为特殊变量 {input_value}，输出为其反相")
                return NegatedVariable(input_value.var_id, input_value.var_name)
            # 如果输入是特殊变量的反相，输出原变量
            elif isinstance(input_value, NegatedVariable):
                self.logger.debug(f"NOT门 {gate.id} 输入为反相变量 {input_value}，输出为原变量")
                return SpecialVariable(input_value.var_id, input_value.var_name)
            # 常规值取反
            else:
                self.logger.debug(f"NOT门 {gate.id} 输入为常规值 {input_value}，输出为 {1 - input_value}")
                return 1 - input_value
        
        # AND门处理
        elif gate.type == "AND":
            self.logger.debug(f"处理AND门 {gate.id} 的输出计算")
            # 检查是否有常规0输入，有则直接返回0
            for input_port in gate.inputs:
                input_value = gate_inputs.get(input_port, 0)
                if isinstance(input_value, (int, float)) and input_value == 0:
                    self.logger.debug(f"AND门 {gate.id} 有常规0输入，直接返回0")
                    return 0
            
            # 收集特殊变量和其反相
            special_vars = {}
            negated_vars = {}
            
            for input_port in gate.inputs:
                input_value = gate_inputs.get(input_port, 0)
                if isinstance(input_value, SpecialVariable):
                    special_vars[input_value.var_id] = input_value
                    self.logger.debug(f"AND门 {gate.id} 的输入端口 {input_port} 包含特殊变量 {input_value}")
                elif isinstance(input_value, NegatedVariable):
                    negated_vars[input_value.var_id] = input_value
                    self.logger.debug(f"AND门 {gate.id} 的输入端口 {input_port} 包含反相变量 {input_value}")
            
            self.logger.debug(f"AND门 {gate.id} 的特殊变量: {special_vars}")
            self.logger.debug(f"AND门 {gate.id} 的反相变量: {negated_vars}")
            
            # 检查是否存在变量和其反相，存在则输出为0（冒险情况）
            for var_id in special_vars:
                if var_id in negated_vars:
                    self.logger.info(f"AND门 {gate.id} 同时接收到变量 {var_id} 及其反相，输出必为0（冒险情况）")
                    return 0  # AND门同时接收变量和其反相，输出必为0
            
            # 如果所有输入都是1，输出特殊变量（如果有）或1
            all_regular_inputs_are_1 = all(isinstance(gate_inputs.get(port, 0), (int, float)) and gate_inputs.get(port, 0) == 1 
                  for port in gate.inputs if port in gate_inputs 
                  and not isinstance(gate_inputs.get(port), (SpecialVariable, NegatedVariable)))
            
            self.logger.debug(f"AND门 {gate.id} 的常规输入是否全为1: {all_regular_inputs_are_1}")
            
            if all_regular_inputs_are_1:
                # 如果只有一个特殊变量，输出该变量
                if len(special_vars) == 1 and not negated_vars:
                    output = list(special_vars.values())[0]
                    self.logger.debug(f"AND门 {gate.id} 只有一个特殊变量且常规输入全为1，输出该特殊变量: {output}")
                    return output
                # 如果只有一个反相变量，输出该反相
                elif len(negated_vars) == 1 and not special_vars:
                    output = list(negated_vars.values())[0]
                    self.logger.debug(f"AND门 {gate.id} 只有一个反相变量且常规输入全为1，输出该反相变量: {output}")
                    return output
                # 如果没有特殊变量，输出1
                elif not special_vars and not negated_vars:
                    self.logger.debug(f"AND门 {gate.id} 没有特殊变量且常规输入全为1，输出1")
                    return 1
                # 多个特殊变量的情况，作为冒险处理
                else:
                    self.logger.info(f"AND门 {gate.id} 有多个特殊变量 {special_vars} 或同时有特殊变量和反相变量，简化处理为0")
                    return 0  # 简化处理，多个特殊变量情况下输出0
            
            # 其他情况输出0
            self.logger.debug(f"AND门 {gate.id} 默认情况，输出0")
            return 0
            
        # OR门处理
        elif gate.type == "OR":
            self.logger.debug(f"处理OR门 {gate.id} 的输出计算")
            # 检查是否有常规1输入，有则直接返回1
            for input_port in gate.inputs:
                input_value = gate_inputs.get(input_port, 0)
                if isinstance(input_value, (int, float)) and input_value == 1:
                    self.logger.debug(f"OR门 {gate.id} 有常规1输入，直接返回1")
                    return 1
            
            # 收集特殊变量和其反相
            special_vars = {}
            negated_vars = {}
            
            for input_port in gate.inputs:
                input_value = gate_inputs.get(input_port, 0)
                if isinstance(input_value, SpecialVariable):
                    special_vars[input_value.var_id] = input_value
                    self.logger.debug(f"OR门 {gate.id} 的输入端口 {input_port} 包含特殊变量 {input_value}")
                elif isinstance(input_value, NegatedVariable):
                    negated_vars[input_value.var_id] = input_value
                    self.logger.debug(f"OR门 {gate.id} 的输入端口 {input_port} 包含反相变量 {input_value}")
            
            self.logger.debug(f"OR门 {gate.id} 的特殊变量: {special_vars}")
            self.logger.debug(f"OR门 {gate.id} 的反相变量: {negated_vars}")
            
            # 检查是否存在变量和其反相，存在则输出为1（冒险情况）
            for var_id in special_vars:
                if var_id in negated_vars:
                    self.logger.info(f"OR门 {gate.id} 同时接收到变量 {var_id} 及其反相，输出必为1（冒险情况）")
                    return 1  # OR门同时接收变量和其反相，输出必为1
            
            # 如果所有输入都是0，输出特殊变量（如果有）或0
            all_regular_inputs_are_0 = all(isinstance(gate_inputs.get(port, 0), (int, float)) and gate_inputs.get(port, 0) == 0 
                  for port in gate.inputs if port in gate_inputs 
                  and not isinstance(gate_inputs.get(port), (SpecialVariable, NegatedVariable)))
            
            self.logger.debug(f"OR门 {gate.id} 的常规输入是否全为0: {all_regular_inputs_are_0}")
            
            if all_regular_inputs_are_0:
                # 如果只有一个特殊变量，输出该变量
                if len(special_vars) == 1 and not negated_vars:
                    output = list(special_vars.values())[0]
                    self.logger.debug(f"OR门 {gate.id} 只有一个特殊变量且常规输入全为0，输出该特殊变量: {output}")
                    return output
                # 如果只有一个反相变量，输出该反相
                elif len(negated_vars) == 1 and not special_vars:
                    output = list(negated_vars.values())[0]
                    self.logger.debug(f"OR门 {gate.id} 只有一个反相变量且常规输入全为0，输出该反相变量: {output}")
                    return output
                # 如果没有特殊变量，输出0
                elif not special_vars and not negated_vars:
                    self.logger.debug(f"OR门 {gate.id} 没有特殊变量且常规输入全为0，输出0")
                    return 0
                # 多个特殊变量的情况，作为冒险处理
                else:
                    self.logger.info(f"OR门 {gate.id} 有多个特殊变量 {special_vars} 或同时有特殊变量和反相变量，简化处理为1")
                    return 1  # 简化处理，多个特殊变量情况下输出1
            
            # 其他情况输出1
            self.logger.debug(f"OR门 {gate.id} 默认情况，输出1")
            return 1
            
        # 其他类型的门，返回默认值0
        else:
            self.logger.warning(f"不支持的门类型: {gate.type}")
            return 0
    
    def _generate_all_input_combinations(self, input_ids: List[str]) -> List[Dict[str, int]]:
        """
        生成所有可能的输入组合
        
        Args:
            input_ids: 输入ID列表
            
        Returns:
            所有可能的输入组合列表
        """
        if not input_ids:
            return [{}]  # 无输入时返回空字典
            
        # 生成所有可能的01组合
        combinations = []
        total_combinations = 2 ** len(input_ids)
        
        for i in range(total_combinations):
            combination = {}
            for j, input_id in enumerate(input_ids):
                # 将i的二进制表示转换为输入值
                bit_value = (i >> j) & 1
                combination[input_id] = bit_value
            combinations.append(combination)
            
        return combinations
    
    def _find_variables_with_negation(self) -> List[Dict]:
        """查找在电路中同时以原始形式和反相形式存在的变量"""
        result = []
        
        self.logger.info("开始查找同时存在变量及其反相的情况")
        
        # 检查每个输入变量
        for input_id, input_data in self.circuit.inputs.items():
            variable_name = input_data["name"]
            
            self.logger.info(f"分析变量: {variable_name} (ID: {input_id})")
            
            # 查找直接连接到该变量的所有门，检查是否有NOT门
            direct_not_gates = []
            
            # 打印所有连接情况，帮助调试
            self.logger.debug(f"变量 {variable_name} 的所有连接:")
            for conn in self.circuit.connections:
                if conn["from"] == input_id:
                    to_id = conn["to"]
                    to_type = "门" if to_id in self.circuit.gates else "未知"
                    if to_id in self.circuit.gates:
                        to_type = self.circuit.gates[to_id].type
                    self.logger.debug(f"  连接: {input_id} -> {to_id} (类型: {to_type})")
                    
                    if to_id in self.circuit.gates and self.circuit.gates[to_id].type == "NOT":
                        direct_not_gates.append(to_id)
                        self.logger.info(f"找到变量 {variable_name} 的直接非门: {to_id} (类型: {self.circuit.gates[to_id].type})")
            
            self.logger.info(f"变量 {variable_name} 的直接非门数量: {len(direct_not_gates)}")
            
            # 只要存在非门，就认为可能有冒险
            if direct_not_gates:
                self.logger.info(f"变量 {variable_name} 存在非形式，可能导致冒险")
                
                # 查找此变量经过的所有路径
                var_paths = self._find_variable_paths(input_id)
                
                # 分离原始路径和非路径
                original_paths = []
                negation_paths = []
                
                for path in var_paths:
                    var_index = path.index(input_id) if input_id in path else -1
                    if var_index != -1 and var_index < len(path) - 1:
                        next_gate_id = path[var_index + 1]
                        if next_gate_id in direct_not_gates:
                            negation_paths.append(path)
                            self.logger.debug(f"变量 {variable_name} 的非路径: {path}")
                        else:
                            original_paths.append(path)
                            self.logger.debug(f"变量 {variable_name} 的原始路径: {path}")
                
                self.logger.info(f"变量 {variable_name} 的原始路径数量: {len(original_paths)}, 非路径数量: {len(negation_paths)}")
                
                # 检查是否有路径最终汇合到同一个门，这是冒险的必要条件
                has_convergence = False
                convergence_points = set()
                
                # 检查原始路径和非路径是否有相同的门
                original_gates = set([gate_id for path in original_paths for gate_id in path])
                negation_gates = set([gate_id for path in negation_paths for gate_id in path])
                
                # 计算交集，排除变量本身和直接的非门
                exclude_gates = set([input_id] + direct_not_gates)
                common_gates = original_gates.intersection(negation_gates) - exclude_gates
                
                if common_gates:
                    has_convergence = True
                    convergence_points = common_gates
                    self.logger.info(f"变量 {variable_name} 的原始路径和非路径在以下门汇合: {common_gates}")
                else:
                    self.logger.info(f"变量 {variable_name} 的原始路径和非路径没有汇合点，可能不会导致冒险")
                
                result.append({
                    "variable": variable_name,
                    "id": input_id,
                    "negation_paths": negation_paths,
                    "original_paths": original_paths,
                    "direct_not_gates": direct_not_gates,
                    "has_convergence": has_convergence,
                    "convergence_points": list(convergence_points)
                })
            else:
                self.logger.info(f"变量 {variable_name} 在电路中没有非形式，不会导致冒险")
        
        self.logger.info(f"找到 {len(result)} 个存在反相形式的变量")
        if result:
            for var_info in result:
                self.logger.info(f"变量 {var_info['variable']} 可能导致冒险，汇合点: {var_info.get('convergence_points', [])}")
        
        return result
    
    def _find_variable_paths(self, var_id: str) -> List[List[str]]:
        """
        查找一个变量在电路中的所有路径
        
        Args:
            var_id: 变量ID
            
        Returns:
            包含变量的所有路径
        """
        all_paths = []
        
        self.logger.debug(f"查找变量 {var_id} 在电路中的所有路径")
        
        # 查找从变量出发的所有路径
        for output_id in self.circuit.outputs:
            source_id = self.circuit.outputs[output_id]["source"]
            self.logger.debug(f"查找从变量 {var_id} 到输出 {output_id}(源: {source_id}) 的路径")
            
            all_output_paths = self._find_all_paths_to_gate(source_id)
            
            # 筛选包含目标变量的路径
            for path in all_output_paths:
                if var_id in path:
                    all_paths.append(path)
                    self.logger.debug(f"找到包含变量 {var_id} 的路径: {path}")
        
        self.logger.info(f"变量 {var_id} 在电路中的总路径数: {len(all_paths)}")
        
        return all_paths

    def _check_direct_hazards(self) -> List[Dict]:
        """
        直接检测冒险，跳过特殊变量传播机制
        
        Returns:
            冒险列表
        """
        hazards = []
        self.logger.info("开始直接检测冒险方法")
        
        # 查找存在反相的变量
        variables_with_negation = self._find_variables_with_negation()
        
        if not variables_with_negation:
            self.logger.info("未检测到任何变量及其反相同时存在于电路中，不存在冒险")
            return hazards
        
        # 对每个变量分析其汇合点
        for var_info in variables_with_negation:
            variable = var_info["variable"]
            var_id = var_info["id"]
            
            self.logger.info(f"直接分析变量 {variable} 的冒险情况")
            
            # 如果没有汇合点，跳过
            if not var_info.get("has_convergence", False) or not var_info.get("convergence_points"):
                self.logger.info(f"变量 {variable} 没有汇合点，跳过")
                continue
            
            # 分析每个汇合点
            for gate_id in var_info.get("convergence_points", []):
                if gate_id not in self.circuit.gates:
                    self.logger.warning(f"汇合点 {gate_id} 不是有效的门ID，跳过")
                    continue
                    
                gate = self.circuit.gates[gate_id]
                gate_type = gate.type
                
                # 确定冒险类型
                hazard_type = None
                description = None
                
                if gate_type == "AND":
                    hazard_type = "静态冒险-0"
                    description = f"门 {gate_id} (AND) 可能同时接收到变量 {variable} 及其反相，可能产生静态冒险-0"
                elif gate_type == "OR":
                    hazard_type = "静态冒险-1"
                    description = f"门 {gate_id} (OR) 可能同时接收到变量 {variable} 及其反相，可能产生静态冒险-1"
                else:
                    hazard_type = "动态冒险"
                    description = f"门 {gate_id} ({gate_type}) 可能同时接收到变量 {variable} 及其反相，可能产生动态冒险"
                
                self.logger.info(f"在汇合点 {gate_id} ({gate_type}) 检测到变量 {variable} 的 {hazard_type}")
                
                # 添加冒险信息
                hazard_gates = [{
                    "gate_id": gate_id,
                    "gate_type": gate_type,
                    "inputs": gate.inputs,
                    "hazard_type": hazard_type,
                    "critical": True,
                    "description": description
                }]
                
                hazards.append({
                    "variable": variable,
                    "hazard_type": hazard_type,
                    "hazard_gates": hazard_gates,
                    "description": f"变量 {variable} 可能导致 {hazard_type}，因为存在互补输入的门"
                })
        
        self.logger.info(f"直接检测到 {len(hazards)} 个冒险")
        return hazards

class SpecialVariable:
    """表示特殊变量的类，用于冒险检测"""
    
    def __init__(self, var_id: str, var_name: str):
        self.var_id = var_id
        self.var_name = var_name
        
    def __str__(self):
        return f"X({self.var_name})"
        
    def __repr__(self):
        return self.__str__()

class NegatedVariable:
    """表示特殊变量的反相的类，用于冒险检测"""
    
    def __init__(self, var_id: str, var_name: str):
        self.var_id = var_id
        self.var_name = var_name
        
    def __str__(self):
        return f"~X({self.var_name})"
        
    def __repr__(self):
        return self.__str__() 