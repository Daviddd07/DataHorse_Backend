"""Errores de negocio. No conocen HTTP: el adaptador REST decide el código de estado."""


class DominioError(Exception):
    mensaje_por_defecto = "Error de negocio"

    def __init__(self, mensaje: str | None = None):
        self.mensaje = mensaje or self.mensaje_por_defecto
        super().__init__(self.mensaje)


class RecursoNoEncontradoError(DominioError):
    mensaje_por_defecto = "Recurso no encontrado"


class NoAutenticadoError(DominioError):
    mensaje_por_defecto = "No autenticado"


class AccesoDenegadoError(DominioError):
    mensaje_por_defecto = "Acceso denegado"


class ConflictoError(DominioError):
    mensaje_por_defecto = "Conflicto con el estado actual del recurso"


class SolicitudInvalidaError(DominioError):
    mensaje_por_defecto = "Solicitud inválida"


class DemasiadosIntentosError(DominioError):
    mensaje_por_defecto = "Demasiados intentos"


class ServicioExternoError(DominioError):
    mensaje_por_defecto = "Falló un servicio externo"


class ErrorInternoError(DominioError):
    mensaje_por_defecto = "Ocurrió un error interno"


class ConfiguracionError(ErrorInternoError):
    mensaje_por_defecto = "Configuración incompleta"


class RegistroError(DominioError):
    """Base para los errores del registro."""


class DatosInvalidosError(RegistroError):
    def __init__(self, campo: str, mensaje: str):
        super().__init__(mensaje)
        self.campo = campo


class CorreoYaRegistradoError(RegistroError, ConflictoError):
    mensaje_por_defecto = "Ese correo ya está registrado"


class InvalidCredentialsError(NoAutenticadoError):
    mensaje_por_defecto = "Correo o contraseña incorrectos"


# Alias: los archivos que importan EmailAlreadyExistsError siguen funcionando.
EmailAlreadyExistsError = CorreoYaRegistradoError
