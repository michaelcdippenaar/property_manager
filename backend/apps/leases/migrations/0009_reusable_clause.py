from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('leases', '0008_leasetemplate_content_html'),
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='ReusableClause',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('title', models.CharField(max_length=200)),
                ('category', models.CharField(
                    choices=[
                        ('parties', 'Parties'), ('premises', 'Premises'),
                        ('financial', 'Financial'), ('utilities', 'Utilities'),
                        ('legal', 'Legal / Compliance'), ('signatures', 'Signatures'),
                        ('general', 'General'),
                    ],
                    default='general', max_length=30,
                )),
                ('html', models.TextField(help_text='HTML content using allowed Tiptap tags')),
                ('tags', models.JSONField(blank=True, default=list)),
                ('use_count', models.PositiveIntegerField(default=0)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('created_by', models.ForeignKey(
                    on_delete=django.db.models.deletion.CASCADE,
                    related_name='clauses',
                    to=settings.AUTH_USER_MODEL,
                )),
                ('source_templates', models.ManyToManyField(
                    blank=True,
                    related_name='clauses',
                    to='leases.leasetemplate',
                )),
            ],
            options={'ordering': ['-use_count', '-created_at']},
        ),
    ]
