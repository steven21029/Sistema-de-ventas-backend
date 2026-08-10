# Registro y verificacion del comprador

Contrato para el formulario de creacion de cuenta. Las rutas funcionan bajo
`/api/v1/` y `/api/`.

## Crear cuenta

```http
POST /api/v1/usuarios/registro-comprador/
Content-Type: application/json
```

```json
{
  "empresa_slug": "Analiza",
  "nombre_completo": "Maria Rivera",
  "email": "maria@example.com",
  "telefono": "99999999",
  "numero_identidad": "0801199912345",
  "password": "ClaveSegura123!",
  "password_confirmacion": "ClaveSegura123!",
  "acepta_terminos": true,
  "acepta_privacidad": true
}
```

Reglas oficiales del backend:

- `nombre_completo`: solo letras Unicode y espacios. No acepta numeros ni
  signos.
- `telefono`: solo digitos, enviado como texto, con un maximo de 30.
- `numero_identidad`: exactamente 13 digitos, enviado como texto.
- `password`: cumple los validadores de seguridad de Django.
- `password_confirmacion`: debe coincidir con `password`.
- El correo y la identidad deben ser unicos dentro de su alcance.

Un `201 Created` significa que la cuenta inactiva, el codigo y el correo se
crearon correctamente y que el proveedor SMTP acepto un mensaje. Si SMTP no
confirma el envio, la API devuelve `503` y revierte la cuenta y el codigo.

## Verificar correo

```http
POST /api/v1/usuarios/verificar-correo/
Content-Type: application/json

{
  "email": "maria@example.com",
  "codigo": "012345"
}
```

El codigo debe enviarse como texto de exactamente seis digitos para conservar
ceros iniciales. Vence a los 15 minutos y admite un maximo de cinco intentos.

## Reenviar codigo

```http
POST /api/v1/usuarios/reenviar-verificacion/
Content-Type: application/json

{
  "email": "maria@example.com"
}
```

Solo debe llamarse cuando el comprador pulse la accion de reenvio. El registro
inicial ya envia un codigo. Hay que esperar al menos 60 segundos entre
solicitudes. Mostrar "Codigo reenviado" solamente despues de recibir `200`.
Un `400` contiene una validacion por campo y un `503` indica que SMTP no
confirmo el envio.

## Controles del frontend

Nombre completo:

```jsx
<input
  type="text"
  autoComplete="name"
  value={nombreCompleto}
  onChange={(event) =>
    setNombreCompleto(event.target.value.replace(/[^\p{L}\s]/gu, ""))
  }
/>
```

Telefono e identidad deben seguir siendo `type="text"`, no `number`, para no
perder ceros iniciales:

```jsx
<input
  type="text"
  inputMode="numeric"
  pattern="[0-9]*"
  maxLength={30}
  value={telefono}
  onChange={(event) => setTelefono(event.target.value.replace(/\D/g, ""))}
/>

<input
  type="text"
  inputMode="numeric"
  pattern="[0-9]{13}"
  maxLength={13}
  value={numeroIdentidad}
  onChange={(event) =>
    setNumeroIdentidad(event.target.value.replace(/\D/g, ""))
  }
/>
```

El codigo usa el mismo patron numerico con `maxLength={6}` y siempre se envia
como cadena.

El ojo de contrasena es exclusivamente visual. Cada campo debe tener su propio
estado para mostrar u ocultar y un boton `type="button"` para evitar enviar el
formulario:

```jsx
const [mostrarPassword, setMostrarPassword] = useState(false);

<div className="password-field">
  <input
    type={mostrarPassword ? "text" : "password"}
    autoComplete="new-password"
    value={password}
    onChange={(event) => setPassword(event.target.value)}
  />
  <button
    type="button"
    aria-label={mostrarPassword ? "Ocultar contrasena" : "Mostrar contrasena"}
    aria-pressed={mostrarPassword}
    onClick={() => setMostrarPassword((actual) => !actual)}
  >
    {mostrarPassword ? <EyeOff aria-hidden="true" /> : <Eye aria-hidden="true" />}
  </button>
</div>
```

Usar `Eye` y `EyeOff` de `lucide-react`. Repetir el control con otro estado
para `password_confirmacion`. Los errores devueltos por la API deben mostrarse
debajo del campo que coincida con la clave de la respuesta.

## Entrega de Brevo

Una respuesta exitosa confirma la aceptacion SMTP, no la ubicacion final en la
bandeja de Gmail. Si el mensaje no aparece, revisar Spam, Promociones y el log
transaccional de Brevo para identificar `delivered`, `deferred`, `blocked` o
`bounced`. Para produccion se debe autenticar un dominio remitente con DKIM y
DMARC.
