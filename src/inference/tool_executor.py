import json
import logging
from src.database.queries import (
    get_risk_patterns,
    get_benchmarks,
    get_lean_concept,
    get_investment_criteria,
    get_similar_startups,
    get_pivot_cases
)
from src.database.client import execute_safe_tool_query

logger = logging.getLogger(__name__)

class ToolExecutor:
    """
    Exécute les outils (tools) appelés par le modèle LFM.
    
    Le modèle Liquid LFM utilise généralement un format spécifique pour les tool calls :
    <|tool_call_start|>[tool_name(arg1="val", ...)]<|tool_call_end|>
    """
    
    def __init__(self):
        # Mapping des noms de fonctions exposées au LLM vers les implémentations Python
        self.available_tools = {
            "get_risk_patterns": get_risk_patterns,
            "get_benchmarks": get_benchmarks,
            "get_lean_concept": get_lean_concept,
            "get_investment_criteria": get_investment_criteria,
            "get_similar_startups": get_similar_startups,
            "get_pivot_cases": get_pivot_cases,
            "query_postgresql": execute_safe_tool_query
        }

    def execute(self, tool_name: str, args_dict: dict) -> str:
        """
        Exécute un outil et retourne le résultat sous forme de chaîne JSON.
        
        Args:
            tool_name : Nom de l'outil à appeler.
            args_dict : Dictionnaire des arguments à passer à la fonction.
        """
        if tool_name not in self.available_tools:
            logger.warning(f"Outil inconnu appelé : {tool_name}")
            return json.dumps({"error": f"Tool '{tool_name}' is not defined."})
        
        try:
            logger.info(f"Exécution de l'outil : {tool_name} avec {args_dict}")
            result = self.available_tools[tool_name](**args_dict)
            
            # On s'assure que le résultat est sérialisable en JSON
            return json.dumps(result, ensure_ascii=False, default=str)
            
        except Exception as e:
            logger.error(f"Erreur lors de l'exécution de l'outil {tool_name} : {e}")
            return json.dumps({"error": str(e)})

    def parse_and_execute(self, content: str) -> list[dict]:
        """
        Analyse le contenu généré par le modèle pour trouver des tool calls
        et les exécuter. Retourne une liste de messages de rôle 'tool'.
        
        Note: Cette implémentation simplifiée suppose un format : 
        [tool_name(arg="val")]
        """
        # TODO: Implémenter un parser robuste pour les balises <|tool_call_start|>
        # Pour l'instant, on se concentre sur l'exécution
        return []
