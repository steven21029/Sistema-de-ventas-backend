import hashlib
from pathlib import Path

from django.conf import settings
from django.core.files import File
from django.core.files.storage import default_storage
from django.core.management.base import BaseCommand, CommandError
from django.db import connections, transaction
from django.db.models import F

from catalogo.models import (
    Categoria,
    Familia,
    PaqueteCatalogo,
    PaqueteProducto,
    Producto,
)
from empresas.models import (
    Empresa,
    ItemMenuEmpresa,
    SobreNosotrosEmpresa,
    SucursalEmpresa,
)
from promociones.models import BannerPromocional


class Command(BaseCommand):
    help = (
        "Migra unicamente la configuracion, catalogo, banners e imagenes de "
        "Analiza desde SQLite hacia la base principal y Cloudflare R2."
    )

    def add_arguments(self, parser):
        parser.add_argument("--source-database", default="legacy")
        parser.add_argument("--source-slug", default="Analiza")
        parser.add_argument("--dry-run", action="store_true")

    def handle(self, *args, **options):
        source_database = options["source_database"]
        source_slug = options["source_slug"]
        self._validar_origen(source_database)

        try:
            source_company = Empresa.objects.using(source_database).get(
                slug=source_slug
            )
        except Empresa.DoesNotExist as exc:
            raise CommandError(
                f"No existe la empresa {source_slug!r} en {source_database}."
            ) from exc

        if source_company.slug.casefold() == "prueba":
            raise CommandError("La empresa de prueba esta excluida de la migracion.")

        image_names = self._recopilar_imagenes(
            source_database,
            source_company,
        )
        source_counts = self._conteos_origen(source_database, source_company)
        self._mostrar_resumen(source_company, source_counts, image_names)

        if options["dry_run"]:
            self.stdout.write(self.style.WARNING("Simulacion: no se escribieron datos."))
            return

        self._validar_destino()
        uploaded_now = []

        try:
            image_map, uploaded_now = self._subir_imagenes(image_names)
            with transaction.atomic(using="default"):
                target_company = self._migrar_datos(
                    source_database,
                    source_company,
                    image_map,
                )
                self._verificar_resultado(
                    target_company,
                    source_counts,
                    image_map,
                )
        except Exception:
            self._limpiar_subidas(uploaded_now)
            raise

        self.stdout.write(
            self.style.SUCCESS(
                "Analiza se migro correctamente a Supabase y Cloudflare R2."
            )
        )

    def _validar_origen(self, alias):
        if alias == "default":
            raise CommandError("La base de origen no puede ser la base principal.")
        if alias not in connections:
            raise CommandError(
                f"No existe la conexion {alias!r}. Configura LEGACY_DATABASE_URL."
            )
        if connections[alias].vendor != "sqlite":
            raise CommandError("La base de origen debe ser SQLite.")

    def _validar_destino(self):
        if connections["default"].vendor != "postgresql":
            raise CommandError("La base principal de destino debe ser PostgreSQL.")
        if not settings.R2_STORAGE_ENABLED:
            raise CommandError("R2_STORAGE_ENABLED debe estar en True.")

    def _recopilar_imagenes(self, alias, empresa):
        specs = [
            (Empresa.objects.using(alias).filter(pk=empresa.pk), "logo"),
            (
                Empresa.objects.using(alias).filter(pk=empresa.pk),
                "imagen_sucursales",
            ),
            (
                SobreNosotrosEmpresa.objects.using(alias).filter(empresa=empresa),
                "imagen",
            ),
            (
                SucursalEmpresa.objects.using(alias).filter(empresa=empresa),
                "imagen",
            ),
            (Familia.objects.using(alias).filter(empresa=empresa), "imagen"),
            (Categoria.objects.using(alias).filter(empresa=empresa), "imagen"),
            (
                Producto.objects.using(alias).filter(empresa=empresa),
                "imagen_principal",
            ),
            (
                PaqueteCatalogo.objects.using(alias).filter(empresa=empresa),
                "imagen",
            ),
            (
                BannerPromocional.objects.using(alias).filter(empresa=empresa),
                "imagen",
            ),
        ]
        names = {
            getattr(obj, field_name).name
            for queryset, field_name in specs
            for obj in queryset
            if getattr(obj, field_name) and getattr(obj, field_name).name
        }

        media_root = Path(settings.MEDIA_ROOT).resolve()
        missing = []
        for name in sorted(names):
            source_path = (media_root / name).resolve()
            if media_root not in source_path.parents or not source_path.is_file():
                missing.append(name)

        if missing:
            raise CommandError(
                "Faltan archivos locales referenciados: " + ", ".join(missing)
            )
        return sorted(names)

    def _conteos_origen(self, alias, empresa):
        return {
            "menus": ItemMenuEmpresa.objects.using(alias)
            .filter(empresa=empresa)
            .count(),
            "sobre_nosotros": SobreNosotrosEmpresa.objects.using(alias)
            .filter(empresa=empresa)
            .count(),
            "sucursales": SucursalEmpresa.objects.using(alias)
            .filter(empresa=empresa)
            .count(),
            "familias": Familia.objects.using(alias)
            .filter(empresa=empresa)
            .count(),
            "categorias": Categoria.objects.using(alias)
            .filter(empresa=empresa)
            .count(),
            "productos": Producto.objects.using(alias)
            .filter(empresa=empresa)
            .count(),
            "paquetes": PaqueteCatalogo.objects.using(alias)
            .filter(empresa=empresa)
            .count(),
            "componentes": PaqueteProducto.objects.using(alias)
            .filter(paquete__empresa=empresa)
            .count(),
            "banners": BannerPromocional.objects.using(alias)
            .filter(empresa=empresa)
            .count(),
        }

    def _mostrar_resumen(self, empresa, counts, image_names):
        self.stdout.write(f"Origen: {empresa.nombre} ({empresa.slug})")
        for key, value in counts.items():
            self.stdout.write(f"- {key}: {value}")
        self.stdout.write(f"- imagenes: {len(image_names)}")

    def _subir_imagenes(self, image_names):
        image_map = {}
        uploaded_now = []
        media_root = Path(settings.MEDIA_ROOT).resolve()

        for source_name in image_names:
            source_path = (media_root / source_name).resolve()
            target_name = source_name.replace("\\", "/")

            if default_storage.exists(target_name):
                if self._mismo_contenido(source_path, target_name):
                    image_map[source_name] = target_name
                    continue

            with source_path.open("rb") as stream:
                saved_name = default_storage.save(
                    target_name,
                    File(stream, name=source_path.name),
                )
            uploaded_now.append(saved_name)
            if not default_storage.exists(saved_name):
                raise CommandError(f"R2 no confirmo la subida de {source_name}.")
            image_map[source_name] = saved_name

        return image_map, uploaded_now

    def _mismo_contenido(self, local_path, remote_name):
        with local_path.open("rb") as local:
            local_hash = self._hash_stream(local)
        with default_storage.open(remote_name, "rb") as remote:
            remote_hash = self._hash_stream(remote)
        return local_hash == remote_hash

    @staticmethod
    def _hash_stream(stream):
        digest = hashlib.sha256()
        while True:
            chunk = stream.read(1024 * 1024)
            if not chunk:
                break
            digest.update(chunk)
        return digest.hexdigest()

    def _limpiar_subidas(self, uploaded_names):
        for name in reversed(uploaded_names):
            try:
                default_storage.delete(name)
            except Exception as exc:
                self.stderr.write(f"No se pudo limpiar {name}: {exc}")

    @staticmethod
    def _imagen_mapeada(field_file, image_map):
        if not field_file or not field_file.name:
            return None
        return image_map[field_file.name]

    @staticmethod
    def _restaurar_orden(model, instance, source_order):
        if instance.orden == source_order:
            return
        model.objects.filter(pk=instance.pk).update(orden=source_order)
        instance.orden = source_order

    def _migrar_datos(self, alias, source_company, image_map):
        company_defaults = {
            "nombre": source_company.nombre,
            "subdominio": source_company.subdominio,
            "dominio_personalizado": source_company.dominio_personalizado,
            "logo": self._imagen_mapeada(source_company.logo, image_map),
            "imagen_sucursales": self._imagen_mapeada(
                source_company.imagen_sucursales,
                image_map,
            ),
            "imagen_sucursales_url": source_company.imagen_sucursales_url,
            "color_principal": source_company.color_principal,
            "color_secundario": source_company.color_secundario,
            "color_acento": source_company.color_acento,
            "color_texto": source_company.color_texto,
            "color_fondo": source_company.color_fondo,
            "telefono": source_company.telefono,
            "correo": source_company.correo,
            "direccion": source_company.direccion,
            "sitio_web": source_company.sitio_web,
            "instagram_url": source_company.instagram_url,
            "whatsapp_url": source_company.whatsapp_url,
            "facebook_url": source_company.facebook_url,
            "tiktok_url": source_company.tiktok_url,
            "tiene_envios": source_company.tiene_envios,
            "cobra_impuesto": source_company.cobra_impuesto,
            "productos_con_imagen": source_company.productos_con_imagen,
            "modo_inventario": source_company.modo_inventario,
            "activa": source_company.activa,
            "creada_por": None,
        }
        target_company, _ = Empresa.objects.update_or_create(
            slug=source_company.slug,
            defaults=company_defaults,
        )

        self._migrar_menu(alias, source_company, target_company)
        self._migrar_sobre_nosotros(
            alias,
            source_company,
            target_company,
            image_map,
        )
        self._migrar_sucursales(alias, source_company, target_company, image_map)
        family_map = self._migrar_familias(
            alias,
            source_company,
            target_company,
            image_map,
        )
        category_map = self._migrar_categorias(
            alias,
            source_company,
            target_company,
            family_map,
            image_map,
        )
        product_map = self._migrar_productos(
            alias,
            source_company,
            target_company,
            family_map,
            category_map,
            image_map,
        )
        self._migrar_paquetes(
            alias,
            source_company,
            target_company,
            product_map,
            image_map,
        )
        self._migrar_banners(alias, source_company, target_company, image_map)
        return target_company

    def _migrar_menu(self, alias, source_company, target_company):
        source_items = list(
            ItemMenuEmpresa.objects.using(alias)
            .filter(empresa=source_company)
            .order_by("orden", "pk")
        )
        ItemMenuEmpresa.objects.filter(empresa=target_company).update(
            orden=F("orden") + 1000
        )
        for item in source_items:
            target, _ = ItemMenuEmpresa.objects.update_or_create(
                empresa=target_company,
                clave=item.clave,
                defaults={
                    "texto": item.texto,
                    "ruta": item.ruta,
                    "orden": item.orden,
                    "activo": item.activo,
                    "abre_en_nueva_pestana": item.abre_en_nueva_pestana,
                },
            )
            self._restaurar_orden(ItemMenuEmpresa, target, item.orden)

    def _migrar_sobre_nosotros(
        self,
        alias,
        source_company,
        target_company,
        image_map,
    ):
        source = SobreNosotrosEmpresa.objects.using(alias).get(
            empresa=source_company
        )
        SobreNosotrosEmpresa.objects.update_or_create(
            empresa=target_company,
            defaults={
                "titulo": source.titulo,
                "introduccion": source.introduccion,
                "historia": source.historia,
                "mision": source.mision,
                "vision": source.vision,
                "valores": source.valores,
                "compromiso": source.compromiso,
                "imagen": self._imagen_mapeada(source.imagen, image_map),
                "imagen_url": source.imagen_url,
            },
        )

    def _migrar_sucursales(
        self,
        alias,
        source_company,
        target_company,
        image_map,
    ):
        source_items = SucursalEmpresa.objects.using(alias).filter(
            empresa=source_company
        )
        for source in source_items.order_by("orden", "pk"):
            target, _ = SucursalEmpresa.objects.update_or_create(
                empresa=target_company,
                nombre=source.nombre,
                defaults={
                    "direccion": source.direccion,
                    "telefono": source.telefono,
                    "horario": source.horario,
                    "google_maps_url": source.google_maps_url,
                    "imagen": self._imagen_mapeada(source.imagen, image_map),
                    "imagen_url": source.imagen_url,
                    "latitud": source.latitud,
                    "longitud": source.longitud,
                    "orden": source.orden,
                    "activa": source.activa,
                },
            )
            self._restaurar_orden(SucursalEmpresa, target, source.orden)

    def _migrar_familias(
        self,
        alias,
        source_company,
        target_company,
        image_map,
    ):
        mapping = {}
        source_items = Familia.objects.using(alias).filter(empresa=source_company)
        for source in source_items.order_by("orden", "pk"):
            target, _ = Familia.objects.update_or_create(
                empresa=target_company,
                nombre=source.nombre,
                defaults={
                    "descripcion": source.descripcion,
                    "imagen": self._imagen_mapeada(source.imagen, image_map),
                    "imagen_url": source.imagen_url,
                    "activa": source.activa,
                    "orden": source.orden,
                },
            )
            self._restaurar_orden(Familia, target, source.orden)
            mapping[source.pk] = target
        return mapping

    def _migrar_categorias(
        self,
        alias,
        source_company,
        target_company,
        family_map,
        image_map,
    ):
        mapping = {}
        source_items = Categoria.objects.using(alias).filter(empresa=source_company)
        for source in source_items.order_by("orden", "pk"):
            target, _ = Categoria.objects.update_or_create(
                empresa=target_company,
                nombre=source.nombre,
                defaults={
                    "familia": family_map[source.familia_id],
                    "descripcion": source.descripcion,
                    "imagen": self._imagen_mapeada(source.imagen, image_map),
                    "imagen_url": source.imagen_url,
                    "activa": source.activa,
                    "orden": source.orden,
                },
            )
            self._restaurar_orden(Categoria, target, source.orden)
            mapping[source.pk] = target
        return mapping

    def _migrar_productos(
        self,
        alias,
        source_company,
        target_company,
        family_map,
        category_map,
        image_map,
    ):
        source_items = list(
            Producto.objects.using(alias)
            .filter(empresa=source_company)
            .order_by("pk")
        )
        target_items = []
        for source in source_items:
            target_items.append(
                Producto(
                    empresa=target_company,
                    familia=family_map[source.familia_id],
                    categoria=category_map[source.categoria_id],
                    tipo_item=source.tipo_item,
                    codigo_interno=source.codigo_interno,
                    codigo_barra=source.codigo_barra,
                    nombre=source.nombre,
                    descripcion=source.descripcion,
                    imagen_principal=self._imagen_mapeada(
                        source.imagen_principal,
                        image_map,
                    ),
                    imagen_url=source.imagen_url,
                    precio=source.precio,
                    existencia=source.existencia,
                    existencia_minima=source.existencia_minima,
                    orden_destacado=source.orden_destacado,
                    activo=source.activo,
                )
            )

        Producto.objects.bulk_create(
            target_items,
            batch_size=200,
            update_conflicts=True,
            unique_fields=["empresa", "codigo_interno"],
            update_fields=[
                "familia",
                "categoria",
                "tipo_item",
                "codigo_barra",
                "nombre",
                "descripcion",
                "imagen_principal",
                "imagen_url",
                "precio",
                "existencia",
                "existencia_minima",
                "orden_destacado",
                "activo",
            ],
        )

        by_code = {
            product.codigo_interno: product
            for product in Producto.objects.filter(
                empresa=target_company,
                codigo_interno__in=[item.codigo_interno for item in source_items],
            )
        }
        if len(by_code) != len(source_items):
            raise CommandError("No se recuperaron todos los productos migrados.")
        return {
            source.pk: by_code[source.codigo_interno]
            for source in source_items
        }

    def _migrar_paquetes(
        self,
        alias,
        source_company,
        target_company,
        product_map,
        image_map,
    ):
        package_map = {}
        source_items = PaqueteCatalogo.objects.using(alias).filter(
            empresa=source_company
        )
        for source in source_items.order_by("orden", "pk"):
            target, _ = PaqueteCatalogo.objects.update_or_create(
                empresa=target_company,
                codigo=source.codigo,
                defaults={
                    "tipo": source.tipo,
                    "nombre": source.nombre,
                    "descripcion": source.descripcion,
                    "precio_normal": source.precio_normal,
                    "precio_paquete": source.precio_paquete,
                    "porcentaje_descuento": source.porcentaje_descuento,
                    "imagen": self._imagen_mapeada(source.imagen, image_map),
                    "imagen_url": source.imagen_url,
                    "destacado": source.destacado,
                    "activo": source.activo,
                    "orden": source.orden,
                },
            )
            self._restaurar_orden(PaqueteCatalogo, target, source.orden)
            package_map[source.pk] = target

        source_components = PaqueteProducto.objects.using(alias).filter(
            paquete__empresa=source_company
        )
        for source in source_components.order_by("paquete_id", "orden", "pk"):
            target, _ = PaqueteProducto.objects.update_or_create(
                paquete=package_map[source.paquete_id],
                producto=product_map[source.producto_id],
                defaults={
                    "cantidad": source.cantidad,
                    "orden": source.orden,
                },
            )
            self._restaurar_orden(PaqueteProducto, target, source.orden)

    def _migrar_banners(
        self,
        alias,
        source_company,
        target_company,
        image_map,
    ):
        source_items = BannerPromocional.objects.using(alias).filter(
            empresa=source_company
        )
        for source in source_items.order_by("orden", "pk"):
            target, _ = BannerPromocional.objects.update_or_create(
                empresa=target_company,
                titulo=source.titulo,
                defaults={
                    "subtitulo": source.subtitulo,
                    "texto_boton": source.texto_boton,
                    "url_boton": source.url_boton,
                    "imagen": self._imagen_mapeada(source.imagen, image_map),
                    "imagen_url": source.imagen_url,
                    "texto_alternativo": source.texto_alternativo,
                    "orden": source.orden,
                    "activo": source.activo,
                    "fecha_inicio": source.fecha_inicio,
                    "fecha_fin": source.fecha_fin,
                },
            )
            self._restaurar_orden(BannerPromocional, target, source.orden)

    def _verificar_resultado(self, target_company, source_counts, image_map):
        target_counts = {
            "menus": target_company.items_menu.count(),
            "sobre_nosotros": SobreNosotrosEmpresa.objects.filter(
                empresa=target_company
            ).count(),
            "sucursales": target_company.sucursales.count(),
            "familias": target_company.familias.count(),
            "categorias": target_company.categorias.count(),
            "productos": target_company.productos.count(),
            "paquetes": target_company.paquetes_catalogo.count(),
            "componentes": PaqueteProducto.objects.filter(
                paquete__empresa=target_company
            ).count(),
            "banners": target_company.banners_promocionales.count(),
        }
        if target_counts != source_counts:
            raise CommandError(
                f"Los conteos finales no coinciden: {target_counts} != {source_counts}"
            )

        missing_images = [
            target_name
            for target_name in image_map.values()
            if not default_storage.exists(target_name)
        ]
        if missing_images:
            raise CommandError(
                "R2 no contiene todas las imagenes: " + ", ".join(missing_images)
            )

        for key, value in target_counts.items():
            self.stdout.write(f"Destino {key}: {value}")
        self.stdout.write(f"Destino imagenes R2: {len(image_map)}")
