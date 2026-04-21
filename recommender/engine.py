import pickle
import numpy as np
import logging
from datetime import datetime, UTC
from sklearn.metrics.pairwise import cosine_similarity
from django.conf import settings
from .preprocessing import expand_words, clean_data

_cache = None
logger = logging.getLogger("recommender")


def load_artifacts():
    global _cache
    if _cache is None:
        path = settings.ARTIFACTS_DIR / 'objects.pkl'
        logger.info("Loading recommender artifacts | path=%s", path)
        stat = path.stat()
        logger.info(
            "Artifact file details | size_bytes=%s modified_at=%s",
            stat.st_size,
            datetime.fromtimestamp(stat.st_mtime, UTC).isoformat(),
        )
        with open(path, 'rb') as f:
            _cache = pickle.load(f)
        logger.info(
            "Artifacts loaded | urls=%s titles=%s sim_matrix_shape=%s pca_matrix_shape=%s tfidf_shape=%s",
            len(_cache['urls']),
            len(_cache['titles']),
            getattr(_cache['sim_matrix'], 'shape', None),
            getattr(_cache['pca_matrix'], 'shape', None),
            getattr(_cache['tfidf_matrix'], 'shape', None),
        )
    return _cache


def recommend_by_url(url, top_n=10):
    data = load_artifacts()
    urls = data['urls']
    logger.info("recommend_by_url called | url=%s top_n=%s cached_urls=%s", url, top_n, len(urls))

    if url in urls:
        idx     = urls.index(url)
        scores  = data['sim_matrix'][idx].copy()
        scores[idx] = -1
        indices = scores.argsort()[-top_n:][::-1]
        logger.info(
            "Known URL path used | url=%s idx=%s top_scores=%s",
            url,
            idx,
            [float(scores[i]) for i in indices[:5]],
        )
    else:
        from scraper.scraper import (
            build_seed_text_from_metadata,
            fetch_recent_article_metadata,
            scrape_content,
        )
        slug      = url.rstrip('/').split('/')[-1]
        content   = scrape_content(
            slug,
            max_attempts=1,
            request_timeout=8,
            wait_on_rate_limit=False,
        )
        source    = "scrape"

        if not content.strip():
            logger.warning("Scrape returned empty content, trying metadata fallback | url=%s slug=%s", url, slug)
            metadata = fetch_recent_article_metadata(slug, max_pages=3)
            content = build_seed_text_from_metadata(metadata)
            source = "metadata"

        processed = clean_data(expand_words(content))
        logger.info(
            "Unseen URL path used | url=%s slug=%s source=%s raw_chars=%s processed_chars=%s processed_preview=%s",
            url,
            slug,
            source,
            len(content),
            len(processed),
            processed[:240],
        )
        if not content.strip():
            logger.error("Unseen URL produced empty text after fallback | url=%s slug=%s", url, slug)
            raise ValueError("Could not fetch usable text for that Aeon URL.")
        if not processed.strip():
            logger.error("Unseen URL preprocessing produced empty text | url=%s slug=%s source=%s", url, slug, source)
            raise ValueError("Could not extract usable text from that Aeon URL.")
        vector    = data['vectorizer'].transform([processed])
        pca_vec   = data['pca'].transform(vector.toarray()).astype(np.float32)
        scores    = cosine_similarity(pca_vec, data['pca_matrix']).flatten()
        indices   = scores.argsort()[-top_n:][::-1]
        logger.info(
            "Unseen URL similarity computed | url=%s source=%s vector_shape=%s pca_shape=%s top_scores=%s",
            url,
            source,
            getattr(vector, 'shape', None),
            getattr(pca_vec, 'shape', None),
            [float(scores[i]) for i in indices[:5]],
        )

    results = _build_results(data, indices)
    logger.info(
        "Recommendations ready | url=%s result_urls=%s",
        url,
        [result["url"] for result in results[:5]],
    )
    return results


def recommend_by_prompt(prompt, top_n=10):
    data      = load_artifacts()
    processed = clean_data(expand_words(prompt))
    logger.info(
        "recommend_by_prompt called | prompt_chars=%s processed_chars=%s processed_preview=%s",
        len(prompt),
        len(processed),
        processed[:240],
    )
    vector    = data['vectorizer'].transform([processed])
    scores    = cosine_similarity(vector, data['tfidf_matrix']).flatten()
    indices   = scores.argsort()[-top_n:][::-1]
    logger.info(
        "Prompt similarity computed | vector_shape=%s top_scores=%s",
        getattr(vector, 'shape', None),
        [float(scores[i]) for i in indices[:5]],
    )
    results = _build_results(data, indices)
    logger.info("Prompt recommendations ready | result_urls=%s", [result["url"] for result in results[:5]])
    return results


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
