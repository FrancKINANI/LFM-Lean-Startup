import torch
from transformers import AutoModelForCausalLM, AutoTokenizer
from peft import PeftModel

class LFMAnalyst:
    """
    Classe pour gérer l'inférence du modèle LiquidAI LFM2.5.
    Supporte le modèle de base et l'application d'un adaptateur LoRA.
    """
    def __init__(self, model_id="LiquidAI/LFM2.5-350M-Base", adapter_path=None):
        self.model_id = model_id
        print(f"Chargement du modèle : {model_id}")
        
        self.tokenizer = AutoTokenizer.from_pretrained(model_id, trust_remote_code=True)
        
        # Chargement du modèle avec optimisation automatique du device
        self.model = AutoModelForCausalLM.from_pretrained(
            model_id,
            torch_dtype=torch.bfloat16 if torch.cuda.is_available() else torch.float32,
            device_map="auto",
            trust_remote_code=True
        )
        
        # Application de l'adaptateur si fourni (Fine-tuning)
        if adapter_path:
            print(f"Application de l'adaptateur LoRA : {adapter_path}")
            self.model = PeftModel.from_pretrained(self.model, adapter_path)
            
    def generate(self, messages, max_new_tokens=512, temperature=0.7):
        """
        Génère une réponse à partir d'une liste de messages au format ChatML.
        """
        # Application du template de chat spécifique à Liquid LFM
        prompt = self.tokenizer.apply_chat_template(
            messages,
            tokenize=False,
            add_generation_prompt=True
        )
        
        inputs = self.tokenizer(prompt, return_tensors="pt").to(self.model.device)
        
        with torch.no_grad():
            outputs = self.model.generate(
                **inputs,
                max_new_tokens=max_new_tokens,
                temperature=temperature,
                do_sample=True if temperature > 0 else False,
                pad_token_id=self.tokenizer.eos_token_id,
                repetition_penalty=1.1
            )
            
        # Décodage uniquement de la nouvelle partie générée
        input_length = inputs["input_ids"].shape[1]
        response = self.tokenizer.decode(outputs[0][input_length:], skip_special_tokens=True)
        
        return response.strip()

if __name__ == "__main__":
    # Test rapide (si le modèle est accessible localement ou téléchargeable)
    # analyst = LFMAnalyst()
    # print(analyst.generate([{"role": "user", "content": "Hello"}]))
    pass
