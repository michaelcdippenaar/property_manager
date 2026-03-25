"""
Reusable Clause Library
========================
GET    /api/v1/leases/clauses/              — list clauses (filter: ?category=)
POST   /api/v1/leases/clauses/              — save a clause
DELETE /api/v1/leases/clauses/{id}/         — delete a clause
POST   /api/v1/leases/clauses/{id}/use/     — increment use_count (insert event)
POST   /api/v1/leases/clauses/generate/     — AI generates 3 clause options
POST   /api/v1/leases/clauses/extract/      — extract clauses from a template's HTML
"""

import json
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status, generics

from .models import ReusableClause, LeaseTemplate
from .serializers import ReusableClauseSerializer
from .template_views import _get_anthropic_api_key

ALLOWED_CATEGORIES = [c[0] for c in ReusableClause.CATEGORIES]

# Prompt prefix shared by both generate and extract
_CLAUSE_SYSTEM = (
    "You are an expert South African residential lease drafter. "
    "You write precise, legally compliant lease clauses for use under the "
    "Rental Housing Act 50 of 1999, CPA, and POPIA.\n\n"
    "Always output ONLY valid JSON. No markdown fences, no commentary.\n"
    "HTML rules: use only <h3>, <p>, <ul>, <ol>, <li>, <strong>, <em>, <u>, <hr>. "
    "Merge fields: <span data-merge-field=\"field_name\">{{ field_name }}</span>. "
    "No <div>, <table>, <style>, <body>."
)


class ReusableClauseListCreateView(generics.ListCreateAPIView):
    serializer_class = ReusableClauseSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        qs = ReusableClause.objects.filter(created_by=self.request.user)
        cat = self.request.query_params.get("category")
        if cat and cat in ALLOWED_CATEGORIES:
            qs = qs.filter(category=cat)
        q = self.request.query_params.get("q", "").strip()
        if q:
            qs = qs.filter(title__icontains=q)
        return qs

    def perform_create(self, serializer):
        template_id = self.request.data.get("source_template_id")
        clause = serializer.save(created_by=self.request.user)
        if template_id:
            try:
                tmpl = LeaseTemplate.objects.get(pk=template_id)
                clause.source_templates.add(tmpl)
            except LeaseTemplate.DoesNotExist:
                pass


class ReusableClauseDestroyView(generics.DestroyAPIView):
    serializer_class = ReusableClauseSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return ReusableClause.objects.filter(created_by=self.request.user)


class ReusableClauseUseView(APIView):
    """POST /clauses/{id}/use/ — increment use_count when clause is inserted."""
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        try:
            clause = ReusableClause.objects.get(pk=pk, created_by=request.user)
        except ReusableClause.DoesNotExist:
            return Response({"error": "Not found."}, status=status.HTTP_404_NOT_FOUND)
        ReusableClause.objects.filter(pk=pk).update(use_count=clause.use_count + 1)
        return Response({"use_count": clause.use_count + 1})


class GenerateClauseView(APIView):
    """
    POST /api/v1/leases/clauses/generate/
    Body: { topic, category?, count? }
    Returns: { options: [{ title, category, html }] }
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        import anthropic
        from django.conf import settings

        topic = (request.data.get("topic") or "").strip()
        if not topic:
            return Response({"error": "topic is required."}, status=status.HTTP_400_BAD_REQUEST)

        category = request.data.get("category") or "general"
        count = min(int(request.data.get("count") or 3), 5)

        prompt = (
            f"Generate {count} alternative clause options for a South African residential lease. "
            f"Topic: \"{topic}\". Category: {category}.\n\n"
            "Return JSON:\n"
            "{\n"
            '  "options": [\n'
            '    { "title": "Short clause title", "category": "category_key", "html": "...HTML..." },\n'
            '    ...\n'
            "  ]\n"
            "}\n\n"
            f"Valid categories: {', '.join(ALLOWED_CATEGORIES)}.\n"
            "Each option should be a distinct style/approach (e.g. strict, standard, tenant-friendly).\n"
            "Include relevant merge fields where appropriate."
        )

        try:
            client = anthropic.Anthropic(api_key=_get_anthropic_api_key())
            response = client.messages.create(
                model="claude-sonnet-4-6",
                max_tokens=3000,
                system=_CLAUSE_SYSTEM,
                messages=[{"role": "user", "content": prompt}],
            )
            raw = response.content[0].text.strip()
            # Strip markdown fences if model adds them
            if raw.startswith("```"):
                raw = raw.split("\n", 1)[1].rsplit("```", 1)[0]
            data = json.loads(raw)
            options = data.get("options", [])
        except json.JSONDecodeError as e:
            return Response({"error": f"JSON parse error: {e}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        return Response({"options": options})


class ExtractClausesView(APIView):
    """
    POST /api/v1/leases/clauses/extract/
    Body: { template_id }
    AI scans the template's content_html and extracts logical reusable clauses.
    Returns: { clauses: [{ title, category, html }] }
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        import anthropic
        from django.conf import settings

        template_id = request.data.get("template_id")
        if not template_id:
            return Response({"error": "template_id is required."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            tmpl = LeaseTemplate.objects.get(pk=template_id)
        except LeaseTemplate.DoesNotExist:
            return Response({"error": "Template not found."}, status=status.HTTP_404_NOT_FOUND)

        html = (tmpl.content_html or "").strip()
        if not html:
            return Response({"error": "Template has no HTML content to extract from."}, status=status.HTTP_400_BAD_REQUEST)

        prompt = (
            f"Here is the HTML content of a lease template named \"{tmpl.name}\":\n\n"
            f"<document>\n{html[:8000]}\n</document>\n\n"
            "Extract all meaningful, self-contained clauses that could be reused in other templates. "
            "Each clause should be a complete logical unit (e.g. a full section about deposit terms, "
            "a POPIA paragraph, a maintenance clause).\n\n"
            "Return JSON:\n"
            "{\n"
            '  "clauses": [\n'
            '    { "title": "Descriptive title", "category": "category_key", "html": "...HTML..." },\n'
            "    ...\n"
            "  ]\n"
            "}\n\n"
            f"Valid categories: {', '.join(ALLOWED_CATEGORIES)}.\n"
            "Preserve all merge field spans exactly as they appear."
        )

        try:
            client = anthropic.Anthropic(api_key=_get_anthropic_api_key())
            response = client.messages.create(
                model="claude-sonnet-4-6",
                max_tokens=4000,
                system=_CLAUSE_SYSTEM,
                messages=[{"role": "user", "content": prompt}],
            )
            raw = response.content[0].text.strip()
            if raw.startswith("```"):
                raw = raw.split("\n", 1)[1].rsplit("```", 1)[0]
            data = json.loads(raw)
            clauses = data.get("clauses", [])
        except json.JSONDecodeError as e:
            return Response({"error": f"JSON parse error: {e}"}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        return Response({"clauses": clauses, "template_name": tmpl.name})
