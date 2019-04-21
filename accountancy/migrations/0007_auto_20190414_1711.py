# Generated by Django 2.2 on 2019-04-14 17:11

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('accountancy', '0006_accountancyproducts_created'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='accountancyproducts',
            name='unit',
        ),
        migrations.AddField(
            model_name='products',
            name='unit',
            field=models.CharField(blank=True, max_length=25),
        ),
        migrations.AlterField(
            model_name='products',
            name='vat',
            field=models.DecimalField(decimal_places=2, max_digits=4),
        ),
    ]
