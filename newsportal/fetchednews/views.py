from django.shortcuts import render
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework import serializers
from .models import FetchedNews
from .services import NewsDataIOService
from .serializers import FetchedNewsSerializer

# Create your views here.

class FetchedNewsViewSet(viewsets.ReadOnlyModelViewSet):
    queryset = FetchedNews.objects.all()
    serializer_class = FetchedNewsSerializer

    def get_queryset(self):
        queryset = super().get_queryset()
        category = self.request.query_params.get('category')
        if category:
            queryset = queryset.filter(category__iexact=category)
        return queryset

    @action(detail=False, methods=['post'])
    def fetch_nepal_news(self, request):
        """
        Endpoint to fetch latest news from Nepal
        """
        success, message = NewsDataIOService.fetch_nepal_news()
        
        if success:
            return Response({
                'status': 'success',
                'message': message
            }, status=status.HTTP_200_OK)
        return Response({
            'status': 'error',
            'message': message
        }, status=status.HTTP_400_BAD_REQUEST)
