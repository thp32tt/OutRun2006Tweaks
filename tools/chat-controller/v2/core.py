from dataclasses import dataclass


@dataclass
class Pipeline:
    config: dict

    def run(self):
        stages = self.config.get("pipeline", [])
        if stages != ["A", "B", "C"]:
            raise RuntimeError("Localization pipeline must be A_B_THEN_C_BARRIER")
        return {"status": "READY", "barrier": "C"}
