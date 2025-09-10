from sentence_transformers import SentenceTransformer, util

embed_model = SentenceTransformer("all-MiniLM-L6-v2")

INTENT_EXAMPLES = {
    "greeting": ["hi", "hello", "hey", "yo", "sup", "sup bro", "hey there", "yo dude"],
    "rude": ["fuck", "fuck you", "shit", "stupid", "idiot"],
    "game_query": ["recommend me a game", "suggest game like", "tell me about this game", "games similar to"],
    "other": ["milk", "weather", "news", "random stuff"]
}

intent_texts = []
intent_labels = []
for label, examples in INTENT_EXAMPLES.items():
    intent_texts.extend(examples)
    intent_labels.extend([label] * len(examples))

intent_embeddings = embed_model.encode(intent_texts, normalize_embeddings=True)

def route_intent(user_input: str, threshold: float = 0.6) -> str:
    user_embedding = embed_model.encode(user_input, normalize_embeddings=True)
    scores = util.cos_sim(user_embedding, intent_embeddings)[0]
    best_idx = scores.argmax().item()
    best_label = intent_labels[best_idx]
    best_score = scores[best_idx].item()
    if best_score < threshold:
        return "other"
    return best_label
