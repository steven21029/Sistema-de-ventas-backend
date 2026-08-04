# Configuracion de Cloudflare R2

Cloudflare R2 almacena los archivos de imagen. Supabase conserva los datos y
las rutas de esos archivos; no guarda los binarios de las imagenes.

## Variables locales

Completar estas variables en `.env` sin comillas:

```env
R2_STORAGE_ENABLED=True
R2_ACCESS_KEY_ID=CLAVE_DE_ACCESO_R2
R2_SECRET_ACCESS_KEY=CLAVE_SECRETA_R2
R2_BUCKET_NAME=sistema-ventas-media
R2_ENDPOINT_URL=https://ACCOUNT_ID.r2.cloudflarestorage.com
R2_PUBLIC_BASE_URL=https://URL_PUBLICA.r2.dev
R2_REGION_NAME=auto
```

Reglas:

- No guardar credenciales reales en Git, documentos o conversaciones.
- `R2_ENDPOINT_URL` es el endpoint S3 mostrado por Cloudflare.
- `R2_PUBLIC_BASE_URL` es la URL publica del bucket, sin `/` al final.
- La URL `r2.dev` se usa solamente durante las pruebas. En produccion debe
  reemplazarse por un dominio personalizado administrado en Cloudflare.
- El token debe tener `Object Read & Write` y acceso solo al bucket de medios.

## Comportamiento de Django

- Con `R2_STORAGE_ENABLED=False`, los archivos usan `media/` local.
- Con `R2_STORAGE_ENABLED=True`, los `ImageField` usan Cloudflare R2.
- Los objetos se guardan bajo el prefijo `media/`.
- Los archivos con nombres repetidos no sobrescriben los anteriores.
- Las URLs publicas no incluyen firmas temporales porque las imagenes del
  catalogo son contenido publico.
- WhiteNoise continua administrando los archivos estaticos de Django.

## Variables en Render

Despues de validar una subida local, copiar las mismas siete variables a
`Render > Environment`. El valor secreto se copia directamente desde el lugar
seguro donde se guardo al crear el token.

## Migracion inicial

- Solo se trasladara la empresa Analiza y sus archivos relacionados.
- La empresa `prueba` y todos sus registros quedan excluidos.
- Primero se validara una subida y eliminacion temporal.
- Despues se copiaran los archivos locales de Analiza conservando sus rutas.
- Finalmente se importaran los registros de Analiza desde SQLite a Supabase.
