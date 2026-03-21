import pickle
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.decomposition import PCA
from sklearn.metrics.pairwise import cosine_similarity
from sentence_transformers import SentenceTransformer
from django.conf import settings
from scraper.models import Article
from .preprocessing import expand_words, clean_data


def build_and_save(alpha: float = 0.6):

    print("Fetching articles from DB...")
    articles = list(
        Article.objects.all().values("url", "title", "description", "content", "image_url")
    )

    if not articles:
        print("No articles found.")
        return

    urls = [a["url"] for a in articles]
    titles = [a["title"] for a in articles]
    descriptions = [a["description"] for a in articles]
    image_urls = [a["image_url"] for a in articles]
    contents = [a["content"] for a in articles]

    print("Preprocessing content...")
    processed = [clean_data(expand_words(c)) for c in contents]

    print("Vectorizing (TF-IDF)...")
    vectorizer   = TfidfVectorizer()
    tfidf_matrix = vectorizer.fit_transform(processed)

    print("Applying PCA...")
    pca        = PCA(n_components=100)
    pca_matrix = pca.fit_transform(tfidf_matrix.toarray())

    print("Computing TF-IDF similarity matrix...")
    tfidf_sim = cosine_similarity(pca_matrix, pca_matrix)

    print("Building sentence embeddings...")
    model      = SentenceTransformer("all-MiniLM-L6-v2")
    embeddings = model.encode(contents, show_progress_bar=True, batch_size=32)

    emb_sim = cosine_similarity(embeddings, embeddings)

    print(f"Building hybrid similarity matrix (alpha={alpha})...")
    hybrid_sim = _build_hybrid_matrix(tfidf_sim, emb_sim, alpha)

    data = {

        "urls":         urls,
        "titles":       titles,
        "descriptions": descriptions,
        "image_urls":   image_urls,

        "vectorizer":   vectorizer,
        "tfidf_matrix": tfidf_matrix,
        "pca":          pca,
        "pca_matrix":   pca_matrix,
        "tfidf_sim":    tfidf_sim,

        "embeddings":   embeddings,
        "emb_sim":      emb_sim,

        "hybrid_sim":   hybrid_sim,
        "alpha":        alpha,
    }

    settings.ARTIFACTS_DIR.mkdir(exist_ok=True)
    path = settings.ARTIFACTS_DIR / "objects.pkl"
    with open(path, "wb") as f:
        pickle.dump(data, f)

    print(f"Artifacts saved to {path}")



def _normalize_rows(matrix: np.ndarray) -> np.ndarray:
    """Min-max normalize each row independently to [0, 1]."""
    mins = matrix.min(axis=1, keepdims=True)
    maxs = matrix.max(axis=1, keepdims=True)
    denom = np.where(maxs - mins == 0, 1, maxs - mins)   # avoid /0
    return (matrix - mins) / denom


def _build_hybrid_matrix(
    tfidf_sim: np.ndarray,
    emb_sim:   np.ndarray,
    alpha:     float,
) -> np.ndarray:
    """Return a row-normalized hybrid similarity matrix."""
    tfidf_norm = _normalize_rows(tfidf_sim)
    emb_norm   = _normalize_rows(emb_sim)
    return alpha * tfidf_norm + (1 - alpha) * emb_norm