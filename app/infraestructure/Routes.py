from fastapi import APIRouter, Depends, HTTPException, status

from app.config.dependencies import get_registrar_use_case
from app.domain.exceptions import EmailAlreadyExistsError, DatosInvalidosError
from app.domain.ports.in_.registrar_usuario_port import RegistrarUsuarioComando, RegistrarUsuarioPort
from app.infraestructure.adaptadores.inbound.registro_schemas import RegistroRequest, RegistroResponse
router = APIRouter(prefix="/api/usuarios", tags=["usuarios"])


@router.post("/registro", response_model=RegistroResponse, status_code=status.HTTP_201_CREATED)
def registrar(datos: RegistroRequest, caso_uso: RegistrarUsuarioPort = Depends(get_registrar_use_case)):
    try:
        usuario = caso_uso.ejecutar(RegistrarUsuarioComando(**datos.model_dump()))
    except DatosInvalidosError as e:
        raise HTTPException(status_code=422, detail=f"{e.campo}: {e.mensaje}")
    except EmailAlreadyExistsError:
        raise HTTPException(status_code=409, detail="No se pudo completar el registro.")
    return RegistroResponse(id_usuario=usuario.id_usuario, nombre=usuario.nombre, correo=usuario.correo)
