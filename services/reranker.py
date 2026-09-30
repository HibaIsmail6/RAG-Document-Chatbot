from sentence_transformers import CrossEncoder

model = CrossEncoder("cross-encoder/ms-marco-MiniLM-L-6-v2")


def rerank_chunks(question, chunks):
    pairs = [
        (question, chunk["text"])
        for chunk in chunks
    ]

    scores = model.predict(pairs)

    ranked = []

    for chunk, score in zip(chunks, scores):
        ranked.append(
            (chunk, float(score))
        )

    ranked.sort(
        key=lambda x: x[1],
        reverse=True
    )

    print("\nQUESTION:", question)
    print("\nRERANKING RESULTS:")

    for i, (chunk, score) in enumerate(ranked, 1):
        print(f"\nRank {i} | Score: {score:.4f}")
        print(f"Page: {chunk['page']}")
        print(f"Section: {chunk.get('section', 'N/A')}")
        print(chunk["text"][:300])

    return ranked