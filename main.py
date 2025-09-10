from config import chain
from retriever import load_retriever

retriever = load_retriever()
greeting_count = 0

import re

def classify_input(question: str, retriever):
    global greeting_count
    q = question.lower().strip()

    rude_words = ["fuck", "shit", "stupid", "idiot"]
    for r in rude_words:
        if re.search(rf"\b{r}\b", q):
            return "rude"

    greetings = ["hi", "hello", "hey", "yo", "sup", "sup bro"]
    for g in greetings:
        if re.search(rf"\b{g}\b", q):
            greeting_count += 1
            if greeting_count == 1:
                return "greeting"
            return "spam_greeting"

    docs = retriever.invoke(question)
    if docs:
        return "normal"

    return "normal"

def run_chatbot():
    global greeting_count
    print("=== Game Recommendation Chatbot ===")
    while True:
        question = input("\nEnter your question (or 'exit' to quit): ").strip()
        if question.lower() == "exit":
            greeting_count = 0
            break

        category = classify_input(question, retriever)

        if category == "greeting":
            print("Hello! How can I assist you with games today?")
            continue
        elif category == "spam_greeting":
            print("Straight to the point, please.")
            continue
        elif category == "rude":
            print("Let's keep it respectful, please.")
            continue

        docs = retriever.invoke(question)
        if not docs:
            print("Sorry, I can only answer questions about games.")
            continue

        game_list = "\n".join([
            f"- {d.page_content} (Genre: {d.metadata['genre']}, Platform: {d.metadata['platform']}, Score: {d.metadata['score']})"
            for d in docs
        ])

        result = chain.invoke({
            "chat_history": "",
            "game_list": game_list,
            "question": question
        })

        print("\n" + result)

if __name__ == "__main__":
    run_chatbot()
