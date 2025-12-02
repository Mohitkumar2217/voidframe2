from src.web_search import duckduckgo_search

class CostBenchmarkEngine:
    def benchmark(self, project_type, dpr_cost):
        results = duckduckgo_search(f"{project_type} India CPWD PWD", max_results=3)
        return {"benchmarks": results, "dpr_cost": dpr_cost}
