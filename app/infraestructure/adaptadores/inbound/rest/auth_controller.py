from fastapi import APIRouter, Depends, Response

from app.config.dependencies import (
    get_autenticar_google_use_case,
    get_iniciar_sesion_use_case,
    get_reenviar_codigo_use_case,
    get_registrar_cuenta_use_case,
    get_restablecer_contrasena_use_case,
    get_solicitar_recuperacion_use_case,
    get_token_service,
    get_usuario_actual_use_case,
    get_verificar_correo_use_case,
)
from app.domain.ports.in_.cuenta_ports import (
    AutenticarConGooglePort,
    IniciarSesionPort,
    ObtenerUsuarioActualPort,
    ReenviarCodigoPort,
    RegistrarCuentaPort,
    RestablecerContrasenaPort,
    SolicitarRecuperacionPort,
    VerificarCorreoPort,
)
from app.domain.ports.in_.registrar_usuario_port import RegistrarUsuarioComando
from app.domain.ports.out.token_port import TokenPort
from app.infraestructure.adaptadores.inbound.rest.schemas import (
    CorreoRequest,
    GoogleAuthRequest,
    LoginRequest,
    RegistrarRequest,
    ResetPasswordRequest,
    UsuarioResponse,
    VerificarCodigoRequest,
)
from app.infraestructure.adaptadores.inbound.rest.seguridad import (
    abrir_sesion,
    cerrar_sesion,
    obtener_id_usuario_autenticado,
)

router = APIRouter(prefix="/auth", tags=["Autenticación"])

MENSAJE_YA_VERIFICADA = "La cuenta ya está verificada"


@router.post("/register", status_code=201)
def register(
    body: RegistrarRequest,
    use_case: RegistrarCuentaPort = Depends(get_registrar_cuenta_use_case),
):
    cuenta = use_case.ejecutar(
        RegistrarUsuarioComando(
            nombre=body.nombre,
            correo=body.correo,
            contrasena=body.password,
            telefono=body.telefono,
            ubicacion=body.ubicacion,
        )
    )
    usuario = cuenta.usuario

    return {
        "id": usuario.id_usuario,
        "nombre": usuario.nombre,
        "correo": usuario.correo,
        "estado": "pendiente",
        "requiere_verificacion": True,
        "correo_enviado": cuenta.correo_enviado,
        "mensaje": (
            "Revisa tu correo para verificar tu cuenta"
            if cuenta.correo_enviado
            else "Cuenta creada. Usa reenviar código."
        ),
    }


@router.post("/verify-email")
def verify_email(
    body: VerificarCodigoRequest,
    use_case: VerificarCorreoPort = Depends(get_verificar_correo_use_case),
):
    if not use_case.ejecutar(body.correo, body.codigo):
        return {"mensaje": MENSAJE_YA_VERIFICADA}

    return {"mensaje": "Correo verificado correctamente"}


@router.post("/resend-code")
def resend_code(
    body: CorreoRequest,
    use_case: ReenviarCodigoPort = Depends(get_reenviar_codigo_use_case),
):
    if not use_case.ejecutar(body.correo):
        return {"mensaje": MENSAJE_YA_VERIFICADA}

    return {"mensaje": "Código reenviado correctamente"}


@router.post("/login")
def login(
    body: LoginRequest,
    response: Response,
    use_case: IniciarSesionPort = Depends(get_iniciar_sesion_use_case),
    tokens: TokenPort = Depends(get_token_service),
):
    id_usuario = use_case.ejecutar(body.correo, body.password)
    abrir_sesion(response, tokens.crear(id_usuario))

    return {"mensaje": "Login exitoso"}


@router.post("/google")
def google_auth(
    body: GoogleAuthRequest,
    response: Response,
    use_case: AutenticarConGooglePort = Depends(get_autenticar_google_use_case),
    tokens: TokenPort = Depends(get_token_service),
):
    usuario = use_case.ejecutar(body.credential)
    abrir_sesion(response, tokens.crear(usuario.id_usuario))

    return {
        "mensaje": "Autenticación con Google exitosa",
        "usuario": {
            "id": usuario.id_usuario,
            "nombre": usuario.nombre,
            "correo": usuario.correo,
        },
    }


# También sirve para una cuenta creada con Google.
@router.post("/forgot-password")
def forgot_password(
    body: CorreoRequest,
    use_case: SolicitarRecuperacionPort = Depends(get_solicitar_recuperacion_use_case),
):
    use_case.ejecutar(body.correo)

    return {"mensaje": "Si el correo está registrado, recibirás un código."}


@router.post("/reset-password")
def reset_password(
    body: ResetPasswordRequest,
    use_case: RestablecerContrasenaPort = Depends(get_restablecer_contrasena_use_case),
):
    use_case.ejecutar(body.correo, body.codigo, body.nueva_password)

    return {"mensaje": "Contraseña actualizada correctamente"}


@router.get("/me", response_model=UsuarioResponse)
def me(
    id_usuario: int = Depends(obtener_id_usuario_autenticado),
    use_case: ObtenerUsuarioActualPort = Depends(get_usuario_actual_use_case),
):
    usuario = use_case.ejecutar(id_usuario)

    return UsuarioResponse(id=usuario.id_usuario, correo=usuario.correo, nombre=usuario.nombre)


@router.post("/logout")
def logout(response: Response):
    cerrar_sesion(response)

    return {"mensaje": "Sesión cerrada correctamente"}
