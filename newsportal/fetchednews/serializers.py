from rest_framework import serializers
from .models import FetchedNews
 
class FetchedNewsSerializer(serializers.ModelSerializer):
    summary = serializers.CharField(source='description')
    image = serializers.CharField(source='image_url')

    class Meta:
        model = FetchedNews
        fields = ['id', 'title', 'summary', 'image'] 