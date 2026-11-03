"""Pruebas de la descendencia: entidad y reglas del dominio."""
import pytest

from app.domain.entities.descendencia import Descendencia
from app.domain.exceptions import DatosInvalidosError
from app.domain.services.validador_descendencia import MAX_CRIAS, normalizar_descendencia


def test_campos_vacios_lista_lo_que_falta():
    descendencia = Descendencia(padre_nombre="Rayo", crias_anteriores=0)

    vacios = descendencia.campos_vacios()

    assert "padre_nombre" not in vacios
    assert "crias_anteriores" not in vacios  # 0 es un dato, no un vacío
    assert "madre_nombre" in vacios
    assert len(vacios) == len(Descendencia.campos()) - 2


def test_normalizar_sin_descendencia():
    assert normalizar_descendencia(None) is None


def test_normalizar_quita_espacios_y_vacios():
    resultado = normalizar_descendencia(
        Descendencia(padre_nombre="  Rayo  ", madre_nombre="   ", modalidad=" Trocha ", crias_anteriores=2)
    )

    assert resultado.padre_nombre == "Rayo"
    assert resultado.madre_nombre is None
    assert resultado.modalidad == "Trocha"
    assert resultado.crias_anteriores == 2


@pytest.mark.parametrize(
    ("cambios", "campo"),
    [
        ({"modalidad": "Volar"}, "modalidad"),
        ({"temperamento": "Feliz"}, "temperamento"),
        ({"crias_anteriores": -1}, "crias_anteriores"),
        ({"crias_anteriores": MAX_CRIAS + 1}, "crias_anteriores"),
    ],
)
def test_normalizar_rechaza_valores_invalidos(cambios, campo):
    descendencia = Descendencia(**cambios)

    with pytest.raises(DatosInvalidosError) as error:
        normalizar_descendencia(descendencia)

    assert error.value.campo == campo


def test_normalizar_acepta_las_opciones_validas():
    resultado = normalizar_descendencia(Descendencia(modalidad="Paso fino colombiano", temperamento="Dócil"))

    assert (resultado.modalidad, resultado.temperamento) == ("Paso fino colombiano", "Dócil")
