import os

from dotenv import load_dotenv
from groq import Groq

load_dotenv()

client = Groq(
    api_key=os.getenv("GROQ_API_KEY")
)


def generate_response(question: str, context: str) -> str:
    """
    Generates an answer using the retrieved document context.
    """
    system_prompt = """
    You are a document question-answering assistant.
    Rules:
    - Answer ONLY using the provided context.
    - Do NOT use your own knowledge.
    - Do NOT guess or invent information.
    - If the answer is not explicitly present in the context, reply exactly:
    "I couldn't find that information in the uploaded document."
    - Keep answers short and direct.
    """
    user_prompt = f"""
    Context:
{context}

Question:
{question}
"""

    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        temperature=0,
        top_p=1,
        max_tokens=200,
        messages=[
            {
                "role": "system",
                "content": (
                    "Answer ONLY using the provided context. "
                    "Never use outside knowledge. "
                    "If the answer isn't present, reply exactly: "
                    "'I couldn't find that information in the uploaded document.'"
                )
            },
            {
                "role": "user",
                "content": f"Context:\n{context}\n\nQuestion:\n{question}"
            }
        ]
    )

    return response.choices[0].message.content.strip()