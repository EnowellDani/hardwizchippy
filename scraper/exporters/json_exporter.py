import json
from datetime import datetime
from pathlib import Path
import logging

class JsonExporter:
    def __init__(self, output_dir: str = None):
        self.output_dir = Path(output_dir or "data/output")
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.logger = logging.getLogger("exporter.json")
    
    def export_cpus(self, cpus: list, filename: str = "cpu_database.json"):
        output = {
            "version": "2.0",
            "generated_at": datetime.utcnow().isoformat() + "Z",
            "total": len(cpus),
            "cpus": [self._format_cpu(cpu) for cpu in cpus]
        }
        
        filepath = self.output_dir / filename
        with open(filepath, "w", encoding="utf-8") as f:
            json.dump(output, f, indent=2, ensure_ascii=False)
        
        self.logger.info(f"Exported {len(cpus)} CPUs to {filepath}")
        return filepath
    
    def _format_cpu(self, cpu: dict) -> dict:
        return {
            "id": cpu.get("id", 0),
            "name": cpu.get("name", ""),
            "manufacturer": cpu.get("manufacturer_name") or self._detect_manufacturer(cpu.get("name", "")),
            "general": {
                "launch_date": cpu.get("launch_date_raw"),
                "launch_price": cpu.get("launch_msrp"),
                "current_price": cpu.get("current_price"),
                "fab": cpu.get("fab_processor"),
                "process_node": cpu.get("process_node"),
                "transistor_count": cpu.get("transistors_million"),
                "die_size": cpu.get("die_size_mm2"),
                "tdp": cpu.get("tdp"),
                "socket": cpu.get("socket_name"),
            },
            "cores": {
                "microarchitecture": cpu.get("microarchitecture"),
                "codename": cpu.get("codename"),
                "core_stepping": cpu.get("core_stepping"),
                "cores": cpu.get("cores"),
                "threads": cpu.get("threads"),
                "base_frequency": cpu.get("base_clock"),
                "turbo_frequency": cpu.get("boost_clock"),
                "unlocked": cpu.get("unlocked_multiplier", False),
            },
            "cache": {
                "l1_instruction": cpu.get("l1_cache_instruction"),
                "l1_data": cpu.get("l1_cache_data"),
                "l2": cpu.get("l2_cache"),
                "l3": cpu.get("l3_cache"),
            },
            "memory": {
                "type": cpu.get("memory_type"),
                "bandwidth": cpu.get("memory_bandwidth"),
                "channels": cpu.get("memory_channels"),
                "max_size": cpu.get("max_memory_gb"),
                "ecc": cpu.get("ecc_supported", False),
            },
            "graphics": {
                "name": cpu.get("integrated_gpu_name") if cpu.get("has_integrated_gpu") else None,
                "base_freq": cpu.get("graphics_base_freq"),
                "turbo_freq": cpu.get("graphics_turbo_freq"),
            } if cpu.get("has_integrated_gpu") else None,
            "pcie": {
                "revision": cpu.get("pcie_version"),
                "lanes": cpu.get("pcie_lanes"),
                "config": cpu.get("pcie_config"),
            },
            "benchmarks": cpu.get("benchmarks", {}),
            "gaming": cpu.get("gaming", []),
        }
    
    def _detect_manufacturer(self, name: str) -> str:
        name_lower = name.lower()
        if any(x in name_lower for x in ["ryzen", "epyc", "athlon", "threadripper"]):
            return "AMD"
        elif any(x in name_lower for x in ["core", "xeon", "celeron", "pentium"]):
            return "Intel"
        return "Unknown"

