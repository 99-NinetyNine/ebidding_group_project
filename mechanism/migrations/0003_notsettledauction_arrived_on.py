# Generated by Django 4.1.6 on 2023-03-08 16:55

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('mechanism', '0002_liarbidder'),
    ]

    operations = [
        migrations.AddField(
            model_name='notsettledauction',
            name='arrived_on',
            field=models.DateTimeField(auto_now=True, null=True),
        ),
    ]
