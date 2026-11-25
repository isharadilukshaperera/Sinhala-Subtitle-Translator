import torch
from transformers import AutoTokenizer, AutoModelForCausalLM, BitsAndBytesConfig
from anti_gravity.translator_engine import TranslationEngine

engine = TranslationEngine(device='cuda')
engine.load_model()

# Test 1: plain without context or glossary
engine.enable_glossary = False
engine.context_window_size = 0
out1 = engine.translate_batch(['Good morning! How are you doing today?'])
print("1. Plain batch output:", out1)

# Test 2: with glossary
engine.enable_glossary = True
out2 = engine.translate_batch(['I am preparing the report for the project.'])
print("2. Glossary batch output:", out2)

# Test 3: with written form in input
out3 = engine.translate_batch(["Let's meet at the train station at 5 PM."])
print("3. Train station batch output:", out3)

