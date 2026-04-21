from django.shortcuts import render
import logging
from recommender.engine import recommend_by_url, recommend_by_prompt

logger = logging.getLogger("web")

def index(request):
    return render(request, 'index.html')

def results(request):
    query = request.GET.get('query', '').strip()
    mode = request.GET.get('mode', 'prompt')
    logger.info("Results view called | mode=%s query=%s", mode, query)

    if not query:
        logger.info("Results view received empty query")
        return render(request, 'index.html')

    try:
        if query.startswith('https://aeon.co/essays/'):
            recommendations = recommend_by_url(query)
            mode = 'url'
            logger.info("URL recommendations generated | query=%s count=%s", query, len(recommendations))
        elif query.startswith('http://') or query.startswith('https://'):
            logger.warning("Unsupported external URL submitted | query=%s", query)
            return render(request, 'results.html', {
                'error': 'We only support Aeon essay URLs. Try https://aeon.co/essays/...',
                'query': query,
                'mode': mode,
            })
        else:
            recommendations = recommend_by_prompt(query)
            mode = 'prompt'
            logger.info("Prompt recommendations generated | query=%s count=%s", query, len(recommendations))
    except Exception as e:
        logger.exception("Recommendation request failed | query=%s mode=%s error=%s", query, mode, e)
        return render(request, 'results.html', {
            'error': str(e),
            'query': query,
            'mode': mode,
        })

    return render(request, 'results.html', {
        'recommendations': recommendations,
        'query': query,
        'mode': mode,
    })

def extension(request):
    return render(request, 'extension.html')
