# Generated by Django 5.1 on 2024-08-21 04:47

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('blog_generator', '0001_initial'),
    ]

    operations = [
        migrations.AlterField(
            model_name='blogpost',
            name='id',
            field=models.BigAutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID'),
        ),
    ]