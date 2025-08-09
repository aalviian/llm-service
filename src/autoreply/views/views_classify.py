from rest_framework.views import APIView
from rest_framework.response import Response
from drf_spectacular.utils import extend_schema


class ClassifyEmailView(APIView):
    """
    Test email classification API
    POST /api/classify-email/
    """

    authentication_classes = []
    permission_classes = []

    @extend_schema(
        summary="Classify Email",
        description="Test email classification using ML model",
        request={
            "type": "object",
            "properties": {"email_body": {"type": "string"}},
            "required": ["email_body"],
        },
        responses={
            200: {
                "type": "object",
                "properties": {
                    "predicted_category": {"type": "string"},
                    "confidence": {"type": "number"},
                },
            }
        },
        tags=["Classification"],
    )
    def post(self, request):
        # Handle empty request body
        if not hasattr(request, 'data') or not request.data:
            return Response({"error": "Request body is required"}, status=400)
            
        email_body = request.data.get("email_body")
        
        if not email_body:
            return Response({"error": "email_body is required"}, status=400)
        
        try:
            from autoreply.llm.classify import classify_email_text
            
            predicted_category, confidence = classify_email_text(email_body)
            
            return Response({
                "predicted_category": predicted_category,
                "confidence": confidence
            })
            
        except Exception as e:
            return Response({"error": str(e)}, status=500)