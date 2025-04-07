from typing import List, Optional
from app import db
from app.models.database import Circuit, Gate, Connection, DetectionResult

class CircuitDAL:
    """电路数据访问层"""
    
    @staticmethod
    def create_circuit(name: str, expression: str = None) -> Circuit:
        """创建新电路"""
        circuit = Circuit(name=name, expression=expression)
        db.session.add(circuit)
        db.session.commit()
        return circuit
    
    @staticmethod
    def add_gate(circuit: Circuit, gate_id: str, gate_type: str, delay: float) -> Gate:
        """添加逻辑门"""
        gate = Gate(
            gate_id=gate_id,
            type=gate_type,
            delay=delay,
            circuit_id=circuit.id
        )
        db.session.add(gate)
        db.session.commit()
        return gate
    
    @staticmethod
    def add_connection(circuit: Circuit, from_id: str, to_id: str, delay: float) -> Connection:
        """添加连接"""
        connection = Connection(
            from_id=from_id,
            to_id=to_id,
            delay=delay,
            circuit_id=circuit.id
        )
        db.session.add(connection)
        db.session.commit()
        return connection
    
    @staticmethod
    def add_detection_result(
        circuit: Circuit,
        result_type: str,
        description: str,
        details: dict = None
    ) -> DetectionResult:
        """添加检测结果"""
        result = DetectionResult(
            circuit_id=circuit.id,
            result_type=result_type,
            description=description,
            details=details
        )
        db.session.add(result)
        db.session.commit()
        return result
    
    @staticmethod
    def get_circuit_by_id(circuit_id: int) -> Optional[Circuit]:
        """根据ID获取电路"""
        return Circuit.query.get(circuit_id)
    
    @staticmethod
    def get_all_circuits() -> List[Circuit]:
        """获取所有电路"""
        return Circuit.query.all()
    
    @staticmethod
    def delete_circuit(circuit_id: int) -> bool:
        """删除电路"""
        circuit = Circuit.query.get(circuit_id)
        if circuit:
            db.session.delete(circuit)
            db.session.commit()
            return True
        return False 