from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0011_unique_person_phone'),
    ]

    operations = [
        migrations.AddField(
            model_name='userinvite',
            name='cancelled_at',
            field=models.DateTimeField(blank=True, null=True),
        ),
    ]
