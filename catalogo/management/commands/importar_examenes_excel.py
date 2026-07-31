import re
from collections import Counter
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP
from pathlib import Path
from xml.etree import ElementTree
from zipfile import BadZipFile, ZipFile

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from catalogo.models import Categoria, Familia, Producto
from empresas.models import Empresa


MAIN_NAMESPACE = "http://schemas.openxmlformats.org/spreadsheetml/2006/main"
RELATIONSHIP_NAMESPACE = (
    "http://schemas.openxmlformats.org/officeDocument/2006/relationships"
)
NAMESPACES = {"main": MAIN_NAMESPACE}
MONEY_QUANTIZER = Decimal("0.01")


class Command(BaseCommand):
    help = (
        "Importa los examenes de la hoja PRECIOS de un archivo XLSX "
        "a una familia del catalogo."
    )

    def add_arguments(self, parser):
        parser.add_argument("--archivo", required=True)
        parser.add_argument("--empresa-slug", default="Analiza")
        parser.add_argument("--familia", default="Examenes")
        parser.add_argument("--hoja", default="PRECIOS")
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Valida y muestra el resumen sin guardar cambios.",
        )
        parser.add_argument(
            "--actualizar-existentes",
            action="store_true",
            help=(
                "Actualiza nombre, precio y categoria cuando el codigo "
                "ya existe en la empresa."
            ),
        )

    def handle(self, *args, **options):
        archivo = Path(options["archivo"]).expanduser().resolve()
        if not archivo.is_file():
            raise CommandError(f"No existe el archivo: {archivo}")

        empresa = Empresa.objects.filter(
            slug__iexact=options["empresa_slug"].strip()
        ).first()
        if not empresa:
            raise CommandError(
                f"No existe la empresa con slug {options['empresa_slug']}."
            )

        familia = Familia.objects.filter(
            empresa=empresa,
            nombre__iexact=options["familia"].strip(),
        ).first()
        if not familia:
            raise CommandError(
                f"No existe la familia {options['familia']} en {empresa.nombre}."
            )

        registros = self._leer_registros(archivo, options["hoja"])
        self._validar_registros(registros)
        resumen = self._calcular_resumen(empresa, registros)

        self.stdout.write(
            self.style.SUCCESS(
                f"Archivo valido: {len(registros)} examenes y "
                f"{resumen['total_categorias']} categorias."
            )
        )
        self.stdout.write(
            f"Nuevas categorias: {resumen['categorias_nuevas']}; "
            f"nuevos examenes: {resumen['productos_nuevos']}; "
            f"codigos existentes: {resumen['productos_existentes']}."
        )

        if options["dry_run"]:
            self.stdout.write(
                self.style.WARNING("Simulacion finalizada: no se guardaron cambios.")
            )
            return

        with transaction.atomic():
            resultado = self._importar(
                empresa=empresa,
                familia=familia,
                registros=registros,
                actualizar_existentes=options["actualizar_existentes"],
            )

        self.stdout.write(
            self.style.SUCCESS(
                "Importacion completada: "
                f"{resultado['categorias_creadas']} categorias creadas, "
                f"{resultado['productos_creados']} examenes creados, "
                f"{resultado['productos_actualizados']} actualizados y "
                f"{resultado['productos_omitidos']} omitidos."
            )
        )

    def _leer_registros(self, archivo, nombre_hoja):
        try:
            with ZipFile(archivo) as workbook:
                shared_strings = self._leer_shared_strings(workbook)
                ruta_hoja = self._obtener_ruta_hoja(workbook, nombre_hoja)
                hoja = ElementTree.fromstring(workbook.read(ruta_hoja))
        except (BadZipFile, KeyError, ElementTree.ParseError) as exc:
            raise CommandError(f"El archivo XLSX no se pudo leer: {exc}") from exc

        registros = []
        for fila in hoja.findall(".//main:sheetData/main:row", NAMESPACES):
            numero_fila = int(fila.attrib["r"])
            if numero_fila == 1:
                continue

            valores = {}
            for celda in fila.findall("main:c", NAMESPACES):
                columna = re.match(r"[A-Z]+", celda.attrib["r"]).group()
                valores[columna] = self._leer_valor_celda(
                    celda,
                    shared_strings,
                )

            if not any(valores.values()):
                continue

            registros.append(
                {
                    "fila": numero_fila,
                    "codigo": (valores.get("A") or "").strip(),
                    "nombre": (valores.get("B") or "").strip(),
                    "categoria": (valores.get("C") or "").strip(),
                    "precio_original": (valores.get("D") or "").strip(),
                }
            )

        return registros

    def _leer_shared_strings(self, workbook):
        if "xl/sharedStrings.xml" not in workbook.namelist():
            return []

        root = ElementTree.fromstring(workbook.read("xl/sharedStrings.xml"))
        return [
            "".join(
                node.text or ""
                for node in item.iter(f"{{{MAIN_NAMESPACE}}}t")
            )
            for item in root.findall("main:si", NAMESPACES)
        ]

    def _obtener_ruta_hoja(self, workbook, nombre_hoja):
        relaciones = ElementTree.fromstring(
            workbook.read("xl/_rels/workbook.xml.rels")
        )
        destinos = {
            relacion.attrib["Id"]: relacion.attrib["Target"]
            for relacion in relaciones
        }
        workbook_xml = ElementTree.fromstring(workbook.read("xl/workbook.xml"))

        for hoja in workbook_xml.find("main:sheets", NAMESPACES):
            if hoja.attrib["name"].casefold() != nombre_hoja.casefold():
                continue

            relationship_id = hoja.attrib[
                f"{{{RELATIONSHIP_NAMESPACE}}}id"
            ]
            destino = destinos[relationship_id].lstrip("/")
            return destino if destino.startswith("xl/") else f"xl/{destino}"

        raise CommandError(f"No existe la hoja {nombre_hoja} en el archivo.")

    def _leer_valor_celda(self, celda, shared_strings):
        tipo = celda.attrib.get("t")
        valor = celda.find("main:v", NAMESPACES)

        if tipo == "s" and valor is not None:
            return shared_strings[int(valor.text)]

        if tipo == "inlineStr":
            inline = celda.find("main:is", NAMESPACES)
            if inline is None:
                return ""
            return "".join(
                node.text or ""
                for node in inline.iter(f"{{{MAIN_NAMESPACE}}}t")
            )

        return valor.text if valor is not None else ""

    def _validar_registros(self, registros):
        if not registros:
            raise CommandError("La hoja no contiene examenes para importar.")

        errores = []
        for registro in registros:
            faltantes = [
                campo
                for campo in ["codigo", "nombre", "categoria", "precio_original"]
                if not registro[campo]
            ]
            if faltantes:
                errores.append(
                    f"Fila {registro['fila']}: faltan {', '.join(faltantes)}."
                )
                continue

            try:
                precio = Decimal(registro["precio_original"])
            except InvalidOperation:
                errores.append(
                    f"Fila {registro['fila']}: precio invalido "
                    f"{registro['precio_original']}."
                )
                continue

            if precio < 0:
                errores.append(
                    f"Fila {registro['fila']}: el precio no puede ser negativo."
                )
                continue

            registro["precio"] = precio.quantize(
                MONEY_QUANTIZER,
                rounding=ROUND_HALF_UP,
            )

        codigos = Counter(
            registro["codigo"].casefold()
            for registro in registros
            if registro["codigo"]
        )
        duplicados = [codigo for codigo, cantidad in codigos.items() if cantidad > 1]
        if duplicados:
            errores.append(
                "Codigos repetidos en el archivo: " + ", ".join(duplicados)
            )

        if errores:
            detalle = "\n".join(errores[:20])
            if len(errores) > 20:
                detalle += f"\n... y {len(errores) - 20} errores adicionales."
            raise CommandError(detalle)

    def _calcular_resumen(self, empresa, registros):
        categorias_actuales = {
            nombre.casefold()
            for nombre in Categoria.objects.filter(empresa=empresa).values_list(
                "nombre",
                flat=True,
            )
        }
        categorias_archivo = {
            registro["categoria"].casefold() for registro in registros
        }
        codigos_actuales = {
            codigo.casefold()
            for codigo in Producto.objects.filter(
                empresa=empresa,
                codigo_barra__isnull=False,
            ).values_list("codigo_barra", flat=True)
        }
        productos_existentes = sum(
            registro["codigo"].casefold() in codigos_actuales
            for registro in registros
        )

        return {
            "total_categorias": len(categorias_archivo),
            "categorias_nuevas": len(categorias_archivo - categorias_actuales),
            "productos_nuevos": len(registros) - productos_existentes,
            "productos_existentes": productos_existentes,
        }

    def _importar(
        self,
        empresa,
        familia,
        registros,
        actualizar_existentes,
    ):
        categorias = {
            categoria.nombre.casefold(): categoria
            for categoria in Categoria.objects.filter(empresa=empresa)
        }
        productos = {
            producto.codigo_barra.casefold(): producto
            for producto in Producto.objects.filter(
                empresa=empresa,
                codigo_barra__isnull=False,
            )
        }
        categorias_creadas = 0
        productos_creados = 0
        productos_actualizados = 0
        productos_omitidos = 0

        for registro in registros:
            categoria_clave = registro["categoria"].casefold()
            categoria = categorias.get(categoria_clave)
            if not categoria:
                categoria = Categoria.objects.create(
                    empresa=empresa,
                    familia=familia,
                    nombre=registro["categoria"],
                    activa=True,
                )
                categorias[categoria_clave] = categoria
                categorias_creadas += 1

            codigo_clave = registro["codigo"].casefold()
            producto = productos.get(codigo_clave)
            if producto:
                if not actualizar_existentes:
                    productos_omitidos += 1
                    continue

                producto.familia = familia
                producto.categoria = categoria
                producto.nombre = registro["nombre"]
                producto.precio = registro["precio"]
                producto.activo = True
                producto.save()
                productos_actualizados += 1
                continue

            producto = Producto.objects.create(
                empresa=empresa,
                familia=familia,
                categoria=categoria,
                codigo_barra=registro["codigo"],
                nombre=registro["nombre"],
                precio=registro["precio"],
                activo=True,
            )
            productos[codigo_clave] = producto
            productos_creados += 1

        return {
            "categorias_creadas": categorias_creadas,
            "productos_creados": productos_creados,
            "productos_actualizados": productos_actualizados,
            "productos_omitidos": productos_omitidos,
        }
