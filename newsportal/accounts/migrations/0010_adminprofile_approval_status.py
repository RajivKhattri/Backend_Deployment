# Generated by Django 5.1.7 on 2025-05-18 15:04

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('accounts', '0009_rolechangerequest'),
    ]

    operations = [
        migrations.AddField(
            model_name='adminprofile',
            name='approval_status',
            field=models.CharField(choices=[('pending', 'Pending'), ('approved', 'Approved'), ('rejected', 'Rejected')], default='pending', max_length=10),
        ),
    ]
