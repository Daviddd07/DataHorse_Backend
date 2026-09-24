class RegistroError(Exception):
    """Base para los errores del registro."""


class DatosInvalidosError(RegistroError):
    def __init__(self, campo: str, mensaje: str):
        super().__init__(mensaje)
        self.campo = campo
        self.mensaje = mensaje


class CorreoYaRegistradoError(RegistroError):
    pass

class InvalidCredentialsError(Exception):
    """Correo o contraseña incorrectos."""
# Alias: los archivos que importan EmailAlreadyExistsError siguen funcionando.
EmailAlreadyExistsError = CorreoYaRegistradoError