from langchain_ollama.llms import OllamaLLM
from prompts import GAME_PROMPT

model = OllamaLLM(model="llama3.2")

# Create chain
chain = GAME_PROMPT | model
