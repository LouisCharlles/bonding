from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("bonding", "0007_alter_messagereaction_unique_together"),
    ]

    operations = [
        migrations.AddField(
            model_name="profile",
            name="last_seen",
            field=models.DateTimeField(blank=True, null=True),
        ),
    ]
