import django.db.models.deletion
from django.conf import settings
from django.db import migrations, models


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('leases', '0010_leasetemplate_header_footer_html'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='ESigningSubmission',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('docuseal_submission_id', models.CharField(blank=True, max_length=100)),
                ('docuseal_template_id', models.CharField(blank=True, max_length=100)),
                ('status', models.CharField(
                    choices=[
                        ('pending', 'Pending'),
                        ('in_progress', 'In Progress'),
                        ('completed', 'Completed'),
                        ('declined', 'Declined'),
                        ('expired', 'Expired'),
                    ],
                    default='pending',
                    max_length=20,
                )),
                ('signers', models.JSONField(default=list)),
                ('signed_pdf_url', models.URLField(blank=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('webhook_payload', models.JSONField(default=dict)),
                ('lease', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='signing_submissions',
                    to='leases.lease',
                )),
                ('created_by', models.ForeignKey(
                    null=True,
                    on_delete=django.db.models.deletion.SET_NULL,
                    to=settings.AUTH_USER_MODEL,
                )),
            ],
            options={
                'ordering': ['-created_at'],
            },
        ),
    ]
