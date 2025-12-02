from src.web_search import duckduckgo_search

class ComplianceChecker:
    SCHEMES = [
        "PMGSY guidelines",
        "AMRUT DPR rules",
        "Smart Cities DPR format",
        "MoRTH standards",
        "Jal Jeevan Mission guidelines",
        "NEC DPR structure"
    ]

    def check(self, text):
        return {
            scheme: duckduckgo_search(f"{scheme}", max_results=2)
            for scheme in self.SCHEMES
        }
