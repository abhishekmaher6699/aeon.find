import pickle
import numpy as np
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.decomposition import PCA
from sklearn.metrics.pairwise import cosine_similarity
from sentence_transformers import SentenceTransformer
from django.conf import settings
from scraper.models import Article
from .preprocessing import expand_words, clean_data


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

    print("Preprocessing...")
    processed = [clean_data(expand_words(c)) for c in contents]

    print("Vectorizing...")
    vectorizer   = TfidfVectorizer()
    tfidf_matrix = vectorizer.fit_transform(processed)

    print("Applying PCA...")
    pca        = PCA(n_components=100)
    pca_matrix = pca.fit_transform(tfidf_matrix.toarray())

    print("Computing similarity matrix...")
    sim_matrix = cosine_similarity(pca_matrix, pca_matrix)

    data = {
        "urls":         urls,
        "titles":       titles,
        "descriptions": descriptions,
        "image_urls":   image_urls,
        "vectorizer":   vectorizer,
        "tfidf_matrix": tfidf_matrix,
        "pca":          pca,
        "pca_matrix":   pca_matrix,
        "sim_matrix":   sim_matrix,
    }

    settings.ARTIFACTS_DIR.mkdir(exist_ok=True)
    path = settings.ARTIFACTS_DIR / "objects.pkl"
    with open(path, "wb") as f:
        pickle.dump(data, f)

    print(f"Artifacts saved to {path}")