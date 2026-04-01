## Padel Stats Mobile App

App pensada para usar desde celular durante un partido de padel.

### Funcionalidad

- Flujo en 3 pantallas:
	- Setup previo (nombre de partido + nombres de los 4 jugadores)
	- Partido en juego (cancha 2x2 para cargar stats)
	- Resumen final (estadísticas globales y por set)
- Pantalla dividida en 4 cuadrantes (como cancha) para 4 jugadores.
- Botones por jugador para contar:
	- winner
	- errores no forzados
	- smash
	- smash winners
- Estadísticas separadas por set (1, 2 y 3).
- Guardado del set activo en Google Sheets.
- Guardado opcional del partido completo (sets 1, 2 y 3) en Google Sheets.

### Ejecutar local

1. Instalar dependencias:

```bash
uv sync
```

2. Ejecutar app:

```bash
uv run streamlit run main.py
```

3. Abrir URL local de Streamlit desde tu celular y desktop (misma red).

### Configuración Google Sheets

Se detectó el formato real de la hoja compartida por export CSV y la app guarda con esa estructura exacta.

Crear archivo `.streamlit/secrets.toml`:

```toml
google_sheet_id = "1tcyldrxv5lZl2CKaK4-1Me73IasGlLWTVK7cuup9HRY"
google_worksheet = "Stats" # opcional. Si no está, usa la primera pestaña.

[gcp_service_account]
type = "service_account"
project_id = "..."
private_key_id = "..."
private_key = "-----BEGIN PRIVATE KEY-----\n...\n-----END PRIVATE KEY-----\n"
client_email = "..."
client_id = "..."
token_uri = "https://oauth2.googleapis.com/token"
```

También tenés que compartir la hoja con el `client_email` de la service account.

### Columnas reales usadas en la hoja

La app guarda 1 fila por set (no por jugador), en este orden exacto:

1. Partido
2. Set
3. Jugador #1
4. Jugador #2
5. Jugador #3
6. Jugador #4
7. Winners #1
8. no forzados #1
9. Smash #1
10. Smash W #1
11. Winners #2
12. no forzados #2
13. Smash #2
14. Smash W #2
15. Winners #3
16. no forzados #3
17. Smash #3
18. Smash W #3
19. Winners #4
20. no forzados #4
21. Smash #4
22. Smash W #4

`Set` se guarda como `SET 1`, `SET 2` o `SET 3`.
