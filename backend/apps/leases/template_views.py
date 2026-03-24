import io
import os
from django.http import HttpResponse
from rest_framework.views import APIView
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework import status, generics

from .models import LeaseTemplate
from .serializers import LeaseTemplateSerializer

# Lazy import so startup doesn't fail if docxtpl isn't installed yet
try:
    from docxtpl import DocxTemplate
except ImportError:
    DocxTemplate = None


class LeaseTemplateListView(generics.ListCreateAPIView):
    """
    GET  /api/v1/leases/templates/ — list active lease templates.
    POST /api/v1/leases/templates/ — upload a new DOCX template (multipart).

    Multipart POST fields:
      name        (string, required)
      docx_file   (file, required — .docx)
      version     (string, optional, default "1.0")
      province    (string, optional)
    """
    serializer_class = LeaseTemplateSerializer
    permission_classes = [IsAuthenticated]
    parser_classes = [*generics.ListCreateAPIView.parser_classes]

    def get_queryset(self):
        return LeaseTemplate.objects.filter(is_active=True)

    def create(self, request, *args, **kwargs):
        name = (request.data.get("name") or "").strip()
        if not name:
            return Response({"error": "name is required."}, status=status.HTTP_400_BAD_REQUEST)

        # Accept either field name for the file
        uploaded_file = request.FILES.get("docx_file") or request.FILES.get("template_file")
        if not uploaded_file:
            return Response({"error": "template_file (or docx_file) is required."}, status=status.HTTP_400_BAD_REQUEST)

        lower_name = uploaded_file.name.lower()
        is_docx = lower_name.endswith(".docx")
        is_pdf = lower_name.endswith(".pdf")
        if not is_docx and not is_pdf:
            return Response({"error": "Only .docx or .pdf files are accepted."}, status=status.HTTP_400_BAD_REQUEST)

        tmpl = LeaseTemplate.objects.create(
            name=name,
            version=request.data.get("version") or "1.0",
            province=request.data.get("province") or "",
            docx_file=uploaded_file,
        )

        # Discover merge fields — only possible for DOCX templates
        if is_docx and DocxTemplate is not None:
            try:
                doc = DocxTemplate(tmpl.docx_file.path)
                variables = list(doc.get_undeclared_template_variables())
                tmpl.fields_schema = variables
                tmpl.save(update_fields=["fields_schema"])
            except Exception:
                pass  # field discovery is best-effort

        serializer = LeaseTemplateSerializer(tmpl, context={"request": request})
        return Response(serializer.data, status=status.HTTP_201_CREATED)


class LeaseTemplateDetailView(generics.RetrieveUpdateDestroyAPIView):
    """
    GET    /api/v1/leases/templates/{id}/ — retrieve
    PATCH  /api/v1/leases/templates/{id}/ — update (e.g. set is_active=True)
    DELETE /api/v1/leases/templates/{id}/ — delete
    """
    serializer_class = LeaseTemplateSerializer
    permission_classes = [IsAuthenticated]
    queryset = LeaseTemplate.objects.all()


class GenerateLeaseDocumentView(APIView):
    """
    POST /api/v1/leases/generate/

    Fill a DOCX lease template with provided context values and return
    the rendered document as a file download.

    Request body:
    {
        "template_id": 1,      # optional — uses first active template if omitted
        "context": {
            "landlord_name": "...",
            "tenant_name": "...",
            "monthly_rent": "R 12 500",
            ...
        }
    }
    """
    permission_classes = [IsAuthenticated]

    def post(self, request):
        if DocxTemplate is None:
            return Response(
                {"error": "docxtpl is not installed. Run: pip install docxtpl"},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )

        template_id = request.data.get("template_id")
        context = request.data.get("context") or {}

        if template_id:
            try:
                tmpl = LeaseTemplate.objects.get(pk=template_id, is_active=True)
            except LeaseTemplate.DoesNotExist:
                return Response({"error": "Template not found."}, status=status.HTTP_404_NOT_FOUND)
        else:
            tmpl = LeaseTemplate.objects.filter(is_active=True).first()
            if not tmpl:
                return Response(
                    {"error": "No active lease template found. Upload one first."},
                    status=status.HTTP_404_NOT_FOUND,
                )

        if not tmpl.docx_file or not os.path.exists(tmpl.docx_file.path):
            return Response({"error": "Template file not found on disk."}, status=status.HTTP_404_NOT_FOUND)

        # Render the template
        doc = DocxTemplate(tmpl.docx_file.path)
        doc.render(_sanitize_context(context))

        # Stream as DOCX download
        buffer = io.BytesIO()
        doc.save(buffer)
        buffer.seek(0)

        filename = f"lease_{context.get('tenant_name', 'draft').replace(' ', '_')}.docx"
        response = HttpResponse(
            buffer.read(),
            content_type="application/vnd.openxmlformats-officedocument.wordprocessingml.document",
        )
        response["Content-Disposition"] = f'attachment; filename="{filename}"'
        return response


class LeaseTemplatePreviewView(APIView):
    """
    GET /api/v1/leases/templates/{id}/preview/
    Returns template paragraphs + fields for the template editor middle panel.
    """
    permission_classes = [IsAuthenticated]

    def get(self, request, pk):
        try:
            tmpl = LeaseTemplate.objects.get(pk=pk)
        except LeaseTemplate.DoesNotExist:
            return Response({"error": "Not found."}, status=status.HTTP_404_NOT_FOUND)

        if not tmpl.docx_file:
            return Response({"error": "No file attached."}, status=status.HTTP_404_NOT_FOUND)

        try:
            file_path = tmpl.docx_file.path
        except Exception:
            return Response({"error": "File not found on disk."}, status=status.HTTP_404_NOT_FOUND)

        lower = file_path.lower()
        if lower.endswith(".pdf"):
            return Response({
                "type": "pdf",
                "name": tmpl.name,
                "fields": tmpl.fields_schema,
                "paragraphs": [],
            })

        try:
            from docx import Document as DocxDocument
        except ImportError:
            return Response({"error": "python-docx not installed."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        if not os.path.exists(file_path):
            return Response({"error": "File not found on disk."}, status=status.HTTP_404_NOT_FOUND)

        doc = DocxDocument(file_path)
        paragraphs = []
        for p in doc.paragraphs:
            text = p.text
            if text.strip():
                paragraphs.append({"style": p.style.name, "text": text})

        return Response({
            "type": "docx",
            "name": tmpl.name,
            "fields": tmpl.fields_schema,
            "paragraphs": paragraphs,
            "content_html": tmpl.content_html or "",
        })


class LeaseTemplateAIChatView(APIView):
    """
    POST /api/v1/leases/templates/{id}/ai-chat/
    Stateless multi-turn AI chat scoped to a specific template.
    Body: { messages: [{role, content}, ...], message: "latest user message" }
    Returns: { reply }
    """
    permission_classes = [IsAuthenticated]

    def post(self, request, pk):
        import anthropic
        from django.conf import settings

        try:
            tmpl = LeaseTemplate.objects.get(pk=pk)
        except LeaseTemplate.DoesNotExist:
            return Response({"error": "Template not found."}, status=status.HTTP_404_NOT_FOUND)

        messages = request.data.get("messages") or []
        user_message = (request.data.get("message") or "").strip()
        if not user_message:
            return Response({"error": "message is required."}, status=status.HTTP_400_BAD_REQUEST)

        fields_info = ", ".join(tmpl.fields_schema) if tmpl.fields_schema else "none discovered yet"

        # Build document content summary for the AI
        doc_content_snippet = ""
        if tmpl.content_html:
            import re
            plain = re.sub(r"<[^>]+>", " ", tmpl.content_html)
            plain = re.sub(r"\s+", " ", plain).strip()
            doc_content_snippet = plain[:3000]
        elif tmpl.docx_file:
            try:
                file_path = tmpl.docx_file.path
                if file_path.lower().endswith(".docx"):
                    from docx import Document as DocxDocument
                    doc = DocxDocument(file_path)
                    lines = [p.text for p in doc.paragraphs if p.text.strip()]
                    doc_content_snippet = "\n".join(lines)[:3000]
            except Exception:
                pass

        content_section = (
            f"\n\nCURRENT DOCUMENT CONTENT (first 3000 chars):\n---\n{doc_content_snippet}\n---"
            if doc_content_snippet else ""
        )

        system = (
            f"You are an expert South African residential lease template advisor.\n"
            f"You are helping the user edit and improve the lease template: \"{tmpl.name}\".\n"
            f"Discovered merge fields in this template: {fields_info}\n"
            f"{content_section}\n\n"
            "Your role:\n"
            "- Explain what clauses mean in plain language\n"
            "- Suggest additional RHA-compliant clauses or merge fields\n"
            "- Generate new clause text when asked\n"
            "- Advise on what signing fields are needed (signature, initials, date)\n"
            "- Keep responses concise and practical\n\n"
            "Always respond in plain text (no JSON required)."
        )

        # Build message list — must start with user role
        api_messages = list(messages) + [{"role": "user", "content": user_message}]
        while api_messages and api_messages[0].get("role") != "user":
            api_messages = api_messages[1:]

        try:
            api_key = getattr(settings, "ANTHROPIC_API_KEY", "")
            client = anthropic.Anthropic(api_key=api_key)
            response = client.messages.create(
                model="claude-sonnet-4-6",
                max_tokens=800,
                system=system,
                messages=api_messages,
            )
            reply = response.content[0].text
        except Exception as e:
            return Response({"error": str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

        return Response({"reply": reply})


def _sanitize_context(context: dict) -> dict:
    """Ensure all context values are strings (docxtpl requires it for text runs)."""
    safe = {}
    for key, value in context.items():
        if value is None or value == "":
            safe[key] = "—"
        elif isinstance(value, bool):
            safe[key] = "Yes" if value else "No"
        elif isinstance(value, (int, float)):
            safe[key] = str(value)
        else:
            safe[key] = str(value)
    return safe
