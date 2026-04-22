from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("leases", "0017_lease_previous_lease"),
    ]

    operations = [
        migrations.AddField(
            model_name="lease",
            name="rha_flags",
            field=models.JSONField(
                blank=True,
                default=list,
                help_text=(
                    "List of RHA compliance flags. Each flag: "
                    "{code, section, severity ('blocking'|'advisory'), message, field}. "
                    "Blocking flags prevent finalize / send-for-signing."
                ),
            ),
        ),
        migrations.AddField(
            model_name="lease",
            name="rha_override",
            field=models.JSONField(
                blank=True,
                null=True,
                help_text=(
                    "If blocking flags were overridden, stores "
                    "{user_id, user_email, reason, overridden_at, flags_at_override}."
                ),
            ),
        ),
    ]
