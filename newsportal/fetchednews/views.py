from django.shortcuts import render
from rest_framework import viewsets, status
from rest_framework.decorators import action
from rest_framework.response import Response
from rest_framework import serializers
from .models import FetchedNews
from .services import NewsDataIOService
from .serializers import FetchedNewsSerializer
from django.utils import timezone

# Create your views here.

class FetchedNewsViewSet(viewsets.ModelViewSet):
    queryset = FetchedNews.objects.all()
    serializer_class = FetchedNewsSerializer

    def get_queryset(self):
        queryset = super().get_queryset()
        category = self.request.query_params.get('category')
        if category:
            queryset = queryset.filter(category__iexact=category)
        return queryset

    def create(self, request, *args, **kwargs):
        # Generate a unique source_id for manual entries
        source_id = f"manual_{timezone.now().timestamp()}"
        
        # Add required fields
        data = request.data.copy()
        data['source_id'] = source_id
        data['published_at'] = timezone.now()
        data['source_url'] = data.get('source_url', '')  # Optional field
        
        serializer = self.get_serializer(data=data)
        serializer.is_valid(raise_exception=True)
        self.perform_create(serializer)
        
        headers = self.get_success_headers(serializer.data)
        return Response(serializer.data, status=status.HTTP_201_CREATED, headers=headers)

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
