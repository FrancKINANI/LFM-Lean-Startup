import os
import json
from pathlib import Path

def test_dataset_generation_files_exist():
    root = Path(__file__).parent.parent
    data_source = root / "data" / "source" / "full_dataset.jsonl"
    assert data_source.exists(), "Le fichier full_dataset.jsonl devrait exister suite à DVC repro"
    
def test_dataset_format_is_chatml():
    root = Path(__file__).parent.parent
    data_source = root / "data" / "source" / "full_dataset.jsonl"
    
    if data_source.exists():
        with open(data_source, 'r', encoding='utf-8') as f:
            first_line = f.readline()
            if first_line:
                data = json.loads(first_line)
                assert "messages" in data, "Le dataset doit utiliser la clé 'messages' (Format ChatML)"
                assert len(data["messages"]) > 0, "La liste de messages ne doit pas être vide"
                assert "role" in data["messages"][0], "Les messages doivent avoir un attribut 'role'"
                assert "content" in data["messages"][0], "Les messages doivent avoir un attribut 'content'"
