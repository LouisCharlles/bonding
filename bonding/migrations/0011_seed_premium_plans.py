from django.db import migrations

PLANS = [
    {
        "code": "plus",
        "name": "Bonding Plus",
        "description": "Veja quem curtiu você, mais curtidas por dia e rewinds ilimitados.",
        "price_monthly": "29.90",
        "likes_per_day": 50,
        "can_see_who_liked": True,
        "has_unlimited_swipes": False,
        "has_priority_boost": False,
        "has_video_calls": False,
        "is_active": True,
    },
    {
        "code": "gold",
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
]


def seed_plans(apps, schema_editor):
    PremiumPlan = apps.get_model("bonding", "PremiumPlan")
    for plan in PLANS:
        PremiumPlan.objects.get_or_create(code=plan["code"], defaults=plan)


def unseed_plans(apps, schema_editor):
    PremiumPlan = apps.get_model("bonding", "PremiumPlan")
    PremiumPlan.objects.filter(code__in=["plus", "gold"]).delete()


class Migration(migrations.Migration):
    dependencies = [
        ("bonding", "0010_profile_accent_color"),
    ]

    operations = [
        migrations.RunPython(seed_plans, reverse_code=unseed_plans),
    ]
