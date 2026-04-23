import django.db.models.deletion
import django.utils.timezone
import secrets
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="DSARRequest",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                (
                    "requester",
                    models.ForeignKey(
                        blank=True,
                        help_text="User who submitted this request (null if account was deleted before processing)",
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="dsar_requests",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                (
                    "requester_email",
                    models.EmailField(
                        help_text="Denormalised email at submission time — preserved even after account deletion",
                        max_length=254,
                    ),
                ),
                ("request_type", models.CharField(choices=[("sar", "Subject Access Request (s23)"), ("rtbf", "Right to Erasure (s24)")], max_length=10)),
                ("reason", models.TextField(blank=True, help_text="Optional reason or additional context provided by the data subject")),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("pending", "Pending"),
                            ("in_review", "In Review"),
                            ("approved", "Approved"),
                            ("denied", "Denied"),
                            ("completed", "Completed"),
                        ],
                        db_index=True,
                        default="pending",
                        max_length=20,
                    ),
                ),
                ("operator_notes", models.TextField(blank=True, help_text="Internal notes by the reviewing operator (not shared with the data subject)")),
                ("denial_reason", models.TextField(blank=True, help_text="Public-facing reason for denial (communicated to the data subject)")),
                (
                    "reviewed_by",
                    models.ForeignKey(
                        blank=True,
                        help_text="Operator who approved/denied the request",
                        null=True,
                        on_delete=django.db.models.deletion.SET_NULL,
                        related_name="dsar_reviews",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
                ("reviewed_at", models.DateTimeField(blank=True, null=True)),
                ("sla_deadline", models.DateTimeField(help_text="30-day statutory deadline (POPIA s23/s24)")),
                ("created_at", models.DateTimeField(auto_now_add=True, db_index=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
                ("completed_at", models.DateTimeField(blank=True, null=True)),
            ],
            options={
                "verbose_name": "DSAR Request",
                "verbose_name_plural": "DSAR Requests",
                "ordering": ["-created_at"],
            },
        ),
        migrations.CreateModel(
            name="ExportJob",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                (
                    "dsar_request",
                    models.OneToOneField(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="export_job",
                        to="popia.dsarrequest",
                    ),
                ),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("queued", "Queued"),
                            ("running", "Running"),
                            ("completed", "Completed"),
                            ("failed", "Failed"),
                        ],
                        default="queued",
                        max_length=20,
                    ),
                ),
                ("archive_path", models.CharField(blank=True, help_text="Path relative to MEDIA_ROOT — set by the export service on completion", max_length=512)),
                ("download_token", models.CharField(default=secrets.token_urlsafe, help_text="Signed download token (URL-safe base64, 128 chars)", max_length=128, unique=True)),
                ("expires_at", models.DateTimeField(help_text="Token/file expiry (7-day TTL by default)")),
                ("error_detail", models.TextField(blank=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
                ("updated_at", models.DateTimeField(auto_now=True)),
            ],
            options={
                "verbose_name": "Export Job",
                "verbose_name_plural": "Export Jobs",
                "ordering": ["-created_at"],
            },
        ),
        migrations.AddIndex(
            model_name="dsarrequest",
            index=models.Index(fields=["status", "sla_deadline"], name="popia_dsar_status_sla_idx"),
        ),
        migrations.AddIndex(
            model_name="dsarrequest",
            index=models.Index(fields=["requester", "request_type"], name="popia_dsar_requester_type_idx"),
        ),
    ]
