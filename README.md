# DataHorse

## Descripción

DataHorse es una plataforma web orientada al sector equino que busca centralizar y facilitar el acceso a la información relacionada con caballos disponibles para reproducción.

Actualmente, la información sobre caballos, sus características, genealogía, ubicación, disponibilidad y datos relacionados se encuentra dispersa en diferentes medios como WhatsApp, Facebook, Instagram, contactos personales, documentos y registros.

DataHorse busca reunir esta información en una sola plataforma, permitiendo a los usuarios publicar y consultar caballos, realizar búsquedas y filtros, comparar ejemplares, consultar información de los animales y establecer contacto entre usuarios mediante un sistema de chat.

Además, el sistema contará con una funcionalidad básica de compatibilidad que permitirá priorizar caballos de acuerdo con diferentes características de la yegua registrada y del caballo candidato.

---

## Objetivo

Desarrollar una plataforma web que permita centralizar la información de caballos destinados a reproducción y facilitar la búsqueda, comparación y contacto entre usuarios interesados en servicios de reproducción equina.

El sistema busca facilitar el acceso a información organizada sobre los ejemplares y proporcionar herramientas que ayuden al usuario en el proceso de búsqueda y selección de caballos compatibles.

---

## Tecnologías utilizadas

### Lenguajes de programación

- Python
- TypeScript
- SQL
- HTML
- CSS

### Frameworks y tecnologías

- **FastAPI:** desarrollo de la API y backend.
- **Angular:** desarrollo del frontend.
- **Pydantic:** validación y estructuración de datos en el backend.
- **Arquitectura Hexagonal:** organización de la lógica y componentes del backend.

### Base de datos

- **MySQL:** almacenamiento y gestión de la información del sistema.
- **MySQL Workbench:** diseño y administración de la base de datos.

### Herramientas de desarrollo y gestión

- **Git:** control de versiones.
- **GitHub:** almacenamiento y colaboración sobre el código fuente.
- **Jira:** gestión del proyecto, backlog, historias de usuario y sprints.
- **Visual Studio Code:** entorno de desarrollo.

---

## Arquitectura

El backend de DataHorse utiliza una arquitectura monolítica basada en el enfoque de **Arquitectura Hexagonal**, también conocida como Ports and Adapters.

La estructura permite separar las reglas del negocio de elementos externos como la API y la base de datos.

De forma general, el sistema se organiza de la siguiente manera:

```
app/
├── domain/                 Reglas del negocio. No depende de FastAPI, SQLAlchemy ni de ningún servicio externo.
│   ├── entities/           Entidades (Usuario, Caballo, Conversacion, Resena...)
│   ├── services/           Validaciones y reglas puras (validador_usuario, datos_compatibilidad...)
│   ├── ports/in_/          Puertos de entrada: lo que la aplicación ofrece (un caso de uso por acción)
│   ├── ports/out/          Puertos de salida: lo que la aplicación necesita (repositorios, correo, IA...)
│   └── exceptions.py       Errores de negocio (sin códigos HTTP)
├── application/
│   └── use_cases/          Casos de uso: implementan los puertos de entrada usando los de salida
├── infraestructure/adaptadores/
│   ├── inbound/rest/       Controladores FastAPI (traducen HTTP ↔ casos de uso)
│   ├── inbound/websocket/  Chat y notificaciones en tiempo real
│   └── outbound/           Implementaciones de los puertos de salida:
│                           persistence (MySQL), security (JWT, Argon2, límite de intentos),
│                           correo (Mailjet), ia (Groq), geocoding (Nominatim),
│                           almacenamiento e imagenes (fotos en disco con Pillow)
└── config/
    ├── dependencies.py     Único lugar que conoce las clases concretas y las conecta con los puertos
    ├── settings.py         Constantes de la aplicación (límites, rutas, CORS...)
    └── validar_configuracion.py  Revisa los secretos del .env al arrancar
```

La dependencia siempre apunta hacia dentro: `infraestructure` → `application` → `domain`. Para cambiar MySQL, Groq o Mailjet por otra tecnología basta con escribir otro adaptador del mismo puerto y conectarlo en `config/dependencies.py`.

---

## Puesta en marcha

### Con Docker (recomendado)

El backend se levanta junto con MySQL, el frontend y Grafana desde el repositorio que une todo el proyecto (ver su README). La API queda en http://localhost:8000 y la documentación interactiva en http://localhost:8000/docs.

### En local, sin Docker

Requiere Python 3.12 (la misma versión del `Dockerfile`) y un MySQL accesible.

```bash
python -m venv venv
venv\Scripts\activate            # Windows  (Linux/macOS: source venv/bin/activate)
pip install -r requirements-dev.txt
uvicorn main:app --reload
```

### Variables de entorno (`.env`)

El archivo `.env` no se sube a git. Al arrancar, la API se niega a iniciar si falta alguna variable obligatoria o si un secreto tiene menos de 32 caracteres.

| Variable | Obligatoria | Para qué |
|---|---|---|
| `DB_HOST`, `DB_PORT`, `DB_USER`, `DB_PASSWORD`, `DB_NAME` | Sí | Conexión a MySQL (en Docker, `DB_HOST=db` y `DB_PORT=3306`) |
| `SECRET_KEY` | Sí (≥ 32) | Firma de los tokens de sesión (JWT) |
| `CODIGO_SECRET` | Sí (≥ 32) | Firma de los códigos de verificación de correo |
| `ALGORITHM`, `ACCESS_TOKEN_EXPIRE_MINUTES` | No | Algoritmo del JWT (`HS256`) y duración de la sesión (30 min) |
| `MAILJET_API_KEY`, `MAILJET_SECRET_KEY`, `MAILJET_SENDER_EMAIL`, `MAILJET_SENDER_NAME` | Para correos | Envío de códigos de verificación y recuperación |
| `GOOGLE_CLIENT_ID` | Para Google | Inicio de sesión con Google |
| `GROQ_API_KEY` | Para IA | Evaluación de compatibilidad |
| `ALLOWED_ORIGINS` | No | Orígenes CORS separados por comas (por defecto, `localhost:4200`) |
| `GRAFANA_URL` | No | Enlace al dashboard de logs desde el panel de administración |
| `ADMIN_CORREO`, `ADMIN_CONTRASENA`, `ADMIN_NOMBRE` | No | Crea el primer administrador al arrancar si ese correo no existe |

Para generar un secreto:

```bash
python -c "import secrets; print(secrets.token_urlsafe(48))"
```

---

## Pruebas

```bash
pip install -r requirements-dev.txt
python -m pytest -v --cov=app
```

Las pruebas usan dobles (mocks): no necesitan MySQL, Mailjet, Google ni Groq. En GitHub se ejecutan solas en cada push o pull request a `dev` (`.github/workflows/tests-backend.yml`).

---

## Dependencias

- `requirements.txt`: lo que necesita la API en producción, con versiones exactas para que cada build instale lo mismo.
- `requirements-dev.txt`: lo anterior más las herramientas de pruebas.

Para agregar un paquete: instálalo, comprueba que todo funciona y fija su versión exacta (`paquete==x.y.z`) en el archivo que corresponda.

---

## Seguridad

- Contraseñas guardadas con **Argon2**.
- Sesión en cookie con **JWT**.
- **Límite de intentos** en el login: 5 contraseñas incorrectas en 15 minutos bloquean ese correo hasta que caduque el fallo más antiguo (respuesta `429`).
- Los códigos de verificación tienen su propio límite de intentos y caducan.
- El contenedor corre con un usuario sin privilegios.

