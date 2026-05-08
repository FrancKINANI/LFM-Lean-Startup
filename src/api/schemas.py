from pydantic import BaseModel, Field
from typing import List, Optional

class QueryRequest(BaseModel):
    query: str = Field(..., description="La question ou description du projet Lean Startup")
    system_prompt: Optional[str] = Field(None, description="Prompt système personnalisé optionnel")

class QueryResponse(BaseModel):
    answer: str = Field(..., description="La réponse de l'analyste générée par le modèle LFM")
    tool_calls: List[str] = Field(default=[], description="Outils interrogés pendant le raisonnement")

class HealthResponse(BaseModel):
    status: str
    database: Optional[str] = None
    version: Optional[str] = None
    message: Optional[str] = None
