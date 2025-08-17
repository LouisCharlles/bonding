from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from rest_framework import serializers
from django.core.validators import validate_email
from django.core.exceptions import ValidationError
from django.contrib.auth.password_validation import validate_password
from .models import User, Profile, Interest, Preference, Location, Connection, Message, Conversation,Photo
from rest_framework.validators import UniqueValidator

class CustomTokenObtainPairSerializer(TokenObtainPairSerializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True)
    def __init__(self,*args,**kwargs):
        super().__init__(*args,**kwargs)

        self.fields.pop('username',None)
    def validate(self, attrs):
        attrs['username'] = attrs.get('email')
        data = super().validate(attrs)
        user = self.user
        data['user_id'] = user.id
        return data

class LocationSerializer(serializers.ModelSerializer):
    class Meta:
        model = Location
        fields = '__all__'
        read_only_fields = ['id']

class InterestSerializer(serializers.ModelSerializer):
    class Meta:
        model = Interest
        fields = '__all__'
        read_only_fields = ['id']

class PreferenceSerializer(serializers.ModelSerializer):
    class Meta:
        model = Preference
        fields = '__all__'
        read_only_fields = ['id']

class UserSerializer(serializers.ModelSerializer):
    # Garante que o e-mail é único e tem formato válido
    email = serializers.EmailField(
        required=True,
        validators=[UniqueValidator(queryset=User.objects.all())]
    )
    
    # Campo de senha para ser escrito, mas não lido pela API
    password = serializers.CharField(
        write_only=True,
        required=True,
        validators=[validate_password]
    )

    class Meta:
        model = User
        fields = ('id', 'email', 'password')
        # Define a senha como "somente para escrita"
        extra_kwargs = {
            'password': {'write_only': True}
        }
    
    def create(self, validated_data):
        # Cria um novo usuário com senha criptografada
        user = User.objects.create_user(
            email=validated_data['email'],
            password=validated_data['password']
        )
        return user
    
    def update(self, instance, validated_data):
        # Lógica de atualização, com atenção especial à senha
        instance.email = validated_data.get('email', instance.email)
        
        # Se a senha for fornecida, ela deve ser definida com set_password
        password = validated_data.get('password')
        if password:
            instance.set_password(password)
        
        instance.save()
        return instance
    
class PhotoSerializer(serializers.ModelSerializer):
    class Meta:
        model = Photo
        fields = ['id', 'image','description', 'order', 'updated_at']
        read_only_fields = ['id']
class ProfileSerializer(serializers.ModelSerializer):
    photos = PhotoSerializer(many=True)

    location = LocationSerializer()

    interests = InterestSerializer(many=True)

    preferences = PreferenceSerializer(many=True)

    location_id = serializers.PrimaryKeyRelatedField(
        queryset=Location.objects.all(), source='location', write_only=True
    )
    interests_ids = serializers.PrimaryKeyRelatedField(
        queryset=Interest.objects.all(), many=True, source='interests', write_only=True
    )
    preferences_ids = serializers.PrimaryKeyRelatedField(
        queryset=Preference.objects.all(), many=True, source='preferences', write_only=True
    )

    uuid = serializers.UUIDField(read_only=True)

    class Meta:
        model = Profile
        fields = ['uuid', 'user', 'name','age','bio', 'location','gender','course', 'sexual_orientation', 'interests', 'preferences', 'photos','location_id', 'interests_ids', 'preferences_ids']
        read_only_fields = ['uuid', 'user','name','age']

    def create(self, validated_data):
        # Lógica de criação para handle Many-to-Many fields
        interests_data = validated_data.pop('interests', [])
        preferences_data = validated_data.pop('preferences', [])
        
        profile = Profile.objects.create(**validated_data)
        
        # Adiciona os objetos de Many-to-Many ao perfil
        profile.interests.set(interests_data)
        profile.preferences.set(preferences_data)
        
        return profile

    def update(self, instance, validated_data):
        # Lógica de atualização para handle Many-to-Many fields
        interests_data = validated_data.pop('interests', None)
        preferences_data = validated_data.pop('preferences', None)
        
        # Atualiza os outros campos do perfil
        for attr, value in validated_data.items():
            setattr(instance, attr, value)
        
        # Atualiza os campos de Many-to-Many se eles foram enviados
        if interests_data is not None:
            instance.interests.set(interests_data)
        if preferences_data is not None:
            instance.preferences.set(preferences_data)
        
        instance.save()
        return instance

class ConnectionSerializer(serializers.ModelSerializer):
    from_user = serializers.SlugRelatedField(
        queryset=User.objects.all(),
        slug_field='email'
    )
    to_user = serializers.SlugRelatedField(
        queryset=User.objects.all(),
        slug_field='email'
    )

    class Meta:
        model = Connection
        fields = ['id', 'from_user', 'to_user', 'status','created_at']
        read_only_fields = ['id','created_at']

class MessageSerializer(serializers.ModelSerializer):
    sender = serializers.SlugRelatedField(
        queryset=User.objects.all(),
        slug_field='email'
    )

    class Meta:
        model = Message
        fields = ['id', 'conversation', 'sender', 'content', 'created_at', 'read']
        read_only_fields = ['id', 'created_at','conversation']

class ConversationSerializer(serializers.ModelSerializer):
    messages = MessageSerializer(many=True, read_only=True)

    user1 = serializers.SlugRelatedField(
        queryset=User.objects.all(),
        slug_field='email'
    )

    user2 = serializers.SlugRelatedField(
        queryset=User.objects.all(),
        slug_field='email'
    )

    class Meta:
        model = Conversation
        fields = ['id', 'user1', 'user2', 'created_at','last_message','messages']
        read_only_fields = ['id', 'created_at','last_message']