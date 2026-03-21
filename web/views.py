from django.shortcuts import render
from recommender.engine import recommend_by_url, recommend_by_prompt

def index(request):
    return render(request, 'index.html')

def results(request):
    query = request.GET.get('query', '').strip()
    mode = request.GET.get('mode', 'prompt')

    if not query:
        return render(request, 'index.html')

    try:
        if query.startswith('https://aeon.co/essays/'):
            recommendations = recommend_by_url(query)
            mode = 'url'
        elif query.startswith('http://') or query.startswith('https://'):
            return render(request, 'results.html', {
                'error': 'We only support Aeon essay URLs. Try https://aeon.co/essays/...',
                'query': query,
                'mode': mode,
            })
        else:
            recommendations = recommend_by_prompt(query)
            mode = 'prompt'
    except Exception as e:
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