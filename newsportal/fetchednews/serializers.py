from rest_framework import serializers
from .models import FetchedNews
 
class FetchedNewsSerializer(serializers.ModelSerializer):
    class Meta:
        model = FetchedNews
        fields = ['id', 'title', 'summary', 'image']
        read_only_fields = ['id'] 