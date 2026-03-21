from django.db import models

class Article(models.Model):
    title = models.CharField(max_length=500)
    slug = models.SlugField(max_length=500, unique=True, default='')
    url = models.URLField(max_length=1000, unique=True)
    author = models.CharField(max_length=500, blank=True)
    description = models.TextField(blank=True)
    content = models.TextField()
    category = models.CharField(max_length=500, blank=True)
    section = models.CharField(max_length=500, blank=True)
    image_url = models.URLField(max_length=1000, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    def __str__(self):
        return self.title