# Generated by Django 2.0.9 on 2018-12-24 22:02

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    dependencies = [
        ('employee', '0008_auto_20181224_2151'),
    ]

    operations = [
        migrations.AlterField(
            model_name='employeehourlyrate',
            name='name',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='employee.Employee'),
        ),
    ]
