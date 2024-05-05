import numpy
from sentence_transformers import SentenceTransformer


def calculate_similarity(text1: str, text2: str) -> float:
    # Load the RoBERTa model
    embedder = SentenceTransformer('uer/sbert-base-chinese-nli')

    # Tokenize and encode the texts
    encoding1 = embedder.encode(text1)
    encoding2 = embedder.encode(text2)

    # Calculate the cosine similarity between the embeddings
    similarity = numpy.dot(encoding1, encoding2) / \
        (numpy.linalg.norm(encoding1) * numpy.linalg.norm(encoding2))
    return similarity


if __name__ == "__main__":
    text1 = "报告日期"
    text2 = "报告期"
    similarity = calculate_similarity(text1, text2)
    print(similarity)
