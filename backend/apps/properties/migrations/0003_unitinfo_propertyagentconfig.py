import django.db.models.deletion
from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('properties', '0002_property_owner_alter_property_agent_propertygroup'),
    ]

    operations = [
        migrations.CreateModel(
            name='UnitInfo',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('icon_type', models.CharField(
                    choices=[
                        ('wifi', 'WiFi'), ('alarm', 'Alarm'), ('garbage', 'Garbage'),
                        ('parking', 'Parking'), ('electricity', 'Electricity'), ('water', 'Water'),
                        ('gas', 'Gas'), ('intercom', 'Intercom'), ('laundry', 'Laundry'), ('other', 'Other'),
                    ],
                    default='other', max_length=20,
                )),
                ('label', models.CharField(max_length=100)),
                ('value', models.TextField()),
                ('sort_order', models.PositiveSmallIntegerField(default=0)),
                ('created_at', models.DateTimeField(auto_now_add=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('property', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, related_name='info_items', to='properties.property')),
                ('unit', models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.CASCADE, related_name='info_items', to='properties.unit')),
            ],
            options={'ordering': ['sort_order', 'label']},
        ),
        migrations.CreateModel(
            name='PropertyAgentConfig',
            fields=[
                ('id', models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('maintenance_playbook', models.TextField(blank=True, help_text='Instructions for how the AI agent should handle maintenance requests for this property')),
                ('ai_notes', models.TextField(blank=True, help_text='Additional context the AI agent should know about this property')),
                ('is_active', models.BooleanField(default=True)),
                ('updated_at', models.DateTimeField(auto_now=True)),
                ('property', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, related_name='agent_config', to='properties.property')),
            ],
        ),
    ]
