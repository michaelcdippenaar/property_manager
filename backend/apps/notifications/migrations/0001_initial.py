# Generated manually — run `makemigrations` locally if your Django version differs.

from django.db import migrations, models


class Migration(migrations.Migration):
    initial = True

    dependencies = []

    operations = [
        migrations.CreateModel(
            name="NotificationLog",
            fields=[
                (
                    "id",
                    models.BigAutoField(
                        auto_created=True,
                        primary_key=True,
                        serialize=False,
                        verbose_name="ID",
                    ),
                ),
                (
                    "channel",
                    models.CharField(
                        choices=[
                            ("email", "Email"),
                            ("sms", "SMS"),
                            ("whatsapp", "WhatsApp"),
                        ],
                        max_length=16,
                    ),
                ),
                ("to_address", models.CharField(max_length=320)),
                ("subject", models.CharField(blank=True, max_length=255)),
                ("body", models.TextField()),
                (
                    "status",
                    models.CharField(
                        choices=[
                            ("pending", "Pending"),
                            ("sent", "Sent"),
                            ("failed", "Failed"),
                        ],
                        default="pending",
                        max_length=16,
                    ),
                ),
                ("provider_message_id", models.CharField(blank=True, max_length=128)),
                ("error_message", models.TextField(blank=True)),
                ("created_at", models.DateTimeField(auto_now_add=True)),
            ],
            options={
                "ordering": ["-created_at"],
            },
        ),
        migrations.AddIndex(
            model_name="notificationlog",
            index=models.Index(
                fields=["-created_at"], name="notificatio_created_e3f_idx"
            ),
        ),
        migrations.AddIndex(
            model_name="notificationlog",
            index=models.Index(
                fields=["channel", "status"], name="notificatio_channel_0f2_idx"
            ),
        ),
    ]
