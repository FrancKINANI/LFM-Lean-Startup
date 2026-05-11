"""
tests/test_data_pipeline.py
============================
Tests unitaires pour src/data/build_lean_datasets.py
et src/data/report_dataset_metrics.py.

Stratégie de test :
    - Tests isolés : aucune dépendance à PostgreSQL ou au modèle
    - Tests de structure : valider le format des exemples générés
    - Tests de cohérence : valider les splits et les métadonnées
    - Tests de régression : s'assurer que les générateurs produisent
      toujours le bon nombre minimum d'exemples

Lancer :
    pytest tests/test_data_pipeline.py -v
    pytest tests/test_data_pipeline.py -v --tb=short
"""

import json
import sys
import tempfile
from pathlib import Path

import pytest

# Ajout du projet au PYTHONPATH pour les imports relatifs
PROJECT_ROOT = Path(__file__).resolve().parent.parent
sys.path.insert(0, str(PROJECT_ROOT))


# =============================================================================
# FIXTURES
# =============================================================================

@pytest.fixture
def sample_examples():
    """Génère les exemples réels depuis les générateurs du dataset."""
    from src.data.build_lean_datasets import generate_all_examples
    return generate_all_examples()


@pytest.fixture
def example_dict(sample_examples):
    """Retourne le premier exemple sous forme de dict sérialisé."""
    return sample_examples[0].to_dict()


@pytest.fixture
def temp_jsonl(sample_examples):
    """Crée un fichier JSONL temporaire avec tous les exemples."""
    with tempfile.NamedTemporaryFile(
        mode="w", suffix=".jsonl", delete=False, encoding="utf-8"
    ) as f:
        for ex in sample_examples:
            f.write(json.dumps(ex.to_dict(), ensure_ascii=False) + "\n")
        return Path(f.name)


# =============================================================================
# TESTS — GÉNÉRATION DES EXEMPLES
# =============================================================================

class TestExampleGeneration:
    """Tests sur la génération brute des exemples."""

    def test_generates_examples(self, sample_examples):
        """Le générateur produit au moins un exemple."""
        assert len(sample_examples) > 0, "Aucun exemple généré."

    def test_minimum_example_count(self, sample_examples):
        """Le dataset contient au moins 5 exemples (seuil de développement)."""
        assert len(sample_examples) >= 5, (
            f"Trop peu d'exemples : {len(sample_examples)}. "
            "Enrichir les générateurs dans build_lean_datasets.py."
        )

    def test_all_four_categories_present(self, sample_examples):
        """Les quatre catégories attendues sont représentées."""
        categories = {ex.metadata.get("category") for ex in sample_examples}
        expected = {
            "diagnostic_complet",
            "identification_des_dangers",
            "evaluation_investissement",
            "simplification_concept",
        }
        missing = expected - categories
        assert not missing, (
            f"Catégories manquantes dans le dataset : {missing}. "
            "Vérifier que chaque générateur produit au moins un exemple."
        )

    def test_both_tool_use_and_no_tool_use(self, sample_examples):
        """Le dataset contient des exemples avec ET sans tool use."""
        has_tool = any(ex.metadata.get("has_tool_use") for ex in sample_examples)
        no_tool  = any(not ex.metadata.get("has_tool_use") for ex in sample_examples)
        assert has_tool, "Aucun exemple avec tool use dans le dataset."
        assert no_tool,  "Aucun exemple sans tool use dans le dataset."

    def test_tool_use_ratio_in_bounds(self, sample_examples):
        """Le ratio tool use est dans les limites acceptables (20%-85%)."""
        total = len(sample_examples)
        tool_count = sum(1 for ex in sample_examples if ex.metadata.get("has_tool_use"))
        ratio = tool_count / total
        assert 0.20 <= ratio <= 0.85, (
            f"Ratio tool use hors limites : {ratio:.0%}. "
            "Attendu entre 20% et 85%."
        )


# =============================================================================
# TESTS — STRUCTURE DES EXEMPLES
# =============================================================================

class TestExampleStructure:
    """Tests sur la structure interne de chaque exemple."""

    def test_example_has_messages_field(self, example_dict):
        assert "messages" in example_dict, "Champ 'messages' manquant."

    def test_example_has_metadata_field(self, example_dict):
        assert "metadata" in example_dict, "Champ 'metadata' manquant."

    def test_messages_is_non_empty_list(self, example_dict):
        msgs = example_dict["messages"]
        assert isinstance(msgs, list) and len(msgs) > 0, (
            "Le champ 'messages' doit être une liste non vide."
        )

    def test_first_message_is_system(self, example_dict):
        """Le premier message doit toujours être le system prompt."""
        first = example_dict["messages"][0]
        assert first["role"] == "system", (
            f"Le premier message doit avoir role='system', reçu : '{first['role']}'."
        )

    def test_system_message_contains_role_definition(self, example_dict):
        """Le system prompt doit définir le rôle de l'analyste."""
        system_content = example_dict["messages"][0]["content"]
        assert "analyste" in system_content.lower() or "lean startup" in system_content.lower(), (
            "Le system prompt doit définir le rôle d'analyste Lean Startup."
        )

    def test_all_messages_have_role_and_content(self, example_dict):
        """Chaque message doit avoir 'role' et 'content'."""
        for i, msg in enumerate(example_dict["messages"]):
            assert "role" in msg, f"Message {i} : champ 'role' manquant."
            assert "content" in msg, f"Message {i} : champ 'content' manquant."
            assert isinstance(msg["content"], str) and len(msg["content"]) > 0, (
                f"Message {i} : 'content' vide ou non-string."
            )

    def test_valid_roles_only(self, example_dict):
        """Les rôles sont dans l'ensemble valide LFM2.5."""
        valid_roles = {"system", "user", "assistant", "tool"}
        for msg in example_dict["messages"]:
            assert msg["role"] in valid_roles, (
                f"Rôle invalide : '{msg['role']}'. "
                f"Rôles valides : {valid_roles}"
            )

    def test_user_message_present(self, example_dict):
        """Chaque exemple doit avoir au moins un message utilisateur."""
        roles = [m["role"] for m in example_dict["messages"]]
        assert "user" in roles, "Aucun message 'user' dans l'exemple."

    def test_final_message_is_assistant(self, example_dict):
        """Le dernier message doit toujours être une réponse de l'assistant."""
        last_role = example_dict["messages"][-1]["role"]
        assert last_role == "assistant", (
            f"Le dernier message doit être 'assistant', reçu : '{last_role}'."
        )

    def test_tool_use_example_has_tool_message(self, sample_examples):
        """Un exemple marqué has_tool_use=True contient un message 'tool'."""
        tool_examples = [ex for ex in sample_examples if ex.metadata.get("has_tool_use")]
        assert tool_examples, "Aucun exemple avec tool use pour tester."

        for ex in tool_examples:
            roles = [m.role for m in ex.messages]
            assert "tool" in roles, (
                f"Exemple has_tool_use=True sans message 'tool' : "
                f"catégorie={ex.metadata.get('category')}"
            )

    def test_tool_call_format_in_assistant_message(self, sample_examples):
        """Les tool calls respectent le format LFM2.5 avec les tokens spéciaux."""
        from src.inference.tool_executor import TOOL_CALL_START, TOOL_CALL_END

        tool_examples = [ex for ex in sample_examples if ex.metadata.get("has_tool_use")]

        for ex in tool_examples:
            assistant_msgs = [m for m in ex.messages if m.role == "assistant"]
            has_tool_call_in_assistant = any(
                TOOL_CALL_START in m.content for m in assistant_msgs
            )
            # Au moins un message assistant doit contenir un tool call
            assert has_tool_call_in_assistant, (
                f"Exemple has_tool_use=True : aucun token '{TOOL_CALL_START}' "
                f"trouvé dans les messages assistant."
            )


# =============================================================================
# TESTS — MÉTADONNÉES
# =============================================================================

class TestMetadata:
    """Tests sur la cohérence des métadonnées."""

    def test_required_metadata_fields(self, sample_examples):
        """Chaque exemple doit avoir les champs de métadonnées requis."""
        required = ["category", "has_tool_use", "Label", "Severity", "Difficulty", "lean_principle"]
        for i, ex in enumerate(sample_examples):
            for field in required:
                assert field in ex.metadata, (
                    f"Exemple {i} : champ metadata '{field}' manquant."
                )

    def test_has_tool_use_is_boolean(self, sample_examples):
        """has_tool_use doit être un booléen."""
        for ex in sample_examples:
            val = ex.metadata.get("has_tool_use")
            assert isinstance(val, bool), (
                f"has_tool_use doit être bool, reçu : {type(val).__name__}"
            )

    def test_label_severity_difficulty_values_are_valid(self, sample_examples):
        """Les champs de supervision gardent un vocabulaire contrôlé."""
        valid_labels = {"Green Flag", "Red Flag", "Mixed"}
        valid_severities = {"Mineur", "Majeur", "Fatal", "Non applicable"}
        valid_difficulties = {"Explicite", "Implicite", "Ambigu", "Mixte"}

        for ex in sample_examples:
            assert ex.metadata.get("Label") in valid_labels
            assert ex.metadata.get("Severity") in valid_severities
            assert ex.metadata.get("Difficulty") in valid_difficulties

    def test_response_contains_expected_label(self, sample_examples):
        """La réponse finale doit répéter le label attendu par les métadonnées."""
        for ex in sample_examples[:200]:
            final_answer = ex.messages[-1].content
            expected = ex.metadata.get("Label")
            assert f"Label: {expected}" in final_answer

    def test_category_values_are_valid(self, sample_examples):
        """Les catégories sont dans l'ensemble défini."""
        valid_categories = {
            "diagnostic_complet",
            "identification_des_dangers",
            "evaluation_investissement",
            "simplification_concept",
        }
        for ex in sample_examples:
            cat = ex.metadata.get("category")
            assert cat in valid_categories, (
                f"Catégorie invalide : '{cat}'. Valides : {valid_categories}"
            )


# =============================================================================
# TESTS — SPLIT DU DATASET
# =============================================================================

class TestDatasetSplit:
    """Tests sur la logique de split train/val/test."""

    def test_split_covers_all_examples(self, sample_examples):
        """La somme des splits = total des exemples (pas de perte)."""
        from src.data.build_lean_datasets import split_dataset
        train, val, test = split_dataset(sample_examples)
        assert len(train) + len(val) + len(test) == len(sample_examples), (
            "Des exemples ont été perdus lors du split."
        )

    def test_splits_are_disjoint(self, sample_examples):
        """Train, val et test ne partagent aucun exemple."""
        from src.data.build_lean_datasets import split_dataset

        train, val, test = split_dataset(sample_examples)

        # Comparer par contenu JSON pour l'identité
        train_set = {json.dumps(ex.to_dict(), sort_keys=True) for ex in train}
        val_set   = {json.dumps(ex.to_dict(), sort_keys=True) for ex in val}
        test_set  = {json.dumps(ex.to_dict(), sort_keys=True) for ex in test}

        assert not (train_set & val_set),  "Des exemples sont dans train ET val."
        assert not (train_set & test_set), "Des exemples sont dans train ET test."
        assert not (val_set & test_set),   "Des exemples sont dans val ET test."

    def test_split_is_reproducible(self, sample_examples):
        """Deux splits avec le même seed produisent les mêmes résultats."""
        from src.data.build_lean_datasets import split_dataset

        train1, val1, test1 = split_dataset(sample_examples, seed=42)
        train2, val2, test2 = split_dataset(sample_examples, seed=42)

        assert len(train1) == len(train2), "Split non reproductible (train)."
        assert len(val1)   == len(val2),   "Split non reproductible (val)."
        assert len(test1)  == len(test2),  "Split non reproductible (test)."


# =============================================================================
# TESTS — FORMAT LIQUID (TRL)
# =============================================================================

class TestLiquidFormat:
    """Tests sur le format de sortie pour TRL SFTTrainer."""

    def test_liquid_format_has_text_field(self, sample_examples):
        """Le format Liquid doit contenir un champ 'text'."""
        for ex in sample_examples:
            liquid = ex.to_liquid_format()
            assert "text" in liquid, "Format Liquid : champ 'text' manquant."

    def test_liquid_text_contains_chat_tokens(self, sample_examples):
        """Le texte Liquid contient les tokens ChatML de LFM2.5."""
        for ex in sample_examples:
            text = ex.to_liquid_format()["text"]
            assert "<|im_start|>" in text, (
                "Format Liquid : token '<|im_start|>' manquant."
            )

    def test_liquid_format_is_serializable(self, sample_examples):
        """Le format Liquid est sérialisable en JSON (requis pour JSONL)."""
        for ex in sample_examples:
            liquid = ex.to_liquid_format()
            try:
                json.dumps(liquid, ensure_ascii=False)
            except (TypeError, ValueError) as e:
                pytest.fail(f"Format Liquid non sérialisable en JSON : {e}")


# =============================================================================
# TESTS — RAPPORT DE MÉTRIQUES
# =============================================================================

class TestMetricsReport:
    """Tests sur report_dataset_metrics.py."""

    def test_compute_metrics_basic(self, sample_examples):
        """compute_metrics retourne les champs attendus."""
        from src.data.report_dataset_metrics import compute_metrics

        examples_dicts = [ex.to_dict() for ex in sample_examples]
        metrics = compute_metrics(examples_dicts)

        required_keys = [
            "total", "categories", "tool_use_count",
            "tool_use_ratio", "warnings",
        ]
        for key in required_keys:
            assert key in metrics, f"Champ '{key}' manquant dans compute_metrics."

    def test_compute_metrics_total_matches(self, sample_examples):
        """Le total des métriques correspond au nombre d'exemples."""
        from src.data.report_dataset_metrics import compute_metrics
        examples_dicts = [ex.to_dict() for ex in sample_examples]
        metrics = compute_metrics(examples_dicts)
        assert metrics["total"] == len(sample_examples)

    def test_render_report_produces_markdown(self, sample_examples, temp_jsonl):
        """render_report produit un fichier Markdown non vide."""
        from src.data.report_dataset_metrics import compute_metrics, render_report, load_dataset

        examples = load_dataset(temp_jsonl)
        metrics  = compute_metrics(examples)
        report   = render_report(metrics, temp_jsonl)

        assert isinstance(report, str) and len(report) > 100, (
            "Le rapport Markdown est vide ou trop court."
        )
        assert "# Dataset Metrics Report" in report, (
            "Le rapport ne contient pas le titre attendu."
        )
        assert "## Vue d'ensemble" in report, (
            "Le rapport ne contient pas la section Vue d'ensemble."
        )

    def test_load_dataset_from_jsonl(self, temp_jsonl, sample_examples):
        """load_dataset lit correctement un fichier JSONL."""
        from src.data.report_dataset_metrics import load_dataset
        loaded = load_dataset(temp_jsonl)
        assert len(loaded) == len(sample_examples), (
            f"load_dataset a chargé {len(loaded)} exemples, "
            f"attendu {len(sample_examples)}."
        )

    def test_load_dataset_missing_file_raises(self):
        """load_dataset lève FileNotFoundError si le fichier n'existe pas."""
        from src.data.report_dataset_metrics import load_dataset
        with pytest.raises(FileNotFoundError):
            load_dataset(Path("/tmp/fichier_qui_nexiste_pas.jsonl"))
