# Generated by Django 4.2.7 on 2024-02-15 06:02

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('transactions', '0003_remove_transaction_borrowed_book_and_more'),
    ]

    operations = [
        migrations.RemoveField(
            model_name='transaction',
            name='borrow_timestamp',
        ),
        migrations.RemoveField(
            model_name='transaction',
            name='return_timestamp',
        ),
        migrations.AddField(
            model_name='transaction',
            name='transaction_timestamp',
            field=models.DateTimeField(auto_now_add=True, null=True),
        ),
    ]
