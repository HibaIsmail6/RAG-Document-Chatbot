import os
from flask import Flask, request, jsonify, render_template

from services.pdf_loader import extract_text
from services.text_splitter import split_text
from services.embedding import create_embeddings
from services.vector_store import (
    create_vector_store,
    search_vector_store
)
from services.llm import generate_response
from datetime import datetime

app = Flask(__name__)
chunks = None
index = None

def retrieve_context(question, chunks, index, k=2):
    """
    Retrieve the most relevant chunks for a question.
    """

    question_embedding = create_embeddings(question)
    question_embedding = question_embedding.reshape(1, -1)

    _, indices = search_vector_store(
        index,
        question_embedding,
        k=k
    )

    retrieved_chunks = [chunks[i] for i in indices[0]]

    context = "\n\n".join(retrieved_chunks)

    return context, retrieved_chunks

def process_document(pdf_path):
    """
    Extract text, split into chunks, create embeddings,
    and build the FAISS index.
    """

    text = extract_text(pdf_path)

    chunks = split_text(text)

    embeddings = create_embeddings(chunks)

    index = create_vector_store(embeddings)

    return text, chunks, embeddings, index

@app.route("/")
def home():
    return render_template("index.html")

@app.route("/upload", methods=["POST"])
def upload_pdf():
    global chunks, index
    file = request.files.get("pdf")
    if file:
        print("filename =", repr(file.filename))

    if file is None or file.filename == "":
        return jsonify({
            "error": "Please select a PDF."
        }), 400
    upload_folder = "uploads"

    os.makedirs(upload_folder, exist_ok=True)

    print("Filename:", repr(file.filename))

    pdf_path = os.path.join(upload_folder, file.filename)

    file.save(pdf_path)

    # Get actual file size from saved file
    file_size = round(os.path.getsize(pdf_path) / 1024, 2)

    text, chunks, embeddings, index = process_document(pdf_path)

    return jsonify({
        "message": "PDF uploaded successfully!",
        "filename": file.filename,
        "file_size": file_size,
        "characters": len(text),
        "chunks": len(chunks),
        "embeddings": len(embeddings),
        "uploaded_at": datetime.now().strftime("%I:%M %p")
    }), 200

@app.route("/chat", methods=["POST"])
def chat():
    global chunks, index

    data = request.get_json()

    question = data.get("question")
    if index is None or chunks is None:
        return jsonify({
            "error": "Please upload a PDF first."
        }), 400

    if not question:
        return jsonify({
            "error": "Question is required."
        }), 400

    context, retrieved_chunks = retrieve_context(
        question,
        chunks,
        index
    )
    answer = generate_response(question, context)
    return jsonify({
        "answer": answer,
        "sources": [chunk[:1000] + "..." for chunk in retrieved_chunks]
    }), 200


if __name__ == "__main__":
    app.run(debug=True)
