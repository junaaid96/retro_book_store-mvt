# Generated by Django 4.2.7 on 2024-02-15 06:29

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('transactions', '0004_remove_transaction_borrow_timestamp_and_more'),
    ]

    operations = [
        migrations.AlterModelOptions(
            name='transaction',
            options={'ordering': ['-timestamp']},
        ),
        migrations.RenameField(
            model_name='transaction',
            old_name='transaction_timestamp',
            new_name='timestamp',
        ),
    ]