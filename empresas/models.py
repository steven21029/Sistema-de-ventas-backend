from urllib.parse import urlparse

from django.conf import settings
from django.core.exceptions import ValidationError
from django.core.validators import RegexValidator
from django.db import models
from django.utils.text import slugify


hex_color_validator = RegexValidator(
    regex=r"^#[0-9A-Fa-f]{6}$",
    message="El color debe tener formato hexadecimal, por ejemplo #d1393d.",
)

subdominio_validator = RegexValidator(
    regex=r"^[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?$",
    message="El subdominio solo puede usar letras minusculas, numeros y guiones.",
)

dominio_validator = RegexValidator(
    regex=(
        r"^(?=.{1,253}$)"
        r"(?:[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?\.)+"
        r"[a-z0-9](?:[a-z0-9-]{0,61}[a-z0-9])?$"
    ),
    message="Escribe solo el dominio, por ejemplo analiza.localhost o tienda.analizahn.com.",
)

SUBDOMINIOS_RESERVADOS = {"admin", "api", "app", "media", "static", "www"}


def _validar_url_red_social(value, dominios_permitidos, nombre_red):
    if not value:
        return

    url = urlparse(value)
    dominio = (url.hostname or "").lower()
    if url.scheme != "https":
        raise ValidationError(f"La URL de {nombre_red} debe usar HTTPS.")

    if not any(
        dominio == permitido or dominio.endswith(f".{permitido}")
        for permitido in dominios_permitidos
    ):
        raise ValidationError(
            f"La URL debe pertenecer al dominio oficial de {nombre_red}."
        )


def validar_url_instagram(value):
    _validar_url_red_social(value, {"instagram.com"}, "Instagram")


def validar_url_whatsapp(value):
    _validar_url_red_social(value, {"wa.me", "whatsapp.com"}, "WhatsApp")


def validar_url_facebook(value):
    _validar_url_red_social(value, {"facebook.com", "fb.com"}, "Facebook")


def validar_url_tiktok(value):
    _validar_url_red_social(value, {"tiktok.com"}, "TikTok")

MENU_PREDETERMINADO = [
    ("inicio", "Inicio", "/", 1),
    ("examenes", "Examenes", "/examenes", 2),
    ("perfiles", "Perfiles", "/perfiles", 3),
    ("servicios", "Servicios", "/servicios", 4),
    ("promociones", "Promociones", "/promociones", 5),
    ("sucursales", "Sucursales", "/sucursales", 6),
    ("contacto", "Contacto", "/contacto", 7),
    ("sobre_nosotros", "Sobre nosotros", "/sobre-nosotros", 8),
]

MENU_RUTAS = {
    clave: ruta for clave, _texto, ruta, _orden in MENU_PREDETERMINADO
}
MENU_CLAVES = tuple(MENU_RUTAS)


class Empresa(models.Model):
    class ModoInventario(models.TextChoices):
        INVENTARIADO = "inventariado", "Con inventario"
        SIN_INVENTARIO = "sin_inventario", "Sin inventario (servicios)"
        MIXTO = "mixto", "Mixto"

    nombre = models.CharField(max_length=150, unique=True)
    slug = models.SlugField(max_length=170, unique=True, blank=True)
    subdominio = models.CharField(
        max_length=63,
        unique=True,
        null=True,
        blank=True,
        validators=[subdominio_validator],
        help_text="Ejemplo: analiza para abrir analiza.localhost o analiza.tuapp.com.",
    )
    dominio_personalizado = models.CharField(
        max_length=255,
        unique=True,
        null=True,
        blank=True,
        validators=[dominio_validator],
        help_text="Ejemplo: tienda.analizahn.com. No incluir http ni puerto.",
    )
    logo = models.ImageField(upload_to="empresas/logos/", blank=True, null=True)
    imagen_sucursales = models.ImageField(
        upload_to="empresas/sucursales/",
        blank=True,
        null=True,
        help_text="Imagen general que usaran todas las sucursales de esta empresa.",
    )
    imagen_sucursales_url = models.URLField(
        blank=True,
        help_text="URL externa futura para la imagen general de sucursales.",
    )

    color_principal = models.CharField(
        max_length=7,
        default="#d1393d",
        validators=[hex_color_validator],
    )
    color_secundario = models.CharField(
        max_length=7,
        default="#e94a51",
        validators=[hex_color_validator],
    )
    color_acento = models.CharField(
        max_length=7,
        default="#2d4b77",
        validators=[hex_color_validator],
    )
    color_texto = models.CharField(
        max_length=7,
        default="#000000",
        validators=[hex_color_validator],
    )
    color_fondo = models.CharField(
        max_length=7,
        default="#ffffff",
        validators=[hex_color_validator],
    )

    telefono = models.CharField(max_length=30, blank=True)
    correo = models.EmailField(blank=True)
    direccion = models.TextField(blank=True)
    sitio_web = models.URLField(blank=True)
    instagram_url = models.URLField(
        max_length=500,
        blank=True,
        validators=[validar_url_instagram],
    )
    whatsapp_url = models.URLField(
        max_length=500,
        blank=True,
        validators=[validar_url_whatsapp],
        help_text="Ejemplo: https://wa.me/50499999999",
    )
    facebook_url = models.URLField(
        max_length=500,
        blank=True,
        validators=[validar_url_facebook],
    )
    tiktok_url = models.URLField(
        max_length=500,
        blank=True,
        validators=[validar_url_tiktok],
    )

    tiene_envios = models.BooleanField(
        default=False,
        help_text="Si esta activo, la empresa podra ofrecer envio local y envio nacional.",
    )
    cobra_impuesto = models.BooleanField(
        default=True,
        help_text="Si esta activo, las ventas calcularan el 15% de ISV.",
    )
    productos_con_imagen = models.BooleanField(
        default=True,
        help_text=(
            "Si esta activo, los productos pueden mostrar imagenes individuales. "
            "Si esta desactivado, se usan imagenes de familias y categorias."
        ),
    )
    modo_inventario = models.CharField(
        max_length=20,
        choices=ModoInventario.choices,
        default=ModoInventario.INVENTARIADO,
        help_text=(
            "Define si la empresa vende productos fisicos, servicios o ambos."
        ),
    )
    activa = models.BooleanField(default=True)
    creada_por = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="empresas_creadas",
    )
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["nombre"]
        verbose_name = "empresa"
        verbose_name_plural = "empresas"

    def __str__(self):
        return self.nombre

    @property
    def opciones_entrega_disponibles(self):
        if self.tiene_envios:
            return ["envio_local", "envio_nacional"]

        return ["retiro_en_local"]

    @property
    def permite_productos_fisicos(self):
        return self.modo_inventario in [
            self.ModoInventario.INVENTARIADO,
            self.ModoInventario.MIXTO,
        ]

    @property
    def permite_servicios(self):
        return self.modo_inventario in [
            self.ModoInventario.SIN_INVENTARIO,
            self.ModoInventario.MIXTO,
        ]

    @property
    def imagen_sucursales_final(self):
        if self.imagen_sucursales_url:
            return self.imagen_sucursales_url

        if self.imagen_sucursales:
            return self.imagen_sucursales.url

        return None

    def clean(self):
        super().clean()
        self._normalizar_dominios()
        self._validar_cambio_modo_inventario()

        if self.subdominio in SUBDOMINIOS_RESERVADOS:
            raise ValidationError(
                {"subdominio": "Este subdominio esta reservado para el sistema."}
            )

    def save(self, *args, **kwargs):
        es_nueva = self.pk is None
        self._normalizar_dominios()
        self._validar_cambio_modo_inventario()
        if not self.slug:
            self.slug = self._generar_slug_unico()
        super().save(*args, **kwargs)

        if es_nueva:
            self.crear_menu_predeterminado()
            SobreNosotrosEmpresa.objects.get_or_create(empresa=self)

    def crear_menu_predeterminado(self):
        for clave, texto, ruta, orden in MENU_PREDETERMINADO:
            ItemMenuEmpresa.objects.get_or_create(
                empresa=self,
                clave=clave,
                defaults={
                    "texto": texto,
                    "ruta": ruta,
                    "orden": orden,
                    "activo": True,
                },
            )

    @classmethod
    def resolver_por_host(cls, host):
        host_normalizado = cls.normalizar_host(host)
        if not host_normalizado:
            return None

        empresa = cls.objects.filter(
            dominio_personalizado__iexact=host_normalizado,
            activa=True,
        ).first()
        if empresa:
            return empresa

        subdominio = cls.extraer_subdominio(host_normalizado)
        if not subdominio:
            return None

        return cls.objects.filter(subdominio__iexact=subdominio, activa=True).first()

    @staticmethod
    def normalizar_host(host):
        host = (host or "").strip().lower()
        if not host:
            return ""

        valor_parseable = host if "://" in host else f"//{host}"
        parsed = urlparse(valor_parseable)
        hostname = parsed.hostname or host.split("/")[0].split(":")[0]
        return hostname.strip(".").lower()

    @staticmethod
    def extraer_subdominio(host):
        partes = host.split(".")
        if len(partes) < 2:
            return ""

        subdominio = partes[0].strip().lower()
        if subdominio in SUBDOMINIOS_RESERVADOS:
            return ""

        return subdominio

    def _normalizar_dominios(self):
        self.subdominio = (self.subdominio or "").strip().lower() or None
        self.dominio_personalizado = (
            self.normalizar_host(self.dominio_personalizado) or None
        )

    def _validar_cambio_modo_inventario(self):
        if not self.pk:
            return

        modo_anterior = (
            Empresa.objects.filter(pk=self.pk)
            .values_list("modo_inventario", flat=True)
            .first()
        )
        if (
            modo_anterior
            and modo_anterior != self.modo_inventario
            and self.productos.exists()
        ):
            raise ValidationError(
                {
                    "modo_inventario": (
                        "No se puede cambiar el modo porque la empresa ya tiene "
                        "productos o servicios. La conversion requiere una revision "
                        "controlada de esos registros."
                    )
                }
            )

    def _generar_slug_unico(self):
        base_slug = slugify(self.nombre) or "empresa"
        slug = base_slug
        contador = 2

        while Empresa.objects.filter(slug=slug).exclude(pk=self.pk).exists():
            slug = f"{base_slug}-{contador}"
            contador += 1

        return slug


class ItemMenuEmpresa(models.Model):
    empresa = models.ForeignKey(
        Empresa,
        on_delete=models.CASCADE,
        related_name="items_menu",
    )
    clave = models.SlugField(
        max_length=60,
        choices=[
            (clave, texto) for clave, texto, _ruta, _orden in MENU_PREDETERMINADO
        ],
        help_text="Modulo oficial del sistema. No puede cambiarse despues de crearlo.",
    )
    texto = models.CharField(max_length=80)
    ruta = models.CharField(
        max_length=180,
        help_text="Ruta del frontend, por ejemplo /examenes o una URL externa.",
    )
    orden = models.PositiveIntegerField(default=0)
    activo = models.BooleanField(default=True)
    abre_en_nueva_pestana = models.BooleanField(default=False)
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["empresa__nombre", "orden", "texto"]
        verbose_name = "item de menu de empresa"
        verbose_name_plural = "items de menu de empresa"
        constraints = [
            models.UniqueConstraint(
                fields=["empresa", "clave"],
                name="item_menu_clave_unica_por_empresa",
            ),
            models.CheckConstraint(
                condition=models.Q(clave__in=MENU_CLAVES),
                name="item_menu_clave_oficial",
            ),
        ]
        indexes = [
            models.Index(fields=["empresa", "activo", "orden"]),
        ]

    def __str__(self):
        return f"{self.empresa} - {self.texto}"

    def save(self, *args, **kwargs):
        if self.clave not in MENU_RUTAS:
            raise ValidationError(
                {"clave": "Debes seleccionar un modulo oficial del sistema."}
            )

        if self.pk:
            clave_original = (
                ItemMenuEmpresa.objects.filter(pk=self.pk)
                .values_list("clave", flat=True)
                .first()
            )
            if clave_original and clave_original != self.clave:
                raise ValidationError(
                    {"clave": "El modulo de un item existente no puede cambiarse."}
                )

        self.ruta = MENU_RUTAS[self.clave]
        self.abre_en_nueva_pestana = False
        update_fields = kwargs.get("update_fields")
        if update_fields is not None:
            kwargs["update_fields"] = set(update_fields) | {
                "ruta",
                "abre_en_nueva_pestana",
            }

        if not self.pk and self.orden == 0:
            ultimo_orden = (
                ItemMenuEmpresa.objects.filter(empresa=self.empresa)
                .aggregate(max_orden=models.Max("orden"))
                .get("max_orden")
                or 0
            )
            self.orden = ultimo_orden + 1

        orden_repetido = ItemMenuEmpresa.objects.filter(
            empresa=self.empresa,
            orden=self.orden,
        )
        if self.pk:
            orden_repetido = orden_repetido.exclude(pk=self.pk)
        if orden_repetido.exists():
            raise ValidationError(
                {"orden": "Ya existe un modulo con este orden en la empresa."}
            )

        super().save(*args, **kwargs)


class SobreNosotrosEmpresa(models.Model):
    empresa = models.OneToOneField(
        Empresa,
        on_delete=models.CASCADE,
        related_name="sobre_nosotros",
    )
    titulo = models.CharField(max_length=180, default="Sobre nosotros")
    introduccion = models.TextField(blank=True)
    historia = models.TextField(blank=True)
    mision = models.TextField(blank=True)
    vision = models.TextField(blank=True)
    valores = models.TextField(
        blank=True,
        help_text="Escribe un valor por linea.",
    )
    compromiso = models.TextField(blank=True)
    imagen = models.ImageField(
        upload_to="empresas/sobre_nosotros/",
        blank=True,
        null=True,
    )
    imagen_url = models.URLField(
        blank=True,
        help_text="URL externa futura para almacenamiento en linea.",
    )
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "contenido de Sobre nosotros"
        verbose_name_plural = "contenidos de Sobre nosotros"

    def __str__(self):
        return f"Sobre nosotros - {self.empresa}"

    @property
    def imagen_final(self):
        if self.imagen_url:
            return self.imagen_url
        if self.imagen:
            return self.imagen.url
        return None

    @property
    def valores_lista(self):
        return [
            valor.strip()
            for valor in self.valores.splitlines()
            if valor.strip()
        ]


class SucursalEmpresa(models.Model):
    empresa = models.ForeignKey(
        Empresa,
        on_delete=models.CASCADE,
        related_name="sucursales",
    )
    nombre = models.CharField(max_length=150)
    direccion = models.TextField()
    telefono = models.CharField(max_length=30, blank=True)
    horario = models.CharField(max_length=180, blank=True)
    google_maps_url = models.URLField(blank=True)
    imagen = models.ImageField(
        upload_to="empresas/sucursales/",
        blank=True,
        null=True,
    )
    imagen_url = models.URLField(
        blank=True,
        help_text="URL externa futura para almacenamiento en linea.",
    )
    latitud = models.DecimalField(
        max_digits=20,
        decimal_places=15,
        null=True,
        blank=True,
    )
    longitud = models.DecimalField(
        max_digits=20,
        decimal_places=15,
        null=True,
        blank=True,
    )
    orden = models.PositiveIntegerField(default=0)
    activa = models.BooleanField(default=True)
    fecha_creacion = models.DateTimeField(auto_now_add=True)
    fecha_actualizacion = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["empresa__nombre", "orden", "nombre"]
        verbose_name = "sucursal de empresa"
        verbose_name_plural = "sucursales de empresa"
        indexes = [
            models.Index(fields=["empresa", "activa", "orden"]),
        ]

    def __str__(self):
        return f"{self.empresa} - {self.nombre}"

    @property
    def imagen_final(self):
        if self.empresa.imagen_sucursales_url:
            return self.empresa.imagen_sucursales_url

        if self.empresa.imagen_sucursales:
            return self.empresa.imagen_sucursales.url

        return None

    def save(self, *args, **kwargs):
        if not self.pk and self.orden == 0:
            ultimo_orden = (
                SucursalEmpresa.objects.filter(empresa=self.empresa)
                .aggregate(max_orden=models.Max("orden"))
                .get("max_orden")
                or 0
            )
            self.orden = ultimo_orden + 1

        super().save(*args, **kwargs)
