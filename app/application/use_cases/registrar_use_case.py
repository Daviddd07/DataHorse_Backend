from datetime import date

from app.config.settings import ESTADO_INICIAL, ROL_USUARIO_ID
from app.domain.entities.Usuario import Usuario
from app.domain.exceptions import EmailAlreadyExistsError
from app.domain.ports.in_.registrar_usuario_port import RegistrarUsuarioComando, RegistrarUsuarioPort
from app.domain.ports.out.password_hasher_port import PasswordHasherPort
from app.domain.ports.out.usuario_repository_port import UsuarioRepositoryPort
from app.domain.services.validador_usuario import validar_registro

from app.domain.services.geocoding_service import GeocodingService

from datetime import date

from app.config.settings import ESTADO_INICIAL, ROL_USUARIO_ID
from app.domain.entities.Usuario import Usuario
from app.domain.exceptions import EmailAlreadyExistsError
from app.domain.ports.in_.registrar_usuario_port import RegistrarUsuarioComando, RegistrarUsuarioPort
from app.domain.ports.out.password_hasher_port import PasswordHasherPort
from app.domain.ports.out.usuario_repository_port import UsuarioRepositoryPort
from app.domain.services.validador_usuario import validar_registro


from app.domain.services.geocoding_service import GeocodingService


class RegistrarUseCase(RegistrarUsuarioPort):
    def __init__(self, repositorio: UsuarioRepositoryPort, hasher: PasswordHasherPort):
        self._repositorio = repositorio
        self._hasher = hasher

    def ejecutar(self, c: RegistrarUsuarioComando) -> Usuario:
        nombre = c.nombre.strip()
        correo = c.correo.strip().lower()
        telefono = (c.telefono or "").strip() or None
        ubicacion = (c.ubicacion or "").strip() or None

        validar_registro(nombre, correo, c.contrasena, telefono, ubicacion)

        if self._repositorio.find_by_email(correo):
            raise EmailAlreadyExistsError()

       
        ubicacion_lat = None
        ubicacion_lng = None
        ubicacion_texto = ubicacion
        ciudad = None
        departamento = None

        if ubicacion:
            geocoding = GeocodingService()
            datos_geo = geocoding.geocodificar(ubicacion)
            
            if datos_geo:
                ubicacion_lat = datos_geo["lat"]
                ubicacion_lng = datos_geo["lng"]
                ubicacion_texto = datos_geo["texto"]
                ciudad = datos_geo["ciudad"]
                departamento = datos_geo["departamento"]
       

        usuario = Usuario(
            id_usuario=None,
            id_rol=ROL_USUARIO_ID,
            nombre=nombre,
            correo=correo,
            contrasena=self._hasher.hashear(c.contrasena),
            telefono=telefono,
            ubicacion=ubicacion,
            
           
            ubicacion_lat=ubicacion_lat,
            ubicacion_lng=ubicacion_lng,
            ubicacion_texto=ubicacion_texto,
            ciudad=ciudad,
            departamento=departamento,
            
            fecha_registro=date.today(),
            estado=ESTADO_INICIAL,
        )
        return self._repositorio.create(usuario)
