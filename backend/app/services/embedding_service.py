from sentence_transformers import SentenceTransformer


MODEL_NAME = "BAAI/bge-m3"

_model = None


def get_embedding_model() -> SentenceTransformer:
    global _model

    if _model is None:
        _model = SentenceTransformer(MODEL_NAME)

    return _model


def generate_embeddings(
    texts: list[str],
) -> list[list[float]]:
    if not texts:
        return []

    model = get_embedding_model()

    embeddings = model.encode(
        texts,
        normalize_embeddings=True,
        batch_size=8,
        show_progress_bar=False,
    )

    return embeddings.tolist()
