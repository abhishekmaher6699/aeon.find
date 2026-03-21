import pickle
import numpy as np
from sklearn.metrics.pairwise import cosine_similarity
from django.conf import settings
from .preprocessing import expand_words, clean_data

_cache = None


def load_artifacts():
    global _cache
    if _cache is None:
        path = settings.ARTIFACTS_DIR / 'objects.pkl'
        with open(path, 'rb') as f:
            _cache = pickle.load(f)
    return _cache


def recommend_by_url(url, top_n=10):
    data = load_artifacts()
    urls = data['urls']

    if url in urls:
        idx     = urls.index(url)
        scores  = data['sim_matrix'][idx].copy()
        scores[idx] = -1
        indices = scores.argsort()[-top_n:][::-1]
    else:
        from scraper.scraper import scrape_content
        slug      = url.rstrip('/').split('/')[-1]
        content   = scrape_content(slug)
        processed = clean_data(expand_words(content))
        vector    = data['vectorizer'].transform([processed])
        pca_vec   = data['pca'].transform(vector.toarray()).astype(np.float32)
        scores    = cosine_similarity(pca_vec, data['pca_matrix']).flatten()
        indices   = scores.argsort()[-top_n:][::-1]

    return _build_results(data, indices)


def recommend_by_prompt(prompt, top_n=10):
    data      = load_artifacts()
    processed = clean_data(expand_words(prompt))
    vector    = data['vectorizer'].transform([processed])
    scores    = cosine_similarity(vector, data['tfidf_matrix']).flatten()
    indices   = scores.argsort()[-top_n:][::-1]
    return _build_results(data, indices)


def _build_results(data, indices):
    return [
        {
            "url":         data['urls'][i],
            "title":       data['titles'][i],
            "description": data['descriptions'][i],
            "image_url":   data['image_urls'][i],
        }
        for i in indices
    ]