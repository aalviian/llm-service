from drf_spectacular.utils import extend_schema
from rest_framework.response import Response
from rest_framework.views import APIView


class FineTuneModelView(APIView):
    """
    Fine-tune model API
    POST /api/fine-tune/
    """

    authentication_classes = []
    permission_classes = []

    @extend_schema(
        summary="Fine-tune Model",
        description="Fine-tune a text classification model with custom dataset",
        request={
            "type": "object",
            "properties": {
                "training_data": {
                    "type": "array",
                    "items": {
                        "type": "object",
                        "properties": {"text": {"type": "string"}, "label": {"type": "string"}},
                        "required": ["text", "label"],
                    },
                },
                "model_name": {"type": "string", "default": "distilbert-base-uncased"},
            },
            "required": ["training_data"],
        },
        responses={
            200: {
                "type": "object",
                "properties": {
                    "message": {"type": "string"},
                    "model_path": {"type": "string"},
                    "status": {"type": "string"},
                },
            }
        },
        tags=["Fine-tuning"],
    )
    def post(self, request):
        # Handle empty request body
        if not hasattr(request, "data") or not request.data:
            return Response({"error": "Request body is required"}, status=400)

        training_data = request.data.get("training_data")
        model_name = request.data.get("model_name", "indobenchmark/indobert-base-p1")

        if not training_data:
            return Response({"error": "training_data is required"}, status=400)

        if not isinstance(training_data, list) or len(training_data) == 0:
            return Response({"error": "training_data must be a non-empty list"}, status=400)

        # Validate training data format
        for i, item in enumerate(training_data):
            if not isinstance(item, dict) or "text" not in item or "label" not in item:
                return Response(
                    {
                        "error": f"Invalid training data format at index {i}. Each item must have 'text' and 'label' keys"
                    },
                    status=400,
                )

        try:
            from autoreply.llm.fine_tune import fine_tune_model

            # Start fine-tuning (this will take time)
            model_path = fine_tune_model(training_data, model_name)

            # Save to database
            # from autoreply.models import FineTunedModel
            # FineTunedModel.objects.create(
            #     model_path=model_path,
            #     model_name=model_name,
            #     is_active=True
            # )

            return Response(
                {
                    "message": "Model fine-tuned successfully",
                    "model_path": model_path,
                    "status": "completed",
                }
            )

        except Exception as e:
            return Response({"error": str(e)}, status=500)


class TestFineTunedModelView(APIView):
    """
    Test fine-tuned model API
    POST /api/test-finetuned/
    """

    authentication_classes = []
    permission_classes = []

    @extend_schema(
        summary="Test Fine-tuned Model",
        description="Test the latest fine-tuned model",
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
                    "model_used": {"type": "string"},
                },
            }
        },
        tags=["Fine-tuning"],
    )
    def post(self, request):
        # Handle empty request body
        if not hasattr(request, "data") or not request.data:
            return Response({"error": "Request body is required"}, status=400)

        email_body = request.data.get("email_body")

        if not email_body:
            return Response({"error": "email_body is required"}, status=400)

        try:
            from autoreply.llm.classify import classify_email_text

            predicted_category, confidence = classify_email_text(email_body)

            return Response(
                {
                    "predicted_category": predicted_category,
                    "confidence": confidence,
                    "model_used": "fine-tuned" if predicted_category else "zero-shot",
                }
            )

        except Exception as e:
            return Response({"error": str(e)}, status=500)
