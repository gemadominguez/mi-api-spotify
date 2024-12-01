from fastapi import FastAPI, HTTPException
from pydantic import BaseModel, EmailStr, constr
import json

app = FastAPI(
    title="API de Usuarios y Música (Spotify)",
    description="Esta API gestiona usuarios y sus preferencias musicales, y también permite obtener información desde Spotify.",
    version="1.0.0"
)

# Modelo de datos del usuario (ModelUser)
class ModelUser(BaseModel):
    name: str
    email: EmailStr  # Esto valida que el correo tenga el formato adecuado (ej. usuario@dominio.com)

#Modelo de datos para spotify
class ModelSpotify(BaseModel):
    spotify_artists: list = [] # Es una lista que almacenará los IDs de los artistas favoritos del usuario.
    spotify_songs: list = []# Lista para guardar los IDs de las canciones favoritas


# Para cargar y guardar en archivo JSON
def load_base_users():
    try:
        with open("users.json", "r") as file:
            data = json.load(file)
            # Convertir las claves de string a enteros
            return {int(key): value for key, value in data.items()}
    except FileNotFoundError:
        return {}  # Si el archivo no existe, devolvemos un diccionario vacío

def save_base_users(base_users):
    with open("users.json", "w") as file:
        json.dump(base_users, file, indent=4)

# CREAR USUARIO = POST
@app.post("/api/users/")
def create_data_user(data_user: ModelUser):  
    base_users = load_base_users()  # Cargamos los usuarios actuales del archivo JSON

    # Comprobamos si ya existe un usuario con el mismo nombre y email
    for existing_user in base_users.values():  # Recorremos los usuarios existentes
        if existing_user["name"] == data_user.name and existing_user["email"] == data_user.email:
            raise HTTPException(status_code=400, detail={"error": "El usuario con ese nombre y email ya existe"})

    # Validamos que el nombre y el email no estén vacíos
    if not data_user.name or not data_user.email:  # Si el nombre o el email están vacíos
        raise HTTPException(status_code=400, detail={"error": "Se necesita un nombre y un email válidos"})

    # Generar un nuevo ID automáticamente
    new_id = max(base_users.keys(), default=0) + 1

    # Crear el usuario con el nuevo ID
    base_users[new_id] = {"id": new_id, "name": data_user.name, "email": data_user.email}

    save_base_users(base_users)  # Guardamos el diccionario actualizado en el archivo JSON
    #return base_users[new_id]  # Devolvemos el usuario creado
    return {"user": base_users[new_id]}  # Devolver el usuario dentro de un diccionario con una clave 'user'

# LEER BASE DE DATOS DE USUARIOS = GET
@app.get("/api/users/")
def get_base_users():
    base_users = load_base_users()  # Cargamos los usuarios actuales del archivo JSON
    #return base_users  # Devolvemos todos los usuarios
    return {"users": base_users}  # Asegúrate de envolver en un diccionario

# ACTUALIZAR USUARIO = PUT
@app.put("/api/users/{user_id}")
def update_data_user(user_id: int, data_user: ModelUser):
    base_users = load_base_users()  # Cargamos los usuarios actuales del archivo JSON
    if user_id not in base_users:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")  # Si el usuario no existe, lanzamos una excepción

    base_users[user_id] = data_user.dict()  # Actualizamos el usuario con el nuevo contenido
    save_base_users(base_users)  # Guardamos el archivo JSON actualizado
    #return base_users[user_id]  # Devolvemos el usuario actualizado
    return {"user": base_users[user_id]}

# ELIMINAR USUARIO = DELETE
@app.delete("/api/users/{user_id}")
def delete_data_user(user_id: int):
    base_users = load_base_users()  # Cargamos los usuarios desde el archivo JSON
    if user_id not in base_users:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")  # Si el usuario no existe, lanzamos un error 404

    del base_users[user_id]  # Eliminamos al usuario por su ID

    # Reordenar los IDs para que sean consecutivos
    reordered_base_users = {}
    for new_id, user in enumerate(base_users.values(), start=1):
        user["id"] = new_id  # Actualizamos el ID del usuario
        reordered_base_users[new_id] = user

    save_base_users(reordered_base_users)  # Guardamos los usuarios reordenados en el diccionario

    return {"detail": "Usuario eliminado correctamente"}



#-------------- API EXTERNA -------------------

# Importar las librerías de Spotify
import spotipy
from spotipy.oauth2 import SpotifyClientCredentials
import os
from dotenv import load_dotenv

# Cargar las variables de entorno desde el archivo .env
load_dotenv()

# Recuperar las credenciales de Spotify
CLIENT_ID = os.getenv("SPOTIFY_CLIENT_ID")
CLIENT_SECRET = os.getenv("SPOTIFY_CLIENT_SECRET")

# Verificar que las credenciales existan
if not CLIENT_ID or not CLIENT_SECRET:
    raise Exception("Faltan las credenciales de Spotify en las variables de entorno.")

# Configurar la autenticación de Spotify
auth_manager = SpotifyClientCredentials(client_id=CLIENT_ID, client_secret=CLIENT_SECRET)

# Crear la instancia de Spotify usando el manager de autenticación
api_spotify = spotipy.Spotify(auth_manager=auth_manager)

# Ahora puedes usar la variable `spotify` para interactuar con la API de Spotify


#Para obtener las 5 canciones más populares al buscar al artista
def obtener_top_canciones_artista(artist_id, country="US"):
    """
    Devuelve las top 5 canciones de un artista según su ID de Spotify.
    """
    try:
        # Obtener las canciones más populares del artista
        top_tracks = api_spotify.artist_top_tracks(artist_id, country=country)
        return [
            {
                "titulo": track['name'],
                "url": track['external_urls']['spotify']
            }
            for track in top_tracks['tracks'][:5]  # Selecciona las 5 primeras
        ]
    except Exception as e:
        return []



#Buscar un artista
def obtener_artista_spotify(nombre_artista):
    # Buscar al artista en Spotify
    resultado = api_spotify.search(q=nombre_artista, type='artist', limit=1)

    # Obtener el primer resultado (el más relevante)
    artista = resultado['artists']['items'][0] if resultado['artists']['items'] else None

    # Si se encontró el artista, devolver los datos relevantes
    if artista:
        top_canciones = obtener_top_canciones_artista(artista['id'])
        return {
            "nombre": artista['name'],
            "id": artista['id'],
            "popularidad": artista['popularity'],
            "url": artista['external_urls']['spotify'],
            "top_canciones": top_canciones
        }
    else:
        return None


#Buscar una canción
def obtener_cancion_spotify(nombre_cancion):
    # Buscar la canción en Spotify
    resultado = api_spotify.search(q=nombre_cancion, type='track', limit=1)

    # Obtener el primer resultado (la canción más relevante)
    cancion = resultado['tracks']['items'][0] if resultado['tracks']['items'] else None

    # Si se encontró la canción, devolver los datos relevantes
    if cancion:
        return {
            "titulo": cancion['name'],
            "artista": cancion['artists'][0]['name'],
            "id": cancion['id'],
            "url": cancion['external_urls']['spotify']
        }
    else:
        return None


#<---------------- GET (spotify) ------------------>
#Mi api busca un artista en spotify
@app.get("/api/spotify/artist/{nombre_artista}")
def obtener_artista_api(nombre_artista: str):
    artista = obtener_artista_spotify(nombre_artista)
    if artista: 
        return artista
    else:
         raise HTTPException(status_code=404, detail="Artista no encontrado")


#Mi api busca una canción en spotify
@app.get("/api/spotify/song/{nombre_cancion}")
def obtener_cancion_api(nombre_cancion: str):
    cancion = obtener_cancion_spotify(nombre_cancion)
    if cancion:
        return cancion
    else:
        raise HTTPException(status_code=404, detail="Canción no encontrada")
    

#<---------------- PUT (usuario-spotify) ------------------>
# Mi API agrega un artista a las preferencias musicales de un usuario
@app.put("/api/users/{user_id}/add-favorite-artist")
def agregar_artista_favorito_al_usuario(user_id: int, artist: ModelSpotify):
    base_users = load_base_users()  # Cargamos los usuarios actuales del archivo JSON

    # Verificamos que el usuario exista
    if user_id not in base_users:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")

    # Si el usuario no tiene una lista de artistas favoritos, la creamos
    if 'artistas_favoritos' not in base_users[user_id]:
        base_users[user_id]['artistas_favoritos'] = []

    # Filtramos los nuevos artistas que no estén ya en la lista
    new_artists = [
        artist_id for artist_id in artist.spotify_artists
        if artist_id not in base_users[user_id]["artistas_favoritos"]
    ]

    # Si no hay artistas nuevos para agregar, devolvemos un mensaje de error
    if not new_artists:
        raise HTTPException(
            status_code=400,
            detail="Todos los artistas proporcionados ya están en la lista de favoritos"
        )

    # Agregamos solo los nuevos artistas a la lista
    base_users[user_id]["artistas_favoritos"].extend(new_artists)

    save_base_users(base_users)  # Guardamos los cambios en el archivo JSON

    return {
        "detail": f"Artistas {new_artists} agregados a favoritos",
        "user": base_users[user_id]  # Devolvemos el usuario actualizado
    }


#Mi api añade las canciones favoritas del usuario
@app.put('/api/users/{user_id}/add_favorite_songs')
def agregar_cancion_favorita_al_usuario(user_id: int, song: ModelSpotify):
    base_users = load_base_users()

    # Verificar si el usuario existe
    if user_id not in base_users: 
        raise HTTPException(status_code=404, detail="Usuario no encontrado")

    # Inicializar la lista de canciones favoritas si no existe
    if 'canciones_favoritas' not in base_users[user_id]:
        base_users[user_id]['canciones_favoritas'] = []

    # Validar que `spotify_songs` sea una lista
    if not isinstance(song.spotify_songs, list):
        raise HTTPException(status_code=400, detail="El campo 'spotify_songs' debe ser una lista")

    # Evitar duplicados al agregar canciones
    agregar_cancion = [cancion for cancion in song.spotify_songs 
                       if cancion not in base_users[user_id]["canciones_favoritas"]]
    
    # Si no hay canciones nuevas para agregar, lanzamos un error
    if not agregar_cancion:
        raise HTTPException(status_code=400, detail="La canción ya están en la lista de favoritos")

    # Agregamos la nueva canción a la lista de favoritos
    base_users[user_id]["canciones_favoritas"].extend(agregar_cancion)

    # Guardar los cambios en el archivo JSON
    save_base_users(base_users)
    return {"detail": f"Canciones {agregar_cancion} agregadas a favoritos", 
            "user": base_users[user_id]}


#<---------------- GET  (usuario-spotify) ------------------>

#Mi api pregunta el artista favorito del usuario
@app.get("/api/users/{user_id}/favorite-artist")
def obtener_artistas_favoritos_del_usuario(user_id: int):
    base_users = load_base_users()  # Cargamos los usuarios actuales del archivo JSON

    # Verificamos que el usuario exista
    if user_id not in base_users:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")

    # Verificamos si el usuario tiene artistas favoritos
    if 'artistas_favoritos' not in base_users[user_id]:
        raise HTTPException(status_code=404, detail="El usuario no tiene artistas favoritos")

    # Devolvemos los artistas favoritos del usuario
    return {
        "name" : base_users[user_id]["name"],
        "artistas_favoritos": base_users[user_id]["artistas_favoritos"]
    }



# Mi api consulta las canciones favoritas del usuario
@app.get("/api/users/{user_id}/favorite-songs")
def obtener_canciones_favoritas_del_usuario(user_id: int):
    base_users = load_base_users()  # Cargamos los usuarios actuales del archivo JSON

    # Verificamos que el usuario exista
    if user_id not in base_users:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")

    # Inicializar error si la lista de canciones favoritas no existe
    if 'canciones_favoritas' not in base_users[user_id]:
         raise HTTPException(status_code=404, detail="El usuario no tiene canciones favoritas")


    # Devolvemos las canciones favoritas del usuario
    return {
        "name" : base_users[user_id]["name"],
        "canciones_favoritas": base_users[user_id]["canciones_favoritas"]
    }



#<---------------- DELETE (usuario - spotify) ------------------>


#Mi api borra un artista favorito del usuario
@app.delete("/api/users/{user_id}/delete-favorite-artist")
def eliminar_artista_favorito(user_id: int, artist_name: str):
    base_users = load_base_users() 
    # Verificar si el usuario existe
    if user_id not in base_users:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")

    # Verificar si tiene una lista de artistas favoritos
    if 'artistas_favoritos' not in base_users[user_id]:
        raise HTTPException(status_code=404, detail="El usuario no tiene artistas favoritos")

    # Verificar si el artista está en la lista de favoritos
    if artist_name not in base_users[user_id]['artistas_favoritos']:
        raise HTTPException(status_code=404, detail="El artista no está en la lista de favoritos")
    
    # Eliminar el artista de la lista
    base_users[user_id]['artistas_favoritos'].remove(artist_name)

    # Guardar los cambios en el archivo JSON
    save_base_users(base_users)

    return {
        "detail": f"Artista {artist_name} eliminado de la lista de favoritos",
        "user": base_users[user_id]  # Devolver el usuario actualizado
    }


#Mi api borra una canción favorito del usuario
@app.delete("/api/users/{user_id}/delete-favorite-song")
def eliminar_cancion_favorita(user_id: int, song_name: str):
    base_users = load_base_users() 
    # Verificar si el usuario existe
    if user_id not in base_users:
        raise HTTPException(status_code=404, detail="Usuario no encontrado")

    # Verificar si tiene una lista de canciones favorita
    if 'canciones_favoritas' not in base_users[user_id]:
        raise HTTPException(status_code=404, detail="El usuario no tiene canciones favoritas")

    # Verificar si la canción está en la lista de favoritos
    if song_name not in base_users[user_id]['canciones_favoritas']:
        raise HTTPException(status_code=404, detail="La canción no está en la lista de favoritos")
    
    # Eliminar la canción de la lista
    base_users[user_id]['canciones_favoritas'].remove(song_name)

    # Guardar los cambios en el archivo JSON
    save_base_users(base_users)

    return {
        "detail": f"La canción {song_name} ha sido eliminada de la lista de favoritos",
        "user": base_users[user_id]  # Devolver el usuario actualizado
    }