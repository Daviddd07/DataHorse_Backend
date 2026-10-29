from datetime import datetime, timedelta
from unittest.mock import Mock

import pytest

from app.application.services.codigo_verificacion_service import (
    CODIGO_EXPIRA_MINUTOS,
    MAX_INTENTOS_CODIGO,
    CodigoVerificacionService,
)
from app.application.use_cases.cuenta_use_cases import (
    AutenticarConGoogleUseCase,
    IniciarSesionUseCase,
    ObtenerUsuarioActualUseCase,
    ReenviarCodigoUseCase,
    RegistrarCuentaUseCase,
    RestablecerContrasenaUseCase,
    SolicitarRecuperacionUseCase,
    VerificarCorreoUseCase,
)
from app.domain.entities.Usuario import Usuario
from app.domain.entities.codigo_verificacion import CodigoVerificacion
from app.domain.exceptions import (
    AccesoDenegadoError,
    ConfiguracionError,
    ConflictoError,
    CorreoYaRegistradoError,
    DatosInvalidosError,
    DemasiadosIntentosError,
    ErrorInternoError,
    InvalidCredentialsError,
    NoAutenticadoError,
    RecursoNoEncontradoError,
    ServicioExternoError,
    SolicitudInvalidaError,
)
from app.domain.ports.in_.registrar_usuario_port import RegistrarUsuarioComando


def usuario(estado="activo", **cambios):
    datos = dict(
        id_usuario=7, id_rol=2, nombre="Ana", correo="ana@test.com",
        contrasena="hash", telefono=None, ubicacion=None, estado=estado,
    )
    datos.update(cambios)
    return Usuario(**datos)


# ======================================================
# SERVICIO DE CÓDIGOS
# ======================================================

@pytest.fixture
def codigos():
    repo, hasher, enviador = Mock(), Mock(), Mock()
    hasher.hashear.side_effect = lambda c: f"h:{c}"
    return CodigoVerificacionService(repo, hasher, enviador), repo, enviador


def registro_codigo(codigo="123456", minutos=5, intentos=0):
    return CodigoVerificacion(
        id_verificacion=3,
        codigo_hash=f"h:{codigo}",
        fecha_expiracion=datetime.now() + timedelta(minutes=minutos),
        intentos=intentos,
    )


def test_emitir_guarda_hash_y_envia_codigo(codigos):
    servicio, repo, enviador = codigos

    servicio.emitir(usuario(), "REGISTRO")

    enviado = enviador.enviar.call_args.kwargs
    guardado = repo.reemplazar.call_args.kwargs
    assert len(enviado["codigo"]) == 6 and enviado["codigo"].isdigit()
    assert guardado["codigo_hash"] == f"h:{enviado['codigo']}"
    assert guardado["tipo"] == "REGISTRO"
    assert enviado["minutos_validez"] == CODIGO_EXPIRA_MINUTOS
    assert guardado["fecha_expiracion"] > datetime.now()


def test_validar_codigo_correcto_lo_marca_usado(codigos):
    servicio, repo, _ = codigos
    repo.obtener_vigente.return_value = registro_codigo()

    servicio.validar(7, "123456", "REGISTRO")

    repo.marcar_usado.assert_called_once_with(3)


def test_validar_sin_codigo(codigos):
    servicio, repo, _ = codigos
    repo.obtener_vigente.return_value = None

    with pytest.raises(SolicitudInvalidaError, match="No existe un código válido"):
        servicio.validar(7, "123456", "REGISTRO")


def test_validar_codigo_expirado(codigos):
    servicio, repo, _ = codigos
    repo.obtener_vigente.return_value = registro_codigo(minutos=-1)

    with pytest.raises(SolicitudInvalidaError, match="El código ha expirado"):
        servicio.validar(7, "123456", "REGISTRO")

    repo.marcar_usado.assert_called_once_with(3)


def test_validar_supera_intentos(codigos):
    servicio, repo, _ = codigos
    repo.obtener_vigente.return_value = registro_codigo(intentos=MAX_INTENTOS_CODIGO)

    with pytest.raises(DemasiadosIntentosError):
        servicio.validar(7, "123456", "REGISTRO")


def test_validar_codigo_incorrecto_suma_intento(codigos):
    servicio, repo, _ = codigos
    repo.obtener_vigente.return_value = registro_codigo()

    with pytest.raises(SolicitudInvalidaError, match="Código incorrecto"):
        servicio.validar(7, "000000", "REGISTRO")

    repo.registrar_intento_fallido.assert_called_once_with(3, MAX_INTENTOS_CODIGO)
    repo.marcar_usado.assert_not_called()


# ======================================================
# REGISTRO / VERIFICACIÓN / REENVÍO
# ======================================================

COMANDO = RegistrarUsuarioComando(nombre="Ana", correo="ana@test.com", contrasena="Clave1234")


@pytest.mark.parametrize(
    ("error_correo", "enviado"),
    [(None, True), (ServicioExternoError(), False), (ConfiguracionError(), False)],
)
def test_registrar_cuenta_queda_pendiente(error_correo, enviado):
    registrar, repo, codigos = Mock(), Mock(), Mock()
    registrar.ejecutar.return_value = usuario()
    codigos.emitir.side_effect = error_correo

    cuenta = RegistrarCuentaUseCase(registrar, repo, codigos).ejecutar(COMANDO)

    assert cuenta.correo_enviado is enviado
    repo.actualizar_estado.assert_called_once_with(7, "pendiente")


def test_registrar_cuenta_propaga_datos_invalidos():
    registrar = Mock()
    registrar.ejecutar.side_effect = DatosInvalidosError("nombre", "corto")

    with pytest.raises(DatosInvalidosError):
        RegistrarCuentaUseCase(registrar, Mock(), Mock()).ejecutar(COMANDO)


def test_verificar_correo_activa_la_cuenta():
    repo, codigos = Mock(), Mock()
    repo.find_by_email.return_value = usuario(estado="pendiente")

    assert VerificarCorreoUseCase(repo, codigos).ejecutar(" ANA@test.com ", "123456") is True
    repo.find_by_email.assert_called_once_with("ana@test.com")
    codigos.validar.assert_called_once_with(7, "123456", "REGISTRO")
    repo.actualizar_estado.assert_called_once_with(7, "activo")


def test_verificar_correo_ya_activa():
    repo, codigos = Mock(), Mock()
    repo.find_by_email.return_value = usuario(estado="Activo")

    assert VerificarCorreoUseCase(repo, codigos).ejecutar("ana@test.com", "123456") is False
    codigos.validar.assert_not_called()


@pytest.mark.parametrize("clase", [VerificarCorreoUseCase, ReenviarCodigoUseCase])
def test_usuario_no_encontrado(clase):
    repo = Mock()
    repo.find_by_email.return_value = None
    caso = clase(repo, Mock())
    argumentos = ("x@test.com", "123456") if clase is VerificarCorreoUseCase else ("x@test.com",)

    with pytest.raises(RecursoNoEncontradoError, match="Usuario no encontrado"):
        caso.ejecutar(*argumentos)


@pytest.mark.parametrize(("estado", "esperado"), [("pendiente", True), ("activo", False)])
def test_reenviar_codigo(estado, esperado):
    repo, codigos = Mock(), Mock()
    repo.find_by_email.return_value = usuario(estado=estado)

    assert ReenviarCodigoUseCase(repo, codigos).ejecutar("ana@test.com") is esperado
    assert codigos.emitir.called is esperado


# ======================================================
# INICIO DE SESIÓN
# ======================================================

@pytest.fixture
def sesion():
    login, repo, auditoria = Mock(), Mock(), Mock()
    login.execute.return_value = "7"
    repo.find_by_id.return_value = usuario()
    return IniciarSesionUseCase(login, repo, auditoria), login, repo, auditoria


def test_iniciar_sesion_exitoso(sesion):
    caso, _, _, auditoria = sesion

    assert caso.ejecutar("ana@test.com", "Clave1234") == 7
    assert auditoria.registrar.call_args.kwargs["resultado"] == "EXITOSO"


def test_iniciar_sesion_credenciales_invalidas(sesion):
    caso, login, _, auditoria = sesion
    login.execute.side_effect = InvalidCredentialsError()

    with pytest.raises(InvalidCredentialsError):
        caso.ejecutar("ana@test.com", "mala")

    assert auditoria.registrar.call_args.kwargs["detalle"] == "Credenciales incorrectas"


def test_iniciar_sesion_usuario_desaparecido(sesion):
    caso, _, repo, _ = sesion
    repo.find_by_id.return_value = None

    with pytest.raises(NoAutenticadoError, match="Usuario no encontrado"):
        caso.ejecutar("ana@test.com", "Clave1234")


def test_iniciar_sesion_cuenta_pendiente(sesion):
    caso, _, repo, auditoria = sesion
    repo.find_by_id.return_value = usuario(estado="pendiente")

    with pytest.raises(AccesoDenegadoError, match="verificar tu correo"):
        caso.ejecutar("ana@test.com", "Clave1234")

    assert auditoria.registrar.call_args.kwargs["resultado"] == "DENEGADO"


# ======================================================
# GOOGLE
# ======================================================

DATOS_GOOGLE = {"sub": "g-1", "email": " ANA@test.com ", "name": " Ana ", "email_verified": True}


@pytest.fixture
def google():
    verificador, registrar, repo, google_repo = Mock(), Mock(), Mock(), Mock()
    verificador.verificar.return_value = dict(DATOS_GOOGLE)
    google_repo.obtener_id_usuario.return_value = None
    google_repo.obtener_sub.return_value = None
    repo.find_by_email.return_value = usuario()
    caso = AutenticarConGoogleUseCase(verificador, registrar, repo, google_repo)
    return caso, verificador, registrar, repo, google_repo


def test_google_usuario_ya_vinculado(google):
    caso, _, _, repo, google_repo = google
    google_repo.obtener_id_usuario.return_value = 7
    repo.find_by_id.return_value = usuario()

    assert caso.ejecutar("cred").id_usuario == 7
    google_repo.vincular.assert_not_called()
    repo.actualizar_estado.assert_called_once_with(7, "activo")


def test_google_vinculado_pero_usuario_borrado(google):
    caso, _, _, repo, google_repo = google
    google_repo.obtener_id_usuario.return_value = 7
    repo.find_by_id.return_value = None

    with pytest.raises(NoAutenticadoError):
        caso.ejecutar("cred")


def test_google_vincula_cuenta_existente_por_correo(google):
    caso, _, registrar, repo, google_repo = google

    caso.ejecutar("cred")

    repo.find_by_email.assert_called_with("ana@test.com")
    registrar.ejecutar.assert_not_called()
    google_repo.vincular.assert_called_once_with(7, "g-1")


def test_google_crea_usuario_nuevo(google):
    caso, verificador, registrar, repo, google_repo = google
    verificador.verificar.return_value = {**DATOS_GOOGLE, "name": None}
    repo.find_by_email.return_value = None
    registrar.ejecutar.return_value = usuario(id_usuario=8)

    assert caso.ejecutar("cred").id_usuario == 8
    comando = registrar.ejecutar.call_args.args[0]
    assert comando.nombre == "ana"
    assert comando.contrasena.startswith("Aa1!")
    google_repo.vincular.assert_called_once_with(8, "g-1")


def test_google_carrera_al_crear_usuario(google):
    caso, _, registrar, repo, _ = google
    repo.find_by_email.side_effect = [None, usuario()]
    registrar.ejecutar.side_effect = CorreoYaRegistradoError()

    assert caso.ejecutar("cred").id_usuario == 7


def test_google_no_pudo_crear_usuario(google):
    caso, _, registrar, repo, _ = google
    repo.find_by_email.side_effect = [None, None]
    registrar.ejecutar.side_effect = CorreoYaRegistradoError()

    with pytest.raises(ErrorInternoError, match="No fue posible crear el usuario"):
        caso.ejecutar("cred")


def test_google_cuenta_vinculada_a_otro_google(google):
    caso, _, _, _, google_repo = google
    google_repo.obtener_sub.return_value = "otro"

    with pytest.raises(ConflictoError):
        caso.ejecutar("cred")


@pytest.mark.parametrize("campo", ["sub", "email", "email_verified"])
def test_google_datos_incompletos(google, campo):
    caso, verificador, *_ = google
    verificador.verificar.return_value = {**DATOS_GOOGLE, campo: None}

    with pytest.raises(NoAutenticadoError, match="no pudo verificarse"):
        caso.ejecutar("cred")


# ======================================================
# RECUPERACIÓN DE CONTRASEÑA / USUARIO ACTUAL
# ======================================================

@pytest.mark.parametrize(("encontrado", "emitido"), [(usuario(), True), (None, False)])
def test_solicitar_recuperacion(encontrado, emitido):
    repo, codigos = Mock(), Mock()
    repo.find_by_email.return_value = encontrado

    SolicitarRecuperacionUseCase(repo, codigos).ejecutar("ana@test.com")

    assert codigos.emitir.called is emitido


def test_restablecer_contrasena():
    repo, codigos, hasher = Mock(), Mock(), Mock()
    repo.find_by_email.return_value = usuario(estado="pendiente")
    hasher.hashear.return_value = "nuevo-hash"

    RestablecerContrasenaUseCase(repo, codigos, hasher).ejecutar("ana@test.com", "123456", "NuevaClave1")

    codigos.validar.assert_called_once_with(7, "123456", "RECUPERAR_PASSWORD")
    repo.actualizar_contrasena.assert_called_once_with(7, "nuevo-hash")
    repo.actualizar_estado.assert_called_once_with(7, "activo")


def test_restablecer_correo_desconocido():
    repo = Mock()
    repo.find_by_email.return_value = None

    with pytest.raises(SolicitudInvalidaError, match="Correo o código inválido"):
        RestablecerContrasenaUseCase(repo, Mock(), Mock()).ejecutar("x@test.com", "123456", "NuevaClave1")


@pytest.mark.parametrize(
    ("clave", "mensaje"),
    [
        ("Corta1", "mínimo 8"),
        ("sinmayuscula1", "mayúscula"),
        ("SINMINUSCULA1", "minúscula"),
        ("SinNumeros", "número"),
    ],
)
def test_restablecer_valida_politica(clave, mensaje):
    repo, codigos = Mock(), Mock()
    repo.find_by_email.return_value = usuario()

    with pytest.raises(DatosInvalidosError, match=mensaje):
        RestablecerContrasenaUseCase(repo, codigos, Mock()).ejecutar("ana@test.com", "123456", clave)

    codigos.validar.assert_not_called()


def test_obtener_usuario_actual():
    repo = Mock()
    repo.find_by_id.return_value = usuario()

    assert ObtenerUsuarioActualUseCase(repo).ejecutar(7).nombre == "Ana"


def test_obtener_usuario_actual_inexistente():
    repo = Mock()
    repo.find_by_id.return_value = None

    with pytest.raises(NoAutenticadoError):
        ObtenerUsuarioActualUseCase(repo).ejecutar(7)
