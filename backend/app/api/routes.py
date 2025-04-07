from flask_restx import Resource, fields
from app.api import api
from app.services.parser import CircuitParser
from app.services.detector import HazardDetector
from app.models.circuit import Circuit
from app.utils.exceptions import CircuitParseError, ValidationError
from app.dal.circuit_dal import CircuitDAL
from datetime import datetime
import logging

# API模型定义
parse_request = api.model('ParseRequest', {
    'expression': fields.String(required=True, description='逻辑表达式(如 "A AND B OR C")')
})

gate_model = api.model('Gate', {
    'id': fields.String(description='门ID'),
    'type': fields.String(description='门类型(AND/OR/NOT)'),
    'delay': fields.Float(description='门延迟(ns)'),
    'inputs': fields.List(fields.String, description='输入端口列表'),
    'output': fields.String(description='输出端口')
})

circuit_model = api.model('Circuit', {
    'name': fields.String(description='电路名称'),
    'gates': fields.List(fields.Nested(gate_model)),
    'inputs': fields.Raw(description='输入端口映射'),
    'outputs': fields.Raw(description='输出端口映射'),
    'connections': fields.List(fields.Raw(description='连接关系'))
})

hazard_result_model = api.model('HazardResult', {
    'race_conditions': fields.List(fields.Raw(description='竞争条件列表')),
    'hazards': fields.List(fields.Raw(description='冒险列表'))
})

@api.route('/')
class Index(Resource):
    def get(self):
        """API根路径"""
        return {
            "status": "success",
            "message": "电路检测系统API服务正在运行",
            "version": "1.0"
        }

@api.route('/parse')
class CircuitParserAPI(Resource):
    """电路解析API"""
    
    @api.expect(parse_request)
    @api.response(200, '解析成功', circuit_model)
    @api.response(400, '解析错误')
    def post(self):
        """解析逻辑表达式为电路模型"""
        try:
            data = api.payload
            if not data or 'expression' not in data:
                raise ValidationError("缺少电路表达式")
                
            parser = CircuitParser()
            circuit_model = parser.parse(data['expression'])
            
            # 保存到数据库
            circuit = CircuitDAL.create_circuit(
                name=f"Circuit_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                expression=data['expression']
            )
            
            # 保存门
            for gate in circuit_model.gates.values():
                CircuitDAL.add_gate(
                    circuit=circuit,
                    gate_id=gate.id,
                    gate_type=gate.type,
                    delay=gate.delay
                )
            
            # 保存连接
            for conn in circuit_model.connections:
                CircuitDAL.add_connection(
                    circuit=circuit,
                    from_id=conn['from'],
                    to_id=conn['to'],
                    delay=conn['delay']
                )
            
            return {
                "status": "success",
                "circuit": {
                    "id": circuit.id,
                    "name": circuit.name,
                    "expression": circuit.expression,
                    "inputs": {
                        input_id: {
                            "name": input_data["name"],
                            "initial_value": input_data["initial_value"]
                        }
                        for input_id, input_data in circuit_model.inputs.items()
                    },
                    "outputs": {
                        output_id: {
                            "name": output_data["name"],
                            "source": output_data["source"]
                        }
                        for output_id, output_data in circuit_model.outputs.items()
                    },
                    "gates": [
                        {
                            "id": g.gate_id,
                            "type": g.type,
                            "delay": g.delay
                        }
                        for g in circuit.gates
                    ],
                    "connections": circuit_model.connections
                }
            }
            
        except (CircuitParseError, ValidationError) as e:
            api.abort(400, str(e))
        except Exception as e:
            api.abort(500, "服务器内部错误")

@api.route('/detect')
class HazardDetection(Resource):
    """竞争冒险检测API"""
    
    @api.expect(circuit_model)
    @api.response(200, '检测成功', hazard_result_model)
    @api.response(400, '检测错误')
    def post(self):
        """检测电路中的竞争和冒险"""
        logger = logging.getLogger(__name__)
        
        try:
            data = api.payload
            logger.info(f"接收到检测请求: {data.get('circuit', {}).get('name', '未命名')}")
            
            if not data or 'circuit' not in data:
                logger.error("请求数据缺少circuit字段")
                raise ValidationError("缺少电路数据")
            
            # 记录接收到的数据结构
            logger.debug(f"接收到的电路数据: {data}")
            
            # 预处理电路数据，确保每个门都有inputs和output字段
            circuit_data = data['circuit']
            if 'gates' in circuit_data and 'connections' in circuit_data:
                for gate in circuit_data['gates']:
                    # 如果门缺少inputs字段，从connections中推断
                    if 'inputs' not in gate:
                        gate['inputs'] = []
                        for conn in circuit_data['connections']:
                            if conn['to'] == gate['id']:
                                gate['inputs'].append(conn['from'])
                        logger.info(f"为门 {gate['id']} 推断inputs: {gate['inputs']}")
                    
                    # 如果门缺少output字段，假设与门ID相同
                    if 'output' not in gate:
                        # 输出端口需修改，并不是真正的经计算过后的输出端口
                        gate['output'] = gate['id']
                        logger.info(f"为门 {gate['id']} 设置默认output: {gate['output']}")
            
            try:
                circuit = Circuit.from_dict(data)
                logger.info(f"电路解析成功: {circuit.name}, 包含 {len(circuit.gates)} 个门")
            except Exception as e:
                logger.error(f"电路解析失败: {str(e)}")
                logger.error(f"电路数据: {data}")
                raise ValidationError(f"电路数据格式错误: {str(e)}")
            
            try:
                detector = HazardDetector(circuit)
                logger.info("开始检测电路中的竞争和冒险")
                results = detector.detect_hazards()
                logger.info(f"检测完成: 发现 {len(results['race_conditions'])} 个竞争条件, {len(results['hazards'])} 个冒险")
            except Exception as e:
                logger.error(f"检测过程出错: {str(e)}")
                import traceback
                logger.error(traceback.format_exc())
                raise Exception(f"检测过程出错: {str(e)}")
            
            return {
                "status": "success",
                "results": results
            }
            
        except ValidationError as e:
            logger.error(f"验证错误: {str(e)}")
            api.abort(400, str(e))
        except Exception as e:
            logger.error(f"服务器内部错误: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
            api.abort(500, f"服务器内部错误: {str(e)}")

@api.route('/simulate')
class CircuitSimulation(Resource):
    """电路仿真API"""
    
    @api.expect(api.model('SimulationRequest', {
        'circuit_id': fields.Integer(description='电路ID', required=False),
        'circuit': fields.Nested(circuit_model, required=False),
        'inputs': fields.Raw(description='输入值映射 {input_id: value}', required=True)
    }))
    @api.response(200, '仿真成功')
    @api.response(400, '仿真错误')
    def post(self):
        """仿真电路，计算输出值，并生成逻辑表达式"""
        logger = logging.getLogger(__name__)
        
        try:
            data = api.payload
            logger.info(f"接收到仿真请求")
            
            if not data or 'inputs' not in data:
                logger.error("请求数据缺少inputs字段")
                raise ValidationError("缺少输入值数据")
            
            # 获取电路
            circuit = None
            if 'circuit_id' in data and data['circuit_id']:
                # 从数据库获取电路
                circuit_model = CircuitDAL.get_circuit_by_id(data['circuit_id'])
                if not circuit_model:
                    raise ValidationError(f"未找到ID为 {data['circuit_id']} 的电路")
                
                # 将数据库模型转换为电路对象
                # 这里需要根据您的具体实现来完成转换
                circuit = Circuit(circuit_model.name)
                # ...转换逻辑...
                
            elif 'circuit' in data and data['circuit']:
                # 使用请求中的电路数据
                try:
                    circuit = Circuit.from_dict(data)
                except Exception as e:
                    logger.error(f"电路解析失败: {str(e)}")
                    raise ValidationError(f"电路数据格式错误: {str(e)}")
            else:
                raise ValidationError("请提供circuit_id或circuit")
            
            # 获取输入值
            input_values = data['inputs']
            
            # 执行电路计算
            try:
                results = circuit.compute_circuit(input_values)
                logger.info("电路计算完成")
            except Exception as e:
                logger.error(f"电路计算失败: {str(e)}")
                raise ValidationError(f"电路计算错误: {str(e)}")
            
            # 为输出生成逻辑表达式
            expression = None
            simplified_expression = None
            hazard_type = None
            
            try:
                if len(circuit.outputs) > 0:
                    # 创建检测器
                    detector = HazardDetector(circuit)
                    
                    # 使用新的方法检测冒险
                    hazard_results = detector._detect_hazards_by_expression()
                    
                    if hazard_results:
                        # 获取第一个检测到的冒险
                        hazard = hazard_results[0]
                        hazard_type = hazard["hazard_type"]
                        expression = f"检测到 {hazard_type}"
                        simplified_expression = f"变量 {hazard['variable']} 可能导致冒险，原因是存在互补输入的门"
                        logger.info(f"检测到冒险: {hazard_type}")
                    else:
                        expression = "未检测到冒险"
                        simplified_expression = "电路不存在变量及其反相同时存在的情况"
                        logger.info("未检测到冒险")
            except Exception as e:
                logger.error(f"冒险检测失败: {str(e)}")
                # 不要因为冒险检测失败而中断整个仿真
                logger.error(traceback.format_exc())
            
            return {
                "status": "success",
                "results": results,
                "expression": expression,
                "simplified_expression": simplified_expression,
                "hazard_type": hazard_type
            }
            
        except ValidationError as e:
            logger.error(f"验证错误: {str(e)}")
            api.abort(400, str(e))
        except Exception as e:
            logger.error(f"服务器内部错误: {str(e)}")
            import traceback
            logger.error(traceback.format_exc())
            api.abort(500, f"服务器内部错误: {str(e)}")

@api.route('/circuits')
class CircuitList(Resource):
    """电路列表API"""
    
    @api.response(200, '获取成功')
    def get(self):
        """获取所有电路"""
        circuits = CircuitDAL.get_all_circuits()
        return {
            "status": "success",
            "circuits": [
                {
                    "id": c.id,
                    "name": c.name,
                    "expression": c.expression,
                    "created_at": c.created_at.isoformat()
                }
                for c in circuits
            ]
        }

@api.route('/circuits/<int:circuit_id>')
class CircuitDetail(Resource):
    """电路详情API"""
    
    @api.response(200, '获取成功')
    @api.response(404, '电路不存在')
    def get(self, circuit_id):
        """获取电路详情"""
        circuit = CircuitDAL.get_circuit_by_id(circuit_id)
        if not circuit:
            api.abort(404, "电路不存在")
            
        return {
            "status": "success",
            "circuit": {
                "id": circuit.id,
                "name": circuit.name,
                "expression": circuit.expression,
                "gates": [
                    {
                        "id": g.gate_id,
                        "type": g.type,
                        "delay": g.delay
                    }
                    for g in circuit.gates
                ],
                "detection_results": [
                    {
                        "type": r.result_type,
                        "description": r.description,
                        "details": r.details,
                        "created_at": r.created_at.isoformat()
                    }
                    for r in circuit.detection_results
                ]
            }
        }
    
    @api.response(200, '删除成功')
    @api.response(404, '电路不存在')
    def delete(self, circuit_id):
        """删除电路"""
        if CircuitDAL.delete_circuit(circuit_id):
            return {"status": "success", "message": "电路已删除"}
        api.abort(404, "电路不存在") 