from django.shortcuts import render
import logging
from recommender.engine import recommend_by_url, recommend_by_prompt

logger = logging.getLogger("web")


def index(request):
    return render(request, 'index.html')


def results(request):
    query = request.GET.get('query', '').strip()
    mode = request.GET.get('mode', 'prompt')

    if not query:
        logger.info("Empty query")
        return render(request, 'index.html')

    try:
        if query.startswith('https://aeon.co/essays/'):
            recommendations = recommend_by_url(query)
            mode = 'url'
            logger.info("URL recommendations generated (%s)", len(recommendations))

        elif query.startswith('http://') or query.startswith('https://'):
            logger.warning("Unsupported URL")
            return render(request, 'results.html', {
                'error': 'We only support Aeon essay URLs. Try https://aeon.co/essays/...',
                'query': query,
                'mode': mode,
            })

        else:
            recommendations = recommend_by_prompt(query)
            mode = 'prompt'
            logger.info("Prompt recommendations generated (%s)", len(recommendations))

    except Exception:
        logger.exception("Recommendation failed")
        return render(request, 'results.html', {
            'error': 'Something went wrong. Please try again.',
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