from rest_framework import generics, status, permissions
from rest_framework.response import Response
from geopy.geocoders import Nominatim
from ..models import Location
from ..serial import LocationSerializer

geolocator = Nominatim(user_agent='bonding')

class LocationCreateOrRetrieveView(generics.GenericAPIView):
    """
    View para buscar uma localização existente ou criar uma nova
    com base nas coordenadas de latitude e longitude.
    """
    queryset = Location.objects.all()
    serializer_class = LocationSerializer
    permission_classes = [permissions.IsAuthenticated]

    def post(self,request,*args,**kwargs):
        latitude = request.data.get('latitude')
        longitude = request.data.get('longitude')

        if not latitude or not longitude:
            return Response({'error':'Latitude e Longitude são obrigatórios'},status=status.HTTP_400_BAD_REQUEST)
        try:
            #Conversão das coordenadas em endereço(geocoding reverso)
            location_data = geolocator.reverse(f"{latitude}, {longitude}",language='pt-BR')

            if not location_data:
                return Response({'error':"Não foi possivel encontrar um endereço para estas coordenadas."},status=status.HTTP_400_BAD_REQUEST)
            
            address = location_data.raw['address']

            city = address.get('city') or address.get('town') or address.get('village')

            state = address.get("state")

            country = address.get('country')

            if not city or not state or not country:
                return Response({'error': 'Endereço incompleto. Cidade, estado ou país não encontrados.'}, status=status.HTTP_400_BAD_REQUEST)
            
            location, created = Location.objects.get_or_create(
                city=city,
                state=state,
                country=country,
                defaults={'latitude':latitude, 'longitude':longitude}
            )

            if not created and (location.latitude != latitude or location.longitude != longitude):
                location.latitude = latitude
                location.longitude = longitude
                location.save()

            serializer = self.get_serializer(location)
            return Response(serializer.data, status=status.HTTP_201_CREATED)
        except Exception as e:
            return Response({'error': str(e)}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)