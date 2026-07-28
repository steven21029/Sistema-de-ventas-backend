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

MENU_PREDETERMINADO = [
    ("inicio", "Inicio", "/", 1),
    ("examenes", "Examenes", "/examenes", 2),
    ("perfiles", "Perfiles", "/perfiles", 3),
    ("servicios", "Servicios", "/servicios", 4),
    ("promociones", "Promociones", "/promociones", 5),
    ("sucursales", "Sucursales", "/sucursales", 6),
    ("contacto", "Contacto", "/contacto", 7),
]


class Empresa(models.Model):
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

    tiene_envios = models.BooleanField(
        default=False,
        help_text="Si esta activo, la empresa podra ofrecer envio local y envio nacional.",
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
    def imagen_sucursales_final(self):
        if self.imagen_sucursales_url:
            return self.imagen_sucursales_url

        if self.imagen_sucursales:
            return self.imagen_sucursales.url

        return None

    def clean(self):
        super().clean()
        self._normalizar_dominios()

        if self.subdominio in SUBDOMINIOS_RESERVADOS:
            raise ValidationError(
                {"subdominio": "Este subdominio esta reservado para el sistema."}
            )

    def save(self, *args, **kwargs):
        es_nueva = self.pk is None
        self._normalizar_dominios()
        if not self.slug:
            self.slug = self._generar_slug_unico()
        super().save(*args, **kwargs)

        if es_nueva:
            self.crear_menu_predeterminado()

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
        help_text="Identificador estable, por ejemplo inicio, catalogo o contacto.",
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
            )
        ]
        indexes = [
            models.Index(fields=["empresa", "activo", "orden"]),
        ]

    def __str__(self):
        return f"{self.empresa} - {self.texto}"

    def save(self, *args, **kwargs):
        if not self.pk and self.orden == 0:
            ultimo_orden = (
                ItemMenuEmpresa.objects.filter(empresa=self.empresa)
                .aggregate(max_orden=models.Max("orden"))
                .get("max_orden")
                or 0
            )
            self.orden = ultimo_orden + 1

        super().save(*args, **kwargs)


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
