import os

# La clave se leerá preferiblemente de la caché interna (client_storage) o variables de entorno
GROQ_API_KEY = os.environ.get("GROQ_API_KEY", "")
