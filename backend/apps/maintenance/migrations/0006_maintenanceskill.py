from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('maintenance', '0005_supplier_linked_user'),
    ]

    operations = [
        migrations.CreateModel(
            name='MaintenanceSkill',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.CharField(max_length=200)),
                ('trade', models.CharField(
                    choices=[
                        ('plumbing', 'Plumbing'), ('electrical', 'Electrical'), ('carpentry', 'Carpentry'),
                        ('painting', 'Painting'), ('hvac', 'HVAC / Air Con'), ('roofing', 'Roofing'),
                        ('general', 'General Maintenance'), ('appliance', 'Appliance Repair'),
                        ('pest', 'Pest Control'), ('other', 'Other'),
                    ],
                    default='general', max_length=20,
                )),
                ('difficulty', models.CharField(
                    choices=[('easy', 'Easy'), ('medium', 'Medium'), ('hard', 'Hard')],
                    default='medium', max_length=10,
                )),
                ('symptom_phrases', models.JSONField(default=list, help_text='List of phrases that indicate this issue, used for AI matching')),
                ('steps', models.JSONField(default=list, help_text='Ordered list of resolution steps')),
                ('notes', models.TextField(blank=True)),
                ('is_active', models.BooleanField(default=True)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
            ],
            options={'ordering': ['trade', 'name']},
        ),
    ]
