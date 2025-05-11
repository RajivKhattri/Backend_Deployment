from rest_framework import serializers
from .models import FetchedNews
 
class FetchedNewsSerializer(serializers.ModelSerializer):
    class Meta:
        model = FetchedNews
        fields = ['id', 'title', 'summary', 'image', 'source_url', 'published_at', 'category', 'source_id']
        read_only_fields = ['source_id', 'published_at'] 