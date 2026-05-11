"""
src/training/config.py
======================
Configuration centralisée de l'entraînement.

Toutes les décisions d'hyperparamètres sont ici — jamais dans le code
du trainer. Cela garantit que chaque run MLflow peut être reproduit
exactement en relisant sa configuration.

Deux niveaux de configuration :
    - LoraConfig    : paramètres d'adaptation LoRA (architecture)
    - TrainingConfig: paramètres d'entraînement (optimisation, données)

Les valeurs par défaut sont calibrées pour LFM2.5-350M sur un GPU
de 16-24 Go (A100 40G ou RTX 3090/4090). Ajuster batch_size et
gradient_accumulation_steps selon la mémoire disponible.
"""

import os
from dataclasses import dataclass, field
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[2]


# =============================================================================
# CONFIGURATION LORA
# =============================================================================

@dataclass
class LoraConfig:
    """
    Paramètres LoRA (Low-Rank Adaptation).

    LoRA n'entraîne pas tous les poids du modèle — il ajoute de petites
    matrices d'adaptation (rang r) aux couches d'attention. Cela permet
    de fine-tuner LFM2.5-350M avec seulement ~1-5% des paramètres totaux.

    Paramètres clés :
        r       : rang des matrices d'adaptation. Plus élevé = plus de
                  capacité mais plus de paramètres entraînés.
                  Pour 350M params : r=16 est un bon équilibre.

        lora_alpha : facteur de scaling. Convention : lora_alpha = 2 × r.
                     Contrôle l'amplitude de l'adaptation.

        target_modules : couches où LoRA est appliqué. Pour LFM2.5,
                         cibler les projections d'attention Q, K, V, O
                         et les projections FFN.
    """
    r:                  int   = 16
    lora_alpha:         int   = 32       # = 2 × r (convention standard)
    lora_dropout:       float = 0.05
    bias:               str   = "none"   # "none" | "all" | "lora_only"
    task_type:          str   = "CAUSAL_LM"

    # Modules ciblés dans LFM2.5-350M
    # Note : LFM2.5 utilise une architecture hybride (Liquid + Attention).
    # Ces noms sont à vérifier avec model.named_modules() au premier run.
    target_modules: list[str] = field(default_factory=lambda: [
        "q_proj",    # projection Query
        "k_proj",    # projection Key
        "v_proj",    # projection Value
        "o_proj",    # projection Output attention
        "gate_proj", # FFN gate
        "up_proj",   # FFN up
        "down_proj", # FFN down
    ])

    # Modules exclus du fine-tuning (couche de sortie — ne pas modifier)
    modules_to_save: list[str] = field(default_factory=lambda: [
        "lm_head",
        "embed_tokens",
    ])

    @property
    def trainable_params_ratio(self) -> str:
        """Estimation du ratio de paramètres entraînés (approximatif)."""
        # Pour r=16 sur 350M params ≈ 1-3% selon les modules ciblés
        estimated = self.r * len(self.target_modules) * 2 * 1024
        total = 350_000_000
        return f"~{estimated/total:.1%}"


# =============================================================================
# CONFIGURATION D'ENTRAÎNEMENT
# =============================================================================

@dataclass
class TrainingConfig:
    """
    Paramètres de l'entraînement SFT complet.

    Organisation en sections :
        - Chemins (modèle, données, sorties)
        - Hyperparamètres d'optimisation
        - Paramètres de batch et séquence
        - Évaluation et sauvegarde
        - MLflow
    """

    # ------------------------------------------------------------------
    # CHEMINS
    # ------------------------------------------------------------------
    base_model_id:   str = "LiquidAI/LFM2.5-350M-Base"
    output_dir:      str = str(PROJECT_ROOT / "models" / "lfm25-350m-lean")
    logging_dir:     str = str(PROJECT_ROOT / "models" / "logs")

    # Données
    train_file:      str = str(PROJECT_ROOT / "data" / "liquid" / "train_liquid.jsonl")
    val_file:        str = str(PROJECT_ROOT / "data" / "liquid" / "val_liquid.jsonl")
    dataset_field:   str = "text"   # champ utilisé par SFTTrainer

    # ------------------------------------------------------------------
    # HYPERPARAMÈTRES D'OPTIMISATION
    # Ces paramètres sont loggués dans MLflow à chaque run
    # ------------------------------------------------------------------
    num_train_epochs:       int   = 3
    learning_rate:          float = 2e-4      # standard LoRA
    lr_scheduler_type:      str   = "cosine"  # décroissance cosinus
    warmup_ratio:           float = 0.05      # 5% des steps en warmup
    weight_decay:           float = 0.01
    max_grad_norm:          float = 1.0       # gradient clipping

    optimizer:              str   = "adamw_torch_fused"  # plus rapide sur GPU

    # ------------------------------------------------------------------
    # BATCH ET SÉQUENCE
    # Ajuster selon la VRAM disponible
    # 16Go VRAM  : per_device=2, grad_accum=8  → batch effectif=16
    # 24Go VRAM  : per_device=4, grad_accum=4  → batch effectif=16
    # 40Go VRAM  : per_device=8, grad_accum=2  → batch effectif=16
    # ------------------------------------------------------------------
    per_device_train_batch_size: int = 2
    per_device_eval_batch_size:  int = 4
    gradient_accumulation_steps: int = 8       # batch effectif = 2×8 = 16
    max_seq_length:              int = 4096    # contexte LFM2.5

    # ------------------------------------------------------------------
    # OPTIMISATIONS MÉMOIRE
    # ------------------------------------------------------------------
    bf16:                      bool = True    # bfloat16 (A100/H100/RTX 4090)
    fp16:                      bool = False   # float16 (RTX 3090, Tesla V100)
    gradient_checkpointing:    bool = True    # économise ~30% de VRAM
    dataloader_num_workers:    int  = 4

    # ------------------------------------------------------------------
    # ÉVALUATION ET SAUVEGARDE
    # ------------------------------------------------------------------
    eval_strategy:          str = "steps"
    eval_steps:             int = 50      # évaluer toutes les 50 steps
    save_strategy:          str = "steps"
    save_steps:             int = 50
    save_total_limit:       int = 3       # garder les 3 meilleurs checkpoints
    load_best_model_at_end: bool = True
    metric_for_best_model:  str = "eval_loss"
    greater_is_better:      bool = False

    logging_steps:          int = 10      # logger toutes les 10 steps

    # ------------------------------------------------------------------
    # MLFLOW
    # ------------------------------------------------------------------
    mlflow_experiment_name:  str = "LFM-Lean-Startup-SFT"
    mlflow_tracking_uri:     str = os.getenv("MLFLOW_TRACKING_URI", "http://localhost:5000")
    mlflow_model_name:       str = "lfm25-lean-startup"

    # Stades du Model Registry MLflow
    # None → Staging → Production → Archived
    auto_register_model:     bool = True
    register_to_stage:       str  = "Staging"

    # ------------------------------------------------------------------
    # REPRODUCTIBILITÉ
    # ------------------------------------------------------------------
    seed: int = 42

    def to_hf_training_args(self) -> dict:
        """
        Convertit en dict compatible avec HuggingFace TrainingArguments.
        Utilisé dans trainer.py pour instancier TrainingArguments.
        """
        return {
            "output_dir":                    self.output_dir,
            "logging_dir":                   self.logging_dir,
            "num_train_epochs":              self.num_train_epochs,
            "learning_rate":                 self.learning_rate,
            "lr_scheduler_type":             self.lr_scheduler_type,
            "warmup_ratio":                  self.warmup_ratio,
            "weight_decay":                  self.weight_decay,
            "max_grad_norm":                 self.max_grad_norm,
            "optim":                         self.optimizer,
            "per_device_train_batch_size":   self.per_device_train_batch_size,
            "per_device_eval_batch_size":    self.per_device_eval_batch_size,
            "gradient_accumulation_steps":   self.gradient_accumulation_steps,
            "bf16":                          self.bf16,
            "fp16":                          self.fp16,
            "gradient_checkpointing":        self.gradient_checkpointing,
            "dataloader_num_workers":        self.dataloader_num_workers,
            "eval_strategy":                 self.eval_strategy,
            "eval_steps":                    self.eval_steps,
            "save_strategy":                 self.save_strategy,
            "save_steps":                    self.save_steps,
            "save_total_limit":              self.save_total_limit,
            "load_best_model_at_end":        self.load_best_model_at_end,
            "metric_for_best_model":         self.metric_for_best_model,
            "greater_is_better":             self.greater_is_better,
            "logging_steps":                 self.logging_steps,
            "seed":                          self.seed,
            "report_to":                     "none",  # MLflow géré manuellement
            "remove_unused_columns":         False,
        }

    def log_params_dict(self) -> dict:
        """
        Retourne tous les paramètres à logger dans MLflow.
        Séparé de to_hf_training_args() pour inclure les params LoRA.
        """
        return {
            # Modèle
            "base_model":               self.base_model_id,
            # Optimisation
            "num_epochs":               self.num_train_epochs,
            "learning_rate":            self.learning_rate,
            "lr_scheduler":             self.lr_scheduler_type,
            "warmup_ratio":             self.warmup_ratio,
            "weight_decay":             self.weight_decay,
            "optimizer":                self.optimizer,
            # Batch
            "batch_size_per_device":    self.per_device_train_batch_size,
            "gradient_accumulation":    self.gradient_accumulation_steps,
            "effective_batch_size":     self.per_device_train_batch_size * self.gradient_accumulation_steps,
            "max_seq_length":           self.max_seq_length,
            # Précision
            "bf16":                     self.bf16,
            "gradient_checkpointing":   self.gradient_checkpointing,
            # Seed
            "seed":                     self.seed,
        }
