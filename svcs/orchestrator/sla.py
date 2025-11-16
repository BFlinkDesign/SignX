from dataclasses import dataclass


@dataclass(frozen=True)
class SLAs:
	materials_ms: int = 800
	stackup_ms: int = 1500
	dfma_ms: int = 900
	cad_ms: int = 1200
	parts_ms: int = 1000
	compliance_ms: int = 900
	eval_ms: int = 700


SLA = SLAs()
