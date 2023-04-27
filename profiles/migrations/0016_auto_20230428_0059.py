# Generated by Django 3.2.12 on 2023-04-27 19:29

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('profiles', '0015_auto_20230428_0058'),
    ]

    operations = [
        migrations.AlterField(
            model_name='artist',
            name='ctc_per_annum',
            field=models.CharField(default='', max_length=2000),
        ),
        migrations.AlterField(
            model_name='artist',
            name='max_budget',
            field=models.CharField(default='', max_length=2000),
        ),
        migrations.AlterField(
            model_name='artist',
            name='min_budget',
            field=models.CharField(default='', max_length=2000),
        ),
        migrations.AlterField(
            model_name='artist',
            name='relocation',
            field=models.CharField(default=False, max_length=2000, null=True),
        ),
    ]
