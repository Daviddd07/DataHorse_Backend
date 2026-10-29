
from app.infraestructure.adaptadores.outbound.security.password_hasher import (
    PasswordHasher,
)


def test_hash_genera_un_hash_diferente_a_la_contrasena():
    hasher = PasswordHasher()
    contrasena = "ClaveSegura123"

    resultado = hasher.hash(contrasena)

    assert resultado != contrasena
    assert resultado.startswith("$2")


def test_verify_acepta_la_contrasena_correcta():
    hasher = PasswordHasher()
    contrasena = "ClaveSegura123"
    hash_generado = hasher.hash(contrasena)

    assert hasher.verify(contrasena, hash_generado) is True


def test_verify_rechaza_una_contrasena_incorrecta():
    hasher = PasswordHasher()
    hash_generado = hasher.hash("ClaveSegura123")

    assert hasher.verify("OtraClave456", hash_generado) is False


def test_hash_genera_hashes_diferentes_para_la_misma_contrasena():
    hasher = PasswordHasher()
    contrasena = "ClaveSegura123"

    hash_1 = hasher.hash(contrasena)
    hash_2 = hasher.hash(contrasena)

    assert hash_1 != hash_2
    assert hasher.verify(contrasena, hash_1)
    assert hasher.verify(contrasena, hash_2)
