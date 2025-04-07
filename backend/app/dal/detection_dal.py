from typing import List, Optional
from app import db
from app.models.database import Circuit, DetectionResult
from datetime import datetime, UTC

class DetectionDAL:
    """检测结果数据访问层"""
    
    @staticmethod
    def get_circuit_results(circuit_id: int) -> List[DetectionResult]:
        """获取电路的所有检测结果"""
        return DetectionResult.query.filter_by(circuit_id=circuit_id).all()
    
    @staticmethod
    def get_latest_result(circuit_id: int) -> Optional[DetectionResult]:
        """获取电路的最新检测结果"""
        return DetectionResult.query.filter_by(circuit_id=circuit_id)\
            .order_by(DetectionResult.created_at.desc())\
            .first()
    
    @staticmethod
    def add_race_condition(
        circuit: Circuit,
        gate_id: str,
        input1: str,
        input2: str,
        delay1: float,
        delay2: float
    ) -> DetectionResult:
        """添加竞争条件检测结果"""
        description = f"在门{gate_id}检测到输入{input1}和{input2}之间的竞争条件"
        details = {
            "gate_id": gate_id,
            "input1": input1,
            "input2": input2,
            "delay1": delay1,
            "delay2": delay2
        }
        
        result = DetectionResult(
            circuit_id=circuit.id,
            result_type="race_condition",
            description=description,
            details=details,
            created_at=datetime.now(UTC)
        )
        
        db.session.add(result)
        db.session.commit()
        return result
    
    @staticmethod
    def add_hazard(
        circuit: Circuit,
        output_id: str,
        paths: List[List[str]],
        max_delay: float,
        min_delay: float
    ) -> DetectionResult:
        """添加冒险检测结果"""
        description = f"在输出{output_id}检测到静态冒险"
        details = {
            "output_id": output_id,
            "paths": paths,
            "max_delay": max_delay,
            "min_delay": min_delay,
            "delay_difference": max_delay - min_delay
        }
        
        result = DetectionResult(
            circuit_id=circuit.id,
            result_type="hazard",
            description=description,
            details=details,
            created_at=datetime.now(UTC)
        )
        
        db.session.add(result)
        db.session.commit()
        return result 