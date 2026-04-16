from django.db import migrations


def deduplicate_message_reactions(apps, schema_editor):
    MessageReaction = apps.get_model("bonding", "MessageReaction")
    seen_pairs = {}

    for reaction in MessageReaction.objects.order_by("message_id", "user_id", "-created_at", "-id"):
        pair = (reaction.message_id, reaction.user_id)
        if pair in seen_pairs:
            reaction.delete()
            continue
        seen_pairs[pair] = reaction.id


class Migration(migrations.Migration):

    dependencies = [
        ("bonding", "0006_profile_spotify_album_image_url_and_more"),
    ]

    operations = [
        migrations.RunPython(deduplicate_message_reactions, migrations.RunPython.noop),
        migrations.AlterUniqueTogether(
            name="messagereaction",
            unique_together={("message", "user")},
        ),
    ]
