from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('leases', '0009_reusable_clause'),
    ]

    operations = [
        migrations.AddField(
            model_name='leasetemplate',
            name='header_html',
            field=models.TextField(blank=True, default='', help_text='HTML shown at the top of every page (logo, title, etc.)'),
        ),
        migrations.AddField(
            model_name='leasetemplate',
            name='footer_html',
            field=models.TextField(blank=True, default='', help_text='HTML shown at the bottom of every page (company name, page number)'),
        ),
    ]
