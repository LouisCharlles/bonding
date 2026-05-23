from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        ("bonding", "0015_remove_institution"),
    ]

    operations = [
        migrations.RemoveField(
            model_name="profile",
            name="allow_study_match",
        ),
    ]
