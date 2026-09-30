import os
import json
from werkzeug.utils import secure_filename
from flask import Flask, request, jsonify, render_template
from services.pdf_loader import extract_text
from services.text_splitter import split_text
from services.embedding import create_embeddings
from services.vector_store import (create_vector_store,search_vector_store)
from services.llm import generate_response
from datetime import datetime
from services.reranker import rerank_chunks

app = Flask(__name__)
documents = []

UPLOAD_FOLDER = "uploads"
DOCUMENTS_FILE = "documents.json"
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
app.config["UPLOAD_FOLDER"] = UPLOAD_FOLDER

def retrieve_context(question, chunks, index, k=15):
    question_embedding = create_embeddings([question])
    question_embedding = question_embedding.reshape(1, -1)

    distances, indices = search_vector_store(
        index,
        question_embedding,
        k=k
    )

    candidate_chunks = []
    seen = set()

    for i in indices[0]:
        chunk = chunks[i]
        chunk_text = chunk["text"]

        if chunk_text not in seen:
            candidate_chunks.append(chunk)
            seen.add(chunk_text)

    print("\nFAISS CANDIDATES:")

    for i, chunk in enumerate(candidate_chunks, 1):
        print(f"\nCandidate {i}")
        print(f"Page: {chunk['page']}")
        print(f"Section: {chunk.get('section', 'N/A')}")
        print(chunk["text"][:300])

    ranked_chunks = rerank_chunks(
        question,
        candidate_chunks
    )

    print("\nRERANKED SCORES:")

    for i, (chunk, score) in enumerate(ranked_chunks, 1):
        print(
            f"Rank {i}: {score:.4f} | "
            f"{chunk.get('section', 'N/A')}"
        )

    # Dynamically select relevant chunks
    best_chunks = []

    if ranked_chunks:
        best_chunks.append(ranked_chunks[0])

        for i in range(1, len(ranked_chunks)):
            current_score = ranked_chunks[i][1]
            previous_score = ranked_chunks[i - 1][1]

            score_gap = previous_score - current_score

            if score_gap > 2.5:
                break

            best_chunks.append(ranked_chunks[i])

            if len(best_chunks) >= 7:
                break

    print("\nSELECTED CONTEXT:")

    for i, (chunk, score) in enumerate(best_chunks, 1):
        print(
            f"Selected {i}: "
            f"{score:.4f} | "
            f"{chunk.get('section', 'N/A')}"
        )

    context = "\n\n".join(
        chunk["text"]
        for chunk, score in best_chunks
    )

    return context, [
        chunk for chunk, score in best_chunks
    ]

def process_document(pdf_path):
    pages = extract_text(pdf_path)
    chunks = split_text(pages)
    chunk_texts = [chunk["text"] for chunk in chunks]
    embeddings = create_embeddings(chunk_texts)
    index = create_vector_store(embeddings)
    return pages, chunks, embeddings, index

def save_documents():
    metadata = []
    for document in documents:
        metadata.append({
            "id": document["id"],
            "filename": document["filename"],
            "path": document["path"],
            "file_size": document.get("file_size"),
            "uploaded_at": document.get("uploaded_at"),
            "characters": document.get("characters"),
            "chunks": len(document["chunks"]),
            "embeddings": len(document["embeddings"])
        })
    with open(DOCUMENTS_FILE, "w", encoding="utf-8") as file:
        json.dump(metadata, file, indent=4)

def load_documents():
    global documents
    if not os.path.exists(DOCUMENTS_FILE):
        return
    with open(DOCUMENTS_FILE, "r", encoding="utf-8") as file:
        metadata = json.load(file)
    for item in metadata:
        pdf_path = item["path"]
        if not os.path.exists(pdf_path):
            continue

        pages, chunks, embeddings, index = process_document(pdf_path)

        documents.append({
            "id": item["id"],
            "filename": item["filename"],
            "path": pdf_path,
            "file_size": item.get("file_size"),
            "uploaded_at": item.get("uploaded_at"),
            "characters": item.get("characters"),
            "pages": pages,
            "chunks": chunks,
            "embeddings": embeddings,
            "index": index
        })

    save_documents()
load_documents()

@app.route("/")
def home():
    document_metadata = [
        {
            "id": document["id"],
            "filename": document["filename"],
            "file_size": document.get("file_size"),
            "uploaded_at": document.get("uploaded_at"),
            "characters": document.get("characters"),
            "chunks": len(document["chunks"]),
            "embeddings": len(document["embeddings"])
        }
        for document in documents
    ]

    return render_template("index.html", documents=document_metadata)

@app.route("/upload", methods=["POST"])
def upload_pdf():
    global documents
    file = request.files.get("pdf")
    if file:
        print("filename =", repr(file.filename))

    if file is None or file.filename == "":
        return jsonify({
            "error": "Please select a PDF."
        }), 400

    if not file.filename.lower().endswith(".pdf"):
        return jsonify({
            "error": "Only PDF files are allowed."
        }), 400

    filename = secure_filename(file.filename)

    if not filename:
        return jsonify({
            "error": "Invalid filename."
        }), 400

    os.makedirs(app.config["UPLOAD_FOLDER"], exist_ok=True)
    print("Filename:", repr(filename))

    pdf_path = os.path.join(
        app.config["UPLOAD_FOLDER"],
        filename
    )

    # Check if this document is already uploaded
    existing_document = next(
        (
            document
            for document in documents
            if document["filename"] == filename
        ),
        None
    )

    if existing_document:
        return jsonify({
            "error": "This PDF is already uploaded."
        }), 400
    file.save(pdf_path)

    try:
        # Get actual file size from saved file
        file_size = round(os.path.getsize(pdf_path) / 1024, 2)

        pages, chunks, embeddings, index = process_document(pdf_path)

    except Exception as e:
        # Remove the uploaded file if processing fails
        if os.path.exists(pdf_path):
            os.remove(pdf_path)

        print("PDF processing error:", e)

        return jsonify({
            "error": "Could not process this PDF. Please make sure it is a valid PDF."
        }), 400
    documents.append({
        "id": max(
            [document["id"] for document in documents],
            default=-1
        ) + 1,
        "filename": filename,
        "path": pdf_path,
        "file_size": file_size,
        "uploaded_at": datetime.now().strftime("%I:%M %p"),
        "characters": sum(len(page["text"]) for page in pages),
        "pages": pages,
        "chunks": chunks,
        "embeddings": embeddings,
        "index": index
    })
    save_documents()

    return jsonify({
        "message": "PDF uploaded successfully!",
        "document_id": documents[-1]["id"],
        "filename":filename,
        "file_size": file_size,
        "characters": sum(len(page["text"]) for page in pages),
        "chunks": len(chunks),
        "embeddings": len(embeddings),
        "uploaded_at": datetime.now().strftime("%I:%M %p")
    }), 200

@app.route("/documents/<int:document_id>", methods=["DELETE"])
def delete_document(document_id):
    global documents

    document = next(
        (
            document
            for document in documents
            if document["id"] == document_id
        ),
        None
    )

    if document is None:
        return jsonify({
            "error": "Document not found."
        }), 404

    # Remove the PDF file from the uploads folder
    pdf_path = document["path"]

    if os.path.exists(pdf_path):
        os.remove(pdf_path)

    # Remove document from memory
    documents.remove(document)

    # Update documents.json
    save_documents()

    return jsonify({
        "message": "Document deleted successfully."
    }), 200

@app.route("/chat", methods=["POST"])
def chat():
    global documents

    data = request.get_json()

    question = data.get("question")
    document_id = data.get("document_id")

    if not documents:
        return jsonify({
            "error": "Please upload a PDF first."
        }), 400

    if not question:
        return jsonify({
            "error": "Question is required."
        }), 400

    if document_id is None:
        return jsonify({
            "error": "Please select a document or All Documents."
        }), 400

    # ==================================================
    # ALL DOCUMENTS MODE
    # ==================================================

    if str(document_id) == "all":

        all_candidates = []

        for document in documents:

            # Get FAISS candidates from this document
            question_embedding = create_embeddings([question])
            question_embedding = question_embedding.reshape(1, -1)

            distances, indices = search_vector_store(
                document["index"],
                question_embedding,
                k=15
            )

            seen = set()

            for i in indices[0]:

                chunk = document["chunks"][i]

                if chunk["text"] in seen:
                    continue

                seen.add(chunk["text"])

                chunk_copy = chunk.copy()

                # Add document information
                chunk_copy["filename"] = document["filename"]

                all_candidates.append(chunk_copy)

        if not all_candidates:
            return jsonify({
                "error": "No relevant information was found."
            }), 404

        # ==================================================
        # GLOBAL RERANKING
        # ==================================================

        ranked_chunks = rerank_chunks(
            question,
            all_candidates
        )

        # Take the best 7 chunks
        best_chunks = ranked_chunks[:7]

        # Build context
        context = "\n\n".join(
            f"Document: {chunk['filename']}\n"
            f"Page: {chunk['page']}\n"
            f"Section: {chunk.get('section', '')}\n"
            f"{chunk['text']}"
            for chunk, score in best_chunks
        )

        answer = generate_response(
            question,
            context
        )

        return jsonify({
            "answer": answer,
            "sources": [
                {
                    "filename": chunk["filename"],
                    "page": chunk["page"],
                    "section": chunk.get("section", ""),
                    "project": chunk.get("project", ""),
                    "text": chunk["text"][:1000] + "..."
                }
                for chunk, score in best_chunks
            ]
        }), 200

    # ==================================================
    # SINGLE DOCUMENT MODE
    # ==================================================

    try:
        document_id = int(document_id)

    except (ValueError, TypeError):

        return jsonify({
            "error": "Invalid document ID."
        }), 400

    selected_document = next(
        (
            document
            for document in documents
            if document["id"] == document_id
        ),
        None
    )

    if selected_document is None:

        return jsonify({
            "error": "Selected document was not found."
        }), 404

    # Retrieve from selected document
    context, retrieved_chunks = retrieve_context(
        question,
        selected_document["chunks"],
        selected_document["index"]
    )

    answer = generate_response(
        question,
        context
    )

    return jsonify({
        "answer": answer,
        "sources": [
            {
                "filename": selected_document["filename"],
                "page": chunk["page"],
                "section": chunk.get("section", ""),
                "project": chunk.get("project", ""),
                "text": chunk["text"][:1000] + "..."
            }
            for chunk in retrieved_chunks
        ]
    }), 200
if __name__ == "__main__":
    app.run(debug=True)
