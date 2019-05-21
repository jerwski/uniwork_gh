# Generated by Django 2.2 on 2019-05-12 17:58

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
    ]

    operations = [
        migrations.CreateModel(
            name='Company',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('company', models.CharField(max_length=240)),
                ('nip', models.CharField(max_length=13)),
                ('street', models.CharField(blank=True, max_length=100)),
                ('city', models.CharField(blank=True, max_length=100)),
                ('postal', models.CharField(blank=True, max_length=10, verbose_name='Postal code')),
                ('phone', models.CharField(blank=True, max_length=20)),
                ('account', models.CharField(blank=True, max_length=34, verbose_name='Contrary account')),
                ('status', models.IntegerField(default=1)),
                ('created', models.DateTimeField(auto_now_add=True)),
                ('updated', models.DateTimeField(auto_now=True)),
            ],
            options={
                'ordering': ['company'],
            },
        ),
        migrations.CreateModel(
            name='CashRegister',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('created', models.DateTimeField(auto_now_add=True)),
                ('symbol', models.CharField(max_length=200)),
                ('contents', models.CharField(max_length=250)),
                ('income', models.FloatField(default=0.0)),
                ('expenditure', models.FloatField(default=0.0)),
                ('cashaccept', models.SmallIntegerField(blank=True, null=True)),
                ('company', models.ForeignKey(on_delete=django.db.models.deletion.DO_NOTHING, to='cashregister.Company')),
            ],
            options={
                'ordering': ['company', 'created'],
            },
        ),
    ]
