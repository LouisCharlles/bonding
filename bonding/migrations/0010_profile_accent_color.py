from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ("bonding", "0009_message_client_request_id_photo_client_request_id_and_more"),
    ]

    operations = [
        migrations.AddField(
            model_name="profile",
            name="accent_color",
            field=models.CharField(default="#D71D29", max_length=7),
        ),
    ]
