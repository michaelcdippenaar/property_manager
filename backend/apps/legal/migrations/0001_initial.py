import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name="LegalDocument",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                (
                    "doc_type",
                    models.CharField(
                        choices=[("tos", "Terms of Service"), ("privacy", "Privacy Policy")],
                        max_length=20,
                    ),
                ),
                ("version", models.CharField(help_text='Semantic version string, e.g. "1.0", "1.1"', max_length=20)),
                ("effective_date", models.DateField()),
                (
                    "summary_of_changes",
                    models.TextField(
                        blank=True,
                        help_text="Human-readable changelog entry shown to users on re-acknowledgement prompts.",
                    ),
                ),
                (
                    "url",
                    models.URLField(
                        help_text="Canonical public URL of this document, e.g. https://klikk.co.za/legal/terms",
                    ),
                ),
                (
                    "is_current",
                    models.BooleanField(
                        default=False,
                        help_text="Exactly one document per doc_type should be current at any time.",
                    ),
                ),
                (
                    "requires_re_ack",
                    models.BooleanField(
                        default=False,
                        help_text=(
                            "Set True for material changes that require existing users to re-acknowledge. "
                            "When True, logged-in users without a UserConsent for this version are gated."
                        ),
                    ),
                ),
                ("created_at", models.DateTimeField(auto_now_add=True)),
            ],
            options={
                "ordering": ["-effective_date", "-created_at"],
            },
        ),
        migrations.CreateModel(
            name="UserConsent",
            fields=[
                ("id", models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name="ID")),
                ("accepted_at", models.DateTimeField(auto_now_add=True)),
                ("ip_address", models.GenericIPAddressField(blank=True, null=True)),
                ("user_agent", models.TextField(blank=True)),
                (
                    "document",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.PROTECT,
                        related_name="consents",
                        to="legal.legaldocument",
                    ),
                ),
                (
                    "user",
                    models.ForeignKey(
                        on_delete=django.db.models.deletion.CASCADE,
                        related_name="legal_consents",
                        to=settings.AUTH_USER_MODEL,
                    ),
                ),
            ],
            options={
                "ordering": ["-accepted_at"],
            },
        ),
        migrations.AddConstraint(
            model_name="legaldocument",
            constraint=models.UniqueConstraint(
                fields=["doc_type", "version"],
                name="unique_legal_document_version",
            ),
        ),
        migrations.AddConstraint(
            model_name="userconsent",
            constraint=models.UniqueConstraint(
                fields=["user", "document"],
                name="unique_user_consent_per_document",
            ),
        ),
        migrations.AddIndex(
            model_name="userconsent",
            index=models.Index(fields=["user", "document"], name="legal_userconsent_user_doc_idx"),
        ),
    ]
