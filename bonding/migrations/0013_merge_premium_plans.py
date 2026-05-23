from django.db import migrations


def merge_plans(apps, schema_editor):
    PremiumPlan = apps.get_model("bonding", "PremiumPlan")
    Profile = apps.get_model("bonding", "Profile")

    PremiumPlan.objects.filter(code="gold").delete()

    PremiumPlan.objects.filter(code="plus").update(
        name="Bonding Premium",
        description="Veja quem curtiu você, swipes ilimitados, rewinds ilimitados e videochamadas.",
        price_monthly="29.90",
        likes_per_day=9999,
        can_see_who_liked=True,
        has_unlimited_swipes=True,
        has_priority_boost=True,
        has_video_calls=True,
        is_active=True,
    )

    Profile.objects.filter(premium_tier="gold").update(premium_tier="plus")


def reverse_merge(apps, schema_editor):
    PremiumPlan = apps.get_model("bonding", "PremiumPlan")

    PremiumPlan.objects.filter(code="plus").update(
        name="Bonding Plus",
        description="Veja quem curtiu você, mais curtidas por dia e rewinds ilimitados.",
        price_monthly="29.90",
        likes_per_day=50,
        can_see_who_liked=True,
        has_unlimited_swipes=False,
        has_priority_boost=False,
        has_video_calls=False,
    )

    PremiumPlan.objects.get_or_create(
        code="gold",
        defaults={
            "name": "Bonding Gold",
            "description": "Swipes ilimitados, prioridade no Discover e videochamadas desbloqueadas.",
            "price_monthly": "59.90",
            "likes_per_day": 9999,
            "can_see_who_liked": True,
            "has_unlimited_swipes": True,
            "has_priority_boost": True,
            "has_video_calls": True,
            "is_active": True,
        },
    )


class Migration(migrations.Migration):
    dependencies = [
        ("bonding", "0012_message_date_suggestion"),
    ]

    operations = [
        migrations.RunPython(merge_plans, reverse_code=reverse_merge),
    ]
