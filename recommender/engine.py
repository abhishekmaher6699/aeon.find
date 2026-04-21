import pickle
import numpy as np
import logging
from sklearn.metrics.pairwise import cosine_similarity
from django.conf import settings
from .preprocessing import expand_words, clean_data

_cache = None
logger = logging.getLogger("recommender")


def load_artifacts():
    global _cache
    if _cache is None:
        path = settings.ARTIFACTS_DIR / 'objects.pkl'
        logger.info("Loading artifacts...")
        with open(path, 'rb') as f:
            _cache = pickle.load(f)
        logger.info("Artifacts loaded (%s items)", len(_cache['urls']))
    return _cache


def recommend_by_url(url, top_n=10):
    data = load_artifacts()
    urls = data['urls']

    if url in urls:
        idx = urls.index(url)
        scores = data['sim_matrix'][idx].copy()
        scores[idx] = -1
        indices = scores.argsort()[-top_n:][::-1]
        logger.info("Known URL used")
    else:
        from scraper.scraper import (
            build_seed_text_from_metadata,
            fetch_recent_article_metadata,
            scrape_content,
        )

        slug = url.rstrip('/').split('/')[-1]
        content = scrape_content(slug, max_attempts=1, request_timeout=8, wait_on_rate_limit=False)
        source = "scrape"

        if not content.strip():
            logger.warning("Scrape failed, using metadata")
            metadata = fetch_recent_article_metadata(slug, max_pages=3)
            content = build_seed_text_from_metadata(metadata)
            source = "metadata"

        processed = clean_data(expand_words(content))

        if not content.strip():
            logger.error("No content for URL")
            raise ValueError("Could not fetch usable text.")

        if not processed.strip():
            logger.error("Processing failed (%s)", source)
            raise ValueError("Could not extract usable text.")

        vector = data['vectorizer'].transform([processed])
        pca_vec = data['pca'].transform(vector.toarray()).astype(np.float32)
        scores = cosine_similarity(pca_vec, data['pca_matrix']).flatten()
        indices = scores.argsort()[-top_n:][::-1]

        logger.info("Unseen URL processed (%s)", source)

    return _build_results(data, indices)


def recommend_by_prompt(prompt, top_n=10):
    data = load_artifacts()
    processed = clean_data(expand_words(prompt))

    vector = data['vectorizer'].transform([processed])
    scores = cosine_similarity(vector, data['tfidf_matrix']).flatten()
    indices = scores.argsort()[-top_n:][::-1]

    logger.info("Prompt recommendation generated")

    return _build_results(data, indices)


def _build_results(data, indices):
    return [
        {
            "url": data['urls'][i],
            "title": data['titles'][i],
            "description": data['descriptions'][i],
            "image_url": data['image_urls'][i],
        }
        for i in indices
    ]