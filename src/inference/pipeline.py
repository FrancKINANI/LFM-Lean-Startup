import logging
import re
from typing import List, Dict, Any
from src.inference.model import LFMAnalyst
from src.inference.tool_executor import ToolExecutor

logger = logging.getLogger(__name__)

class LeanStartupAnalystPipeline:
    """
    Pipeline principal orchestrant l'agent intelligent.
    Gère le cycle : Pensée -> Appel d'outil (facultatif) -> Réponse finale.
    """
    
    def __init__(self, model_id: str = "LiquidAI/LFM2.5-350M-Base", adapter_path: str = None):
        self.model = LFMAnalyst(model_id, adapter_path)
        self.executor = ToolExecutor()
        self.max_iterations = 3 # Éviter les boucles infinies d'appels d'outils

    def _extract_tool_call(self, text: str):
        """
        Extrait les informations d'un appel d'outil dans le texte.
        Format attendu : <|tool_call_start|>[tool_name(arg1="val1", ...)]<|tool_call_end|>
        """
        pattern = r"<\|tool_call_start\|>\[(\w+)\((.*)\)\]<\|tool_call_end|>"
        match = re.search(pattern, text)
        if not match:
            return None, None
        
        tool_name = match.group(1)
        args_str = match.group(2)
        
        # Parsing très simple des arguments (clé="valeur")
        args_dict = {}
        arg_pattern = r'(\w+)\s*=\s*["\']([^"\']+)["\']'
        for arg_match in re.finditer(arg_pattern, args_str):
            args_dict[arg_match.group(1)] = arg_match.group(2)
            
        return tool_name, args_dict

    def run(self, user_query: str, system_prompt: str = None) -> str:
        """
        Exécute la boucle agentique pour répondre à une requête utilisateur.
        """
        if not system_prompt:
            system_prompt = (
                "Tu es un analyste Lean Startup expert. Tu as accès à une base de données "
                "de patterns de risque, benchmarks et cas de startups via des outils SQL. "
                "Si tu as besoin d'informations factuelles, utilise les outils. "
                "Réponds toujours de façon structurée et accessible."
            )

        messages = [
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": user_query}
        ]

        for i in range(self.max_iterations):
            logger.info(f"Iteration {i+1}/{self.max_iterations}")
            
            # 1. Génération par le modèle
            response = self.model.generate(messages)
            
            # 2. Vérification d'un appel d'outil
            tool_name, args = self._extract_tool_call(response)
            
            if not tool_name:
                # Pas d'outil, c'est la réponse finale
                return response
            
            # 3. Exécution de l'outil
            logger.info(f"Le modèle appelle l'outil : {tool_name}")
            tool_result = self.executor.execute(tool_name, args)
            
            # 4. Ajout au contexte et relance
            messages.append({"role": "assistant", "content": response})
            messages.append({"role": "tool", "content": tool_result})
            
            # On continue la boucle pour que le modèle traite le résultat de l'outil
            
        return "Désolé, j'ai atteint la limite d'itérations sans pouvoir conclure."

if __name__ == "__main__":
    # Pipeline de test (nécessite le modèle et la DB configurés)
    # pipeline = LeanStartupAnalystPipeline()
    # print(pipeline.run("Analyse les risques pour un SaaS B2B en Seed."))
    pass
