"""
src/inference/pipeline.py
=========================
Pipeline d'inférence complet : du texte utilisateur à la réponse finale.

Orchestre trois composants :
    1. model.py        → charge et utilise LFM2.5
    2. tool_executor   → intercepte et exécute les tool calls PostgreSQL
    3. queries.py      → accès structuré à la base de données

Flux principal :
    prompt utilisateur
        → construction du contexte (system prompt + historique)
        → première génération (le modèle peut appeler des outils)
        → exécution des tool calls (si présents)
        → deuxième génération avec les données récupérées
        → réponse finale

Dépendances :
    pip install transformers torch accelerate
"""

import logging
from dataclasses import dataclass, field
from typing import Any

from src.inference.tool_executor import (
    build_tools_system_prompt,
    build_tool_messages,
    detect_tool_calls,
    execute_all_tool_calls,
    has_tool_call,
    split_text_and_tool_calls,
)

logger = logging.getLogger(__name__)


# =============================================================================
# CONFIGURATION DU PIPELINE
# =============================================================================

@dataclass
class PipelineConfig:
    """
    Paramètres de génération du modèle.
    Valeurs par défaut calibrées pour l'analyse Lean Startup :
    - température modérée pour des réponses cohérentes mais nuancées
    - pas de sampling trop agressif qui hallucinerait des métriques
    """
    model_path: str = "models/lfm25-350m-lean"  # chemin après fine-tuning
    base_model:  str = "liquid-ai/LFM2.5-350M-Base"

    # Paramètres de génération — première passe (avec tool calls)
    max_new_tokens_first:  int   = 512
    temperature_first:     float = 0.3   # basse : on veut un tool call précis
    do_sample_first:       bool  = True

    # Paramètres de génération — deuxième passe (réponse finale)
    max_new_tokens_final:  int   = 1024
    temperature_final:     float = 0.7   # plus haute : réponse plus naturelle
    do_sample_final:       bool  = True
    top_p:                 float = 0.9

    # Contrôle du pipeline
    max_tool_call_rounds:  int   = 3     # évite les boucles infinies
    device:                str   = "auto"


# =============================================================================
# SYSTEM PROMPT
# =============================================================================

BASE_SYSTEM_PROMPT = """Tu es un analyste Lean Startup expert. Tu évalues les opportunités d'investissement et identifies les dangers critiques pour les startups.

Ton rôle :
- Analyser les informations fournies sur une startup en texte libre
- Identifier les risques critiques de manière claire et accessible
- Évaluer l'opportunité d'investissement selon le profil de l'interlocuteur
- Rendre accessible ce que les whitepapers et documents techniques rendent opaque
- T'appuyer sur des données réelles (benchmarks, cas similaires) via tes outils

Ton style :
- Clair, structuré, sans jargon inutile
- Exigeant sur les faits, bienveillant sur la forme
- Adapté à l'interlocuteur (investisseur ou entrepreneur)

{tools_section}"""


def build_system_prompt(include_tools: bool = True) -> str:
    """
    Construit le system prompt complet avec ou sans section outils.

    Args:
        include_tools : Si True, inclut la définition des outils PostgreSQL.

    Returns:
        System prompt formaté.
    """
    tools_section = build_tools_system_prompt() if include_tools else ""
    return BASE_SYSTEM_PROMPT.format(tools_section=tools_section).strip()


# =============================================================================
# STRUCTURES DE DONNÉES
# =============================================================================

@dataclass
class AnalysisRequest:
    """
    Requête d'analyse entrante.
    Encapsule le texte utilisateur et le contexte optionnel.
    """
    user_input: str
    investor_profile: str = "both"        # "angel", "vc", "impact", "entrepreneur", "both"
    conversation_history: list[dict] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class AnalysisResponse:
    """
    Réponse d'analyse complète avec traçabilité du pipeline.
    """
    final_answer: str
    tool_calls_made: int = 0
    tool_calls_successful: int = 0
    data_sources_used: list[str] = field(default_factory=list)
    intermediate_thinking: str = ""
    error: str | None = None

    @property
    def success(self) -> bool:
        return self.error is None


# =============================================================================
# MODÈLE — CHARGEMENT ET GÉNÉRATION
# =============================================================================

class LFMModel:
    """
    Wrapper autour du modèle LFM2.5 fine-tuné.

    Séparation du chargement et de la génération pour pouvoir
    réutiliser l'instance entre plusieurs requêtes (le chargement
    d'un modèle prend 10-30 secondes).
    """

    def __init__(self, config: PipelineConfig):
        self.config = config
        self._model = None
        self._tokenizer = None

    def load(self) -> None:
        """
        Charge le modèle et le tokenizer en mémoire.
        À appeler une seule fois au démarrage du serveur.
        """
        import torch
        from transformers import AutoModelForCausalLM, AutoTokenizer

        logger.info("Chargement du modèle : %s", self.config.model_path)

        device_map = (
            "auto" if self.config.device == "auto"
            else {"": self.config.device}
        )

        self._tokenizer = AutoTokenizer.from_pretrained(
            self.config.model_path,
            trust_remote_code=True,
        )

        self._model = AutoModelForCausalLM.from_pretrained(
            self.config.model_path,
            device_map=device_map,
            torch_dtype=torch.bfloat16,  # bfloat16 optimal pour LFM2.5
            trust_remote_code=True,
        )
        self._model.eval()

        logger.info(
            "Modèle chargé sur %s — dtype: bfloat16",
            next(self._model.parameters()).device,
        )

    def generate(
        self,
        messages: list[dict[str, str]],
        max_new_tokens: int = 512,
        temperature: float = 0.7,
        do_sample: bool = True,
        top_p: float = 0.9,
    ) -> str:
        """
        Génère une réponse à partir d'une liste de messages.

        Args:
            messages       : Liste de dicts {"role": ..., "content": ...}
                             Le premier message DOIT avoir role="system".
            max_new_tokens : Nombre maximum de tokens à générer.
            temperature    : Température de sampling (0=déterministe, 1=créatif).
            do_sample      : Si False, greedy decoding (température ignorée).
            top_p          : Nucleus sampling threshold.

        Returns:
            Texte généré par le modèle (sans le prompt d'entrée).
        """
        import torch

        if self._model is None or self._tokenizer is None:
            raise RuntimeError(
                "Modèle non chargé. Appeler load() avant generate()."
            )

        # Formatage au format chat de LFM2.5
        input_text = self._tokenizer.apply_chat_template(
            messages,
            tokenize=False,
            add_generation_prompt=True,
        )

        inputs = self._tokenizer(
            input_text,
            return_tensors="pt",
            truncation=True,
            max_length=4096,
        ).to(self._model.device)

        input_length = inputs["input_ids"].shape[1]

        with torch.no_grad():
            outputs = self._model.generate(
                **inputs,
                max_new_tokens=max_new_tokens,
                temperature=temperature if do_sample else 1.0,
                do_sample=do_sample,
                top_p=top_p if do_sample else 1.0,
                pad_token_id=self._tokenizer.eos_token_id,
            )

        # Décoder uniquement les tokens générés (pas le prompt)
        generated_ids = outputs[0][input_length:]
        return self._tokenizer.decode(generated_ids, skip_special_tokens=False)

    @property
    def is_loaded(self) -> bool:
        return self._model is not None and self._tokenizer is not None


# =============================================================================
# PIPELINE PRINCIPAL
# =============================================================================

class LeanStartupPipeline:
    """
    Pipeline d'inférence complet pour l'analyse Lean Startup.

    Gère automatiquement la boucle tool use :
    - Génère une première réponse
    - Détecte si le modèle veut appeler des outils
    - Exécute les outils et injecte les résultats
    - Regénère la réponse finale avec les données enrichies

    Usage :
        pipeline = LeanStartupPipeline()
        pipeline.load()

        response = pipeline.analyze(AnalysisRequest(
            user_input="Nous développons une marketplace...",
            investor_profile="angel"
        ))
        print(response.final_answer)
    """

    def __init__(self, config: PipelineConfig | None = None):
        self.config = config or PipelineConfig()
        self.model = LFMModel(self.config)

    def load(self) -> None:
        """Charge le modèle. À appeler au démarrage."""
        self.model.load()

    def analyze(self, request: AnalysisRequest) -> AnalysisResponse:
        """
        Point d'entrée principal du pipeline.

        Args:
            request : AnalysisRequest avec le texte utilisateur.

        Returns:
            AnalysisResponse avec la réponse finale et les métadonnées.
        """
        if not self.model.is_loaded:
            return AnalysisResponse(
                final_answer="",
                error="Modèle non chargé. Appeler pipeline.load() d'abord.",
            )

        try:
            return self._run_pipeline(request)
        except Exception as e:
            logger.error("Erreur dans le pipeline d'inférence : %s", e)
            return AnalysisResponse(
                final_answer="Une erreur est survenue lors de l'analyse.",
                error=str(e),
            )

    def _run_pipeline(self, request: AnalysisRequest) -> AnalysisResponse:
        """
        Exécution interne du pipeline avec boucle tool use.

        Étapes :
            1. Construction du contexte initial
            2. Première génération (peut contenir des tool calls)
            3. Boucle : exécuter les tool calls → régénérer
            4. Retourner la réponse finale
        """
        # -------------------------------------------------------
        # 1. Construction du contexte
        # -------------------------------------------------------
        system_prompt = build_system_prompt(include_tools=True)

        # Ajout d'une instruction selon le profil de l'interlocuteur
        profile_instruction = self._get_profile_instruction(request.investor_profile)
        if profile_instruction:
            system_prompt = f"{system_prompt}\n\n{profile_instruction}"

        # Construction des messages initiaux
        messages: list[dict[str, str]] = [
            {"role": "system", "content": system_prompt}
        ]

        # Historique de conversation (si multi-tour)
        messages.extend(request.conversation_history)

        # Message de l'utilisateur
        messages.append({"role": "user", "content": request.user_input})

        # -------------------------------------------------------
        # 2. Boucle de génération avec tool use
        # -------------------------------------------------------
        tool_calls_made = 0
        tool_calls_successful = 0
        data_sources: list[str] = []
        intermediate_thinking = ""

        for round_num in range(self.config.max_tool_call_rounds):
            logger.debug("Pipeline — round %d/%d", round_num + 1, self.config.max_tool_call_rounds)

            # Paramètres selon si c'est la première passe ou les suivantes
            is_first_round = (round_num == 0)
            max_tokens  = self.config.max_new_tokens_first if is_first_round else self.config.max_new_tokens_final
            temperature = self.config.temperature_first    if is_first_round else self.config.temperature_final

            # Génération
            model_output = self.model.generate(
                messages=messages,
                max_new_tokens=max_tokens,
                temperature=temperature,
                do_sample=self.config.do_sample_final,
                top_p=self.config.top_p,
            )

            logger.debug("Sortie modèle (round %d) : %s...", round_num + 1, model_output[:200])

            # -------------------------------------------------------
            # 3. Détection et exécution des tool calls
            # -------------------------------------------------------
            if has_tool_call(model_output):
                text_before, tool_calls = split_text_and_tool_calls(model_output)

                if text_before:
                    intermediate_thinking += text_before + "\n"

                if not tool_calls:
                    # Token détecté mais parsing échoué → on arrête la boucle
                    logger.warning("Token tool call détecté mais aucun call parseable.")
                    break

                # Ajouter la réponse du modèle à l'historique
                messages.append({"role": "assistant", "content": model_output})

                # Exécuter tous les tool calls
                results = execute_all_tool_calls(tool_calls)
                tool_calls_made += len(tool_calls)
                tool_calls_successful += sum(1 for r in results if r.success)

                # Enregistrer les sources utilisées
                for tc in tool_calls:
                    if tc.sql:
                        # Extraire le nom de la table principale de la requête
                        source = self._extract_table_name(tc.sql)
                        if source and source not in data_sources:
                            data_sources.append(source)

                # Injecter les résultats dans le contexte
                tool_messages = build_tool_messages(tool_calls, results)
                messages.extend(tool_messages)

                # Continuer la boucle pour générer la réponse finale

            else:
                # Pas de tool call → c'est la réponse finale
                # Nettoyer les tokens spéciaux résiduels
                final_answer = self._clean_output(model_output)

                return AnalysisResponse(
                    final_answer=final_answer,
                    tool_calls_made=tool_calls_made,
                    tool_calls_successful=tool_calls_successful,
                    data_sources_used=data_sources,
                    intermediate_thinking=intermediate_thinking.strip(),
                )

        # Si on sort de la boucle sans réponse finale (max rounds atteint)
        logger.warning("Nombre maximum de rounds atteint sans réponse finale.")
        fallback_output = self.model.generate(
            messages=messages,
            max_new_tokens=self.config.max_new_tokens_final,
            temperature=self.config.temperature_final,
            do_sample=False,  # greedy pour être sûr d'avoir une réponse
        )

        return AnalysisResponse(
            final_answer=self._clean_output(fallback_output),
            tool_calls_made=tool_calls_made,
            tool_calls_successful=tool_calls_successful,
            data_sources_used=data_sources,
            intermediate_thinking=intermediate_thinking.strip(),
        )

    # ==========================================================
    # HELPERS
    # ==========================================================

    def _get_profile_instruction(self, investor_profile: str) -> str:
        """
        Retourne une instruction complémentaire selon le profil de l'utilisateur.
        Permet au modèle d'adapter le niveau et le ton de sa réponse.
        """
        profiles = {
            "entrepreneur": (
                "L'interlocuteur est un entrepreneur. "
                "Concentre-toi sur des conseils actionnables, les étapes concrètes "
                "et les façons d'améliorer la situation. Sois constructif."
            ),
            "angel": (
                "L'interlocuteur est un angel investor. "
                "Structure ta réponse autour de : qualité de l'équipe, taille du marché, "
                "premiers signaux de traction, et risques de dilution. "
                "Sois direct sur le go/no-go."
            ),
            "vc": (
                "L'interlocuteur est un venture capitalist. "
                "Il attend des métriques précises, une analyse des unit economics, "
                "une évaluation de la scalabilité et du potentiel de sortie. "
                "Utilise le vocabulaire technique approprié."
            ),
            "impact": (
                "L'interlocuteur est un investisseur à impact. "
                "Évalue autant la théorie du changement et les métriques d'impact "
                "que la viabilité financière. Les deux doivent être alignées."
            ),
            "both": (
                "La réponse doit être utile à la fois pour un investisseur "
                "et pour l'entrepreneur. Structure-la en deux parties si nécessaire."
            ),
        }
        return profiles.get(investor_profile, "")

    def _clean_output(self, text: str) -> str:
        """
        Nettoie la sortie du modèle :
        - Supprime les tokens spéciaux LFM2.5 résiduels
        - Supprime les tool call blocks non-exécutés
        - Trim les espaces
        """
        import re

        # Supprimer les blocs tool call résiduels
        text = re.sub(
            r"<\|tool_call_start\|>.*?<\|tool_call_end\|>",
            "",
            text,
            flags=re.DOTALL,
        )

        # Supprimer les tokens spéciaux LFM2.5
        special_tokens = [
            "<|im_start|>", "<|im_end|>",
            "<|endoftext|>", "<|tool_call_start|>", "<|tool_call_end|>",
        ]
        for token in special_tokens:
            text = text.replace(token, "")

        return text.strip()

    @staticmethod
    def _extract_table_name(sql: str) -> str | None:
        """Extrait le nom de la table principale d'une requête SELECT."""
        import re
        match = re.search(r"FROM\s+(\w+)", sql, re.IGNORECASE)
        return match.group(1) if match else None
