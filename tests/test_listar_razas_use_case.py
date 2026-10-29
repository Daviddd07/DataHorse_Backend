from unittest.mock import Mock

from app.application.use_cases.listar_razas_use_case import ListarRazasUseCase


def test_ejecutar_devuelve_todas_las_razas():
    raza_repo = Mock()
    razas = [Mock(), Mock()]
    raza_repo.find_all.return_value = razas

    caso_uso = ListarRazasUseCase(raza_repo)

    resultado = caso_uso.ejecutar()

    assert resultado == razas
    raza_repo.find_all.assert_called_once_with()


def test_ejecutar_devuelve_lista_vacia_si_no_hay_razas():
    raza_repo = Mock()
    raza_repo.find_all.return_value = []

    caso_uso = ListarRazasUseCase(raza_repo)

    resultado = caso_uso.ejecutar()

    assert resultado == []
    raza_repo.find_all.assert_called_once_with()
