from io import BytesIO

from app.domain.exceptions import SolicitudInvalidaError
from app.domain.ports.out.procesador_imagen_port import ProcesadorImagenPort

IMAGEN_NO_VALIDA = "El archivo no es una imagen válida"


class PillowProcesadorImagen(ProcesadorImagenPort):
    """Normaliza fotos de perfil con Pillow: verifica que sean imágenes reales, corrige la
    rotación de las fotos de celular, recorta al centro en un cuadrado y guarda un JPEG sin
    metadatos (así no se publica, por ejemplo, la ubicación GPS de la foto)."""

    def __init__(self, lado: int, calidad: int = 85, max_pixeles: int = 40_000_000):
        self._lado = lado
        self._calidad = calidad
        self._max_pixeles = max_pixeles  # evita "bombas" de descompresión

    def foto_de_perfil(self, contenido: bytes) -> bytes:
        # Se importa aquí para que el backend arranque aunque Pillow aún no esté instalado
        from PIL import Image, ImageOps, UnidentifiedImageError

        try:
            with Image.open(BytesIO(contenido)) as imagen:
                imagen.verify()  # detecta archivos dañados o que no son imagen

            # verify() deja la imagen inutilizable: hay que abrirla de nuevo
            with Image.open(BytesIO(contenido)) as imagen:
                if imagen.width * imagen.height > self._max_pixeles:
                    raise SolicitudInvalidaError("La imagen es demasiado grande")

                imagen = ImageOps.exif_transpose(imagen)
                imagen = self._sobre_fondo_blanco(imagen, Image)
                cuadrada = ImageOps.fit(
                    imagen, (self._lado, self._lado), Image.Resampling.LANCZOS
                )

                salida = BytesIO()
                cuadrada.save(salida, "JPEG", quality=self._calidad, optimize=True)
                return salida.getvalue()
        except (UnidentifiedImageError, Image.DecompressionBombError, OSError, SyntaxError) as e:
            raise SolicitudInvalidaError(IMAGEN_NO_VALIDA) from e

    @staticmethod
    def _sobre_fondo_blanco(imagen, Image):
        # JPEG no tiene transparencia: un PNG con fondo transparente quedaría negro
        if imagen.mode in ("RGBA", "LA") or (imagen.mode == "P" and "transparency" in imagen.info):
            con_alfa = imagen.convert("RGBA")
            fondo = Image.new("RGB", con_alfa.size, (255, 255, 255))
            fondo.paste(con_alfa, mask=con_alfa.getchannel("A"))
            return fondo
        return imagen.convert("RGB")
