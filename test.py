import os
import sys
sys.path.append(os.path.dirname(os.path.dirname(os.path.abspath(__file__))))
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'aeon.settings')

import django
django.setup()

import numpy as np
import pickle
from sentence_transformers import SentenceTransformer
from sklearn.metrics.pairwise import cosine_similarity
from scraper.models import Article

EMBEDDINGS_PATH = './artifacts/embeddings.npy'
SIM_MATRIX_PATH = './artifacts/sim_matrix_embeddings.npy'

# load data from DB
print("Loading articles from DB...")
articles = list(Article.objects.all().values('url', 'title', 'content'))
urls = [a['url'] for a in articles]
titles = [a['title'] for a in articles]
contents = [a['content'] for a in articles]
print(f"Loaded {len(urls)} articles")

# load or build embeddings
if os.path.exists(EMBEDDINGS_PATH) and os.path.exists(SIM_MATRIX_PATH):
    print("Loading saved embeddings...")
    embeddings = np.load(EMBEDDINGS_PATH)
    sim_matrix = np.load(SIM_MATRIX_PATH)
    print("Ready.\n")
else:
    model = SentenceTransformer('all-MiniLM-L6-v2')
    print("Building embeddings...")
    embeddings = model.encode(contents, show_progress_bar=True, batch_size=32)
    print("Computing similarity matrix...")
    sim_matrix = cosine_similarity(embeddings, embeddings)
    print("Saving...")
    np.save(EMBEDDINGS_PATH, embeddings)
    np.save(SIM_MATRIX_PATH, sim_matrix)
    print("Ready.\n")

# load tfidf artifacts
with open('./artifacts/objects.pkl', 'rb') as f:
    data = pickle.load(f)

tfidf_urls = data['urls']
tfidf_sim_matrix = data['sim_matrix']
tfidf_titles = data['titles']

def recommend(url, top_n=10):
    if url not in urls:
        print("URL not found in DB")
        return
    idx = urls.index(url)
    scores = list(enumerate(sim_matrix[idx]))
    scores = sorted(scores, key=lambda x: x[1], reverse=True)
    scores = scores[1:top_n+1]
    print(f"\nRecommendations for: {titles[idx]}\n")
    for i, score in scores:
        print(f"  {score:.3f} | {titles[i]}")
        print(f"  {urls[i]}")
        print("---------------------")

def recommend_tfidf(url, top_n=10):
    if url not in tfidf_urls:
        print("  URL not found in TF-IDF artifacts")
        return
    idx = tfidf_urls.index(url)
    scores = list(enumerate(tfidf_sim_matrix[idx]))
    scores = sorted(scores, key=lambda x: x[1], reverse=True)
    scores = scores[1:top_n+1]
    for i, score in scores:
        print(f"  {score:.3f} | {tfidf_titles[i]}")
        print(f"  {tfidf_urls[i]}")
        print("---------------------")

def recommend_hybrid(url, top_n=10, alpha=0.5):
    if url not in urls:
        print("URL not found")
        return
    idx = urls.index(url)
    tfidf_idx = tfidf_urls.index(url) if url in tfidf_urls else None

    query_vec = embeddings[idx].reshape(1, -1)
    emb_scores = cosine_similarity(query_vec, embeddings).flatten()

    tfidf_scores = tfidf_sim_matrix[tfidf_idx] if tfidf_idx is not None else np.zeros(len(urls))

    emb_scores = (emb_scores - emb_scores.min()) / (emb_scores.max() - emb_scores.min())
    tfidf_scores = (tfidf_scores - tfidf_scores.min()) / (tfidf_scores.max() - tfidf_scores.min())

    final_scores = alpha * tfidf_scores + (1 - alpha) * emb_scores
    top_indices = final_scores.argsort()[-top_n-1:][::-1]
    top_indices = [i for i in top_indices if i != idx][:top_n]

    print(f"\nRecommendations for: {titles[idx]}\n")
    for i in top_indices:
        print(f"  {final_scores[i]:.3f} | {titles[i]}")
        print(f"  {urls[i]}")
        print("---------------------")

while True:
    url = input("\nEnter Aeon essay URL (or 'q' to quit): ").strip()
    if url == 'q':
        break
    print("\n=== TF-IDF ===")
    recommend_tfidf(url)
    print("\n=== Embeddings ===")
    recommend(url)
    print("\n=== Hybrid (50/50) ===")
    recommend_hybrid(url, alpha=0.6)