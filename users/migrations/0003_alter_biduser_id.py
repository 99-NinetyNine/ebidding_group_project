# Generated by Django 4.1.1 on 2022-10-08 16:17

from django.db import migrations, models
import uuid


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0002_biduser_bio_biduser_latitude_biduser_longitude_and_more'),
    ]

    operations = [
        migrations.AlterField(
            model_name='biduser',
            name='id',
            field=models.UUIDField(auto_created=True, default=uuid.uuid4, editable=False, primary_key=True, serialize=False),
        ),
    ]