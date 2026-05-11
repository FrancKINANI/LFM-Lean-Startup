#!/bin/bash

# Script d'installation automatique pour Google Colab
# À exécuter dans une cellule Colab via : !bash scripts/setup_colab.sh

echo "🚀 Début de l'installation de l'environnement Colab..."

# 1. Mise à jour de pip
pip install --upgrade pip

# 2. Installation des dépendances GPU + suivi distant
echo "📦 Installation des bibliothèques de fine-tuning distant..."
pip install -r scripts/remote_training_requirements.txt

# 4. Vérification de l'accès GPU
echo "🖥️ Vérification du GPU..."
python -c "import torch; print('✅ GPU disponible :' if torch.cuda.is_available() else '❌ GPU NON TROUVÉ'); print(torch.cuda.get_device_name(0) if torch.cuda.is_available() else '')"

echo "🎉 Installation terminée ! Vous pouvez maintenant lancer l'entraînement."
