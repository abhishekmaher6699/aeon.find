import pickle
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.decomposition import PCA
from sklearn.metrics.pairwise import cosine_similarity
from django.conf import settings
from scraper.models import Article
from .preprocessing import expand_words, clean_data


def build_and_save():
    print("Fetching articles from DB...")
    articles = list(
        Article.objects.all().values("url", "title", "description", "content", "image_url")
    )

    if not articles:
        print("No articles found.")
        return

    urls         = [a["url"]         for a in articles]
    titles       = [a["title"]       for a in articles]
    descriptions = [a["description"] for a in articles]
    image_urls   = [a["image_url"]   for a in articles]
    contents     = [a["content"]     for a in articles]
    combined_texts = [
        " ".join(part for part in [title, description, content] if part)
        for title, description, content in zip(titles, descriptions, contents)
    ]

    print("Preprocessing...")
    processed = [clean_data(expand_words(text)) for text in combined_texts]

    print("Vectorizing...")
    vectorizer   = TfidfVectorizer()
    tfidf_matrix = vectorizer.fit_transform(processed)  # stays sparse

    print("Applying PCA...")
    pca        = PCA(n_components=100)
    pca_matrix = pca.fit_transform(tfidf_matrix.toarray())

    print("Building embeddings...")
    from sentence_transformers import SentenceTransformer
    model      = SentenceTransformer("all-MiniLM-L6-v2")
    embeddings = model.encode(combined_texts, show_progress_bar=True, batch_size=32)

    print("Computing similarity matrices...")
    tfidf_sim  = cosine_similarity(pca_matrix)
    emb_sim    = cosine_similarity(embeddings)
    sim_matrix = 0.5 * _normalize(tfidf_sim) + 0.5 * _normalize(emb_sim)

    data = {
        "urls":         urls,
        "titles":       titles,
        "descriptions": descriptions,
        "image_urls":   image_urls,
        "vectorizer":   vectorizer,
        "tfidf_matrix": tfidf_matrix,                    # sparse, ~5-10MB
        "pca":          pca,
        "pca_matrix":   pca_matrix.astype(np.float32),  # float32, ~1MB
        "sim_matrix":   sim_matrix.astype(np.float32),  # float32, ~25MB
    }

    settings.ARTIFACTS_DIR.mkdir(exist_ok=True)
    path = settings.ARTIFACTS_DIR / "objects.pkl"
    with open(path, "wb") as f:
        pickle.dump(data, f)

    print(f"Artifacts saved to {path}")
    print(f"File size: {path.stat().st_size / 1024 / 1024:.1f} MB")


def _normalize(matrix):
    mins  = matrix.min(axis=1, keepdims=True)
    maxs  = matrix.max(axis=1, keepdims=True)
    denom = np.where(maxs - mins == 0, 1, maxs - mins)
    return (matrix - mins) / denom
