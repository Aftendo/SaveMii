# Generated by Django 4.1.7 on 2023-10-07 14:41

from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ('miiapp', '0005_alter_nintendonetworkid_archived_on_and_more'),
    ]

    operations = [
        migrations.RenameModel(
            old_name='BlockList',
            new_name='BlockedNNID',
        ),
        migrations.AlterModelOptions(
            name='blockednnid',
            options={'verbose_name': 'Blocked NNID', 'verbose_name_plural': 'Blocked NNID'},
        ),
    ]