from django.db import models
from .user import User
from .interest import Interest
from .preference import Preference
import uuid
class Profile(models.Model):
    choices_gender=[
            ('Masculino', 'Masculino'), 
            ('Feminino', 'Feminino'),
            ('Nao-binario', 'Não-binário'),
            ('Genero Fluido', 'Gênero Fluido')
        ]

    choices_orientation = [
        ('Heterossexual', 'Heterossexual'),
        ('Homossexual', 'Homossexual'),
        ('Bissexual', 'Bissexual'),
        ('Assexual', 'Assexual'),
        ('Pansexual', 'Pansexual')
    ]
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name='profile')

    uuid = models.UUIDField(default=uuid.uuid4, editable=False, unique=True)
    name = models.CharField(max_length=100)

    age = models.PositiveIntegerField()

    bio = models.TextField(blank=True, null=True)

    location = models.ForeignKey('Location',on_delete=models.SET_NULL, blank=True, null=True)

    gender = models.CharField(max_length=20,choices=choices_gender)

    sexual_orientation = models.CharField(max_length=20,choices=choices_orientation)
    course = models.CharField(max_length=100)

    interests = models.ManyToManyField(Interest,related_name='perfis', blank=True)

    preferences = models.ManyToManyField(Preference,related_name='perfis_com_preferencia', blank=True)

    def __str__(self):
        return f"Profile of {self.name}"
