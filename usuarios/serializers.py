from django.contrib.auth import authenticate, get_user_model
from django.contrib.auth.password_validation import validate_password
from django.core.exceptions import ValidationError as DjangoValidationError
from django.db import transaction
from django.utils import timezone
from rest_framework import serializers
from rest_framework.exceptions import AuthenticationFailed
from rest_framework_simplejwt.serializers import TokenRefreshSerializer
from rest_framework_simplejwt.tokens import AccessToken, RefreshToken

from empresas.models import Empresa
from .models import CodigoVerificacionCorreo, PerfilUsuario

User = get_user_model()


class UsuarioBasicoSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = [
            "id",
            "username",
            "email",
            "first_name",
            "last_name",
            "is_active",
            "is_superuser",
        ]
        read_only_fields = fields


class PerfilUsuarioSerializer(serializers.ModelSerializer):
    usuario_detalle = UsuarioBasicoSerializer(source="usuario", read_only=True)
    empresa_nombre = serializers.CharField(source="empresa.nombre", read_only=True)
    rol_nombre = serializers.CharField(source="get_rol_display", read_only=True)

    class Meta:
        model = PerfilUsuario
        fields = [
            "id",
            "usuario",
            "usuario_detalle",
            "empresa",
            "empresa_nombre",
            "rol",
            "rol_nombre",
            "telefono",
            "numero_identidad",
            "correo_verificado",
            "puede_crear_usuarios",
            "activo",
            "fecha_creacion",
            "fecha_actualizacion",
        ]
        read_only_fields = [
            "id",
            "usuario_detalle",
            "empresa_nombre",
            "rol_nombre",
            "fecha_creacion",
            "fecha_actualizacion",
        ]


class LoginJWTSerializer(serializers.Serializer):
    email = serializers.EmailField()
    password = serializers.CharField(write_only=True, trim_whitespace=False)

    def validate(self, attrs):
        email = attrs["email"].strip()
        password = attrs["password"]

        user = User.objects.filter(email__iexact=email).first()
        if not user:
            raise AuthenticationFailed("Credenciales invalidas.")

        user = authenticate(
            request=self.context.get("request"),
            username=user.get_username(),
            password=password,
        )
        if not user:
            raise AuthenticationFailed("Credenciales invalidas.")

        if not user.is_active:
            raise AuthenticationFailed("El usuario esta inactivo.")

        perfil = getattr(user, "perfil", None)
        if user.is_superuser and not perfil:
            perfil, _created = PerfilUsuario.objects.get_or_create(
                usuario=user,
                defaults={"rol": PerfilUsuario.Rol.ADMINISTRADOR_MAESTRO},
            )

        if perfil and not perfil.activo:
            raise AuthenticationFailed("El perfil del usuario esta inactivo.")

        refresh = RefreshToken.for_user(user)
        return {
            "access": str(refresh.access_token),
            "refresh": str(refresh),
            "usuario": UsuarioBasicoSerializer(user).data,
            "perfil": PerfilUsuarioSerializer(perfil).data if perfil else None,
        }


class SesionLimitadaTokenRefreshSerializer(TokenRefreshSerializer):
    def validate(self, attrs):
        refresh = self.token_class(attrs["refresh"])
        limite_sesion = int(refresh["exp"])
        data = super().validate(attrs)
        access = AccessToken(data["access"])

        if int(access["exp"]) > limite_sesion:
            access["exp"] = limite_sesion
            data["access"] = str(access)

        return data


class RegistroCompradorSerializer(serializers.Serializer):
    empresa_slug = serializers.CharField(write_only=True)
    nombre_completo = serializers.CharField(max_length=180)
    email = serializers.EmailField()
    telefono = serializers.CharField(max_length=30)
    numero_identidad = serializers.RegexField(
        regex=r"^\d{13}$",
        error_messages={
            "invalid": "El numero de identidad debe tener exactamente 13 digitos.",
        },
    )
    password = serializers.CharField(write_only=True, trim_whitespace=False)
    password_confirmacion = serializers.CharField(write_only=True, trim_whitespace=False)
    acepta_terminos = serializers.BooleanField(write_only=True)
    acepta_privacidad = serializers.BooleanField(write_only=True)

    def validate_email(self, value):
        email = value.strip().lower()

        if User.objects.filter(email__iexact=email).exists():
            raise serializers.ValidationError("Ya existe un usuario con este correo.")

        username_max_length = User._meta.get_field("username").max_length
        if len(email) > username_max_length:
            raise serializers.ValidationError(
                f"El correo no puede superar {username_max_length} caracteres."
            )

        return email

    def validate_empresa_slug(self, value):
        slug = value.strip()
        try:
            return Empresa.objects.get(slug__iexact=slug, activa=True)
        except Empresa.DoesNotExist as exc:
            raise serializers.ValidationError("La empresa no existe o no esta activa.") from exc

    def validate(self, attrs):
        empresa = attrs["empresa_slug"]
        numero_identidad = attrs["numero_identidad"]

        if PerfilUsuario.objects.filter(
            empresa=empresa,
            numero_identidad=numero_identidad,
        ).exists():
            raise serializers.ValidationError(
                {
                    "numero_identidad": (
                        "Esta identidad ya esta registrada en esta empresa."
                    )
                }
            )

        if attrs["password"] != attrs["password_confirmacion"]:
            raise serializers.ValidationError(
                {"password_confirmacion": "Las contrasenas no coinciden."}
            )

        if not attrs["acepta_terminos"]:
            raise serializers.ValidationError(
                {"acepta_terminos": "Debes aceptar los terminos y condiciones."}
            )

        if not attrs["acepta_privacidad"]:
            raise serializers.ValidationError(
                {"acepta_privacidad": "Debes aceptar la politica de privacidad."}
            )

        usuario_temporal = User(
            username=attrs["email"],
            email=attrs["email"],
        )
        try:
            validate_password(attrs["password"], user=usuario_temporal)
        except DjangoValidationError as exc:
            raise serializers.ValidationError({"password": exc.messages}) from exc

        return attrs

    @transaction.atomic
    def create(self, validated_data):
        empresa = validated_data["empresa_slug"]
        nombre_completo = " ".join(validated_data["nombre_completo"].split())
        partes_nombre = nombre_completo.split(" ", 1)
        nombres = partes_nombre[0]
        apellidos = partes_nombre[1] if len(partes_nombre) > 1 else ""

        usuario = User.objects.create_user(
            username=validated_data["email"],
            email=validated_data["email"],
            password=validated_data["password"],
            first_name=nombres,
            last_name=apellidos,
            is_active=False,
        )

        perfil, _created = PerfilUsuario.objects.get_or_create(usuario=usuario)
        perfil.empresa = empresa
        perfil.rol = PerfilUsuario.Rol.COMPRADOR
        perfil.telefono = validated_data["telefono"].strip()
        perfil.numero_identidad = validated_data["numero_identidad"]
        perfil.correo_verificado = False
        perfil.puede_crear_usuarios = False
        perfil.activo = False
        perfil.full_clean()
        perfil.save()

        codigo = CodigoVerificacionCorreo.crear_para_usuario(usuario)
        codigo.enviar_por_correo()

        return {"usuario": usuario, "perfil": perfil}

    def to_representation(self, instance):
        return {
            "usuario": UsuarioBasicoSerializer(instance["usuario"]).data,
            "perfil": PerfilUsuarioSerializer(instance["perfil"]).data,
        }


class VerificarCorreoSerializer(serializers.Serializer):
    email = serializers.EmailField()
    codigo = serializers.CharField(max_length=CodigoVerificacionCorreo.LONGITUD_CODIGO)

    def validate_email(self, value):
        return value.strip().lower()

    def validate_codigo(self, value):
        codigo = value.strip()
        if not codigo.isdigit() or len(codigo) != CodigoVerificacionCorreo.LONGITUD_CODIGO:
            raise serializers.ValidationError("El codigo debe tener 6 digitos.")

        return codigo

    def validate(self, attrs):
        try:
            usuario = User.objects.get(email__iexact=attrs["email"])
        except User.DoesNotExist as exc:
            raise serializers.ValidationError({"email": "No existe un usuario con este correo."}) from exc

        perfil = getattr(usuario, "perfil", None)
        if not perfil:
            raise serializers.ValidationError(
                {"email": "El usuario no tiene un perfil configurado."}
            )

        if perfil.correo_verificado:
            attrs["usuario"] = usuario
            attrs["perfil"] = perfil
            attrs["codigo_obj"] = None
            return attrs

        codigo_obj = (
            CodigoVerificacionCorreo.objects.filter(
                usuario=usuario,
                tipo=CodigoVerificacionCorreo.Tipo.VERIFICACION_CORREO,
                usado=False,
            )
            .order_by("-fecha_creacion")
            .first()
        )
        if not codigo_obj:
            raise serializers.ValidationError(
                {"codigo": "No hay un codigo activo. Solicita uno nuevo."}
            )

        if codigo_obj.expirado:
            codigo_obj.usado = True
            codigo_obj.save(update_fields=["usado"])
            raise serializers.ValidationError(
                {"codigo": "El codigo expiro. Solicita uno nuevo."}
            )

        if codigo_obj.intentos >= CodigoVerificacionCorreo.MAX_INTENTOS:
            codigo_obj.usado = True
            codigo_obj.save(update_fields=["usado"])
            raise serializers.ValidationError(
                {"codigo": "El codigo supero el numero maximo de intentos."}
            )

        if codigo_obj.codigo != attrs["codigo"]:
            codigo_obj.registrar_intento_fallido()
            raise serializers.ValidationError({"codigo": "El codigo no es valido."})

        attrs["usuario"] = usuario
        attrs["perfil"] = perfil
        attrs["codigo_obj"] = codigo_obj
        return attrs

    @transaction.atomic
    def save(self, **kwargs):
        perfil = self.validated_data["perfil"]
        codigo_obj = self.validated_data["codigo_obj"]

        if not perfil.correo_verificado:
            perfil.correo_verificado = True
            perfil.activo = True
            perfil.save(update_fields=["correo_verificado", "activo", "fecha_actualizacion"])

        usuario = self.validated_data["usuario"]
        if not usuario.is_active:
            usuario.is_active = True
            usuario.save(update_fields=["is_active"])

        if codigo_obj:
            codigo_obj.marcar_como_usado()

        return {"usuario": usuario, "perfil": perfil}

    def to_representation(self, instance):
        return {
            "detalle": "Correo verificado correctamente.",
            "usuario": UsuarioBasicoSerializer(instance["usuario"]).data,
            "perfil": PerfilUsuarioSerializer(instance["perfil"]).data,
        }


class ReenviarVerificacionCorreoSerializer(serializers.Serializer):
    email = serializers.EmailField()

    def validate_email(self, value):
        return value.strip().lower()

    def validate(self, attrs):
        try:
            usuario = User.objects.get(email__iexact=attrs["email"])
        except User.DoesNotExist as exc:
            raise serializers.ValidationError({"email": "No existe un usuario con este correo."}) from exc

        perfil = getattr(usuario, "perfil", None)
        if not perfil:
            raise serializers.ValidationError(
                {"email": "El usuario no tiene un perfil configurado."}
            )

        if perfil.correo_verificado:
            raise serializers.ValidationError(
                {"email": "Este correo ya esta verificado."}
            )

        ultimo_codigo = (
            CodigoVerificacionCorreo.objects.filter(
                usuario=usuario,
                tipo=CodigoVerificacionCorreo.Tipo.VERIFICACION_CORREO,
            )
            .order_by("-fecha_creacion")
            .first()
        )
        if ultimo_codigo:
            tiempo_transcurrido = timezone.now() - ultimo_codigo.fecha_creacion
            if (
                tiempo_transcurrido.total_seconds()
                < CodigoVerificacionCorreo.ESPERA_REENVIO_SEGUNDOS
            ):
                raise serializers.ValidationError(
                    {
                        "email": (
                            "Debes esperar al menos 1 minuto antes de solicitar "
                            "otro codigo."
                        )
                    }
                )

        attrs["usuario"] = usuario
        attrs["perfil"] = perfil
        return attrs

    @transaction.atomic
    def save(self, **kwargs):
        codigo = CodigoVerificacionCorreo.crear_para_usuario(
            self.validated_data["usuario"]
        )
        codigo.enviar_por_correo()
        return {
            "usuario": self.validated_data["usuario"],
            "perfil": self.validated_data["perfil"],
        }

    def to_representation(self, instance):
        return {
            "detalle": "Codigo de verificacion enviado.",
            "usuario": UsuarioBasicoSerializer(instance["usuario"]).data,
            "perfil": PerfilUsuarioSerializer(instance["perfil"]).data,
        }


class SolicitarRecuperacionContrasenaSerializer(serializers.Serializer):
    email = serializers.EmailField()

    def validate_email(self, value):
        return value.strip().lower()

    def validate(self, attrs):
        attrs["usuario"] = User.objects.filter(email__iexact=attrs["email"]).first()
        return attrs

    @transaction.atomic
    def save(self, **kwargs):
        usuario = self.validated_data["usuario"]
        if not usuario:
            return {"codigo_enviado": False}

        ultimo_codigo = (
            CodigoVerificacionCorreo.objects.filter(
                usuario=usuario,
                tipo=CodigoVerificacionCorreo.Tipo.RECUPERACION_CONTRASENA,
            )
            .order_by("-fecha_creacion")
            .first()
        )
        if ultimo_codigo:
            tiempo_transcurrido = timezone.now() - ultimo_codigo.fecha_creacion
            if (
                tiempo_transcurrido.total_seconds()
                < CodigoVerificacionCorreo.ESPERA_REENVIO_SEGUNDOS
            ):
                return {"codigo_enviado": False}

        codigo = CodigoVerificacionCorreo.crear_para_usuario(
            usuario=usuario,
            tipo=CodigoVerificacionCorreo.Tipo.RECUPERACION_CONTRASENA,
        )
        codigo.enviar_por_correo()
        return {"codigo_enviado": True}

    def to_representation(self, instance):
        return {
            "detalle": (
                "Si el correo existe, se enviara un codigo para recuperar "
                "la contrasena."
            )
        }


class ConfirmarRecuperacionContrasenaSerializer(serializers.Serializer):
    email = serializers.EmailField()
    codigo = serializers.CharField(max_length=CodigoVerificacionCorreo.LONGITUD_CODIGO)
    password = serializers.CharField(write_only=True, trim_whitespace=False)
    password_confirmacion = serializers.CharField(write_only=True, trim_whitespace=False)

    def validate_email(self, value):
        return value.strip().lower()

    def validate_codigo(self, value):
        codigo = value.strip()
        if not codigo.isdigit() or len(codigo) != CodigoVerificacionCorreo.LONGITUD_CODIGO:
            raise serializers.ValidationError("El codigo debe tener 6 digitos.")

        return codigo

    def validate(self, attrs):
        if attrs["password"] != attrs["password_confirmacion"]:
            raise serializers.ValidationError(
                {"password_confirmacion": "Las contrasenas no coinciden."}
            )

        try:
            usuario = User.objects.get(email__iexact=attrs["email"])
        except User.DoesNotExist as exc:
            raise serializers.ValidationError(
                {"email": "Los datos de recuperacion no son validos."}
            ) from exc

        codigo_obj = (
            CodigoVerificacionCorreo.objects.filter(
                usuario=usuario,
                tipo=CodigoVerificacionCorreo.Tipo.RECUPERACION_CONTRASENA,
                usado=False,
            )
            .order_by("-fecha_creacion")
            .first()
        )
        if not codigo_obj:
            raise serializers.ValidationError(
                {"codigo": "No hay un codigo activo. Solicita uno nuevo."}
            )

        if codigo_obj.expirado:
            codigo_obj.usado = True
            codigo_obj.save(update_fields=["usado"])
            raise serializers.ValidationError(
                {"codigo": "El codigo expiro. Solicita uno nuevo."}
            )

        if codigo_obj.intentos >= CodigoVerificacionCorreo.MAX_INTENTOS:
            codigo_obj.usado = True
            codigo_obj.save(update_fields=["usado"])
            raise serializers.ValidationError(
                {"codigo": "El codigo supero el numero maximo de intentos."}
            )

        if codigo_obj.codigo != attrs["codigo"]:
            codigo_obj.registrar_intento_fallido()
            raise serializers.ValidationError({"codigo": "El codigo no es valido."})

        usuario_temporal = User(
            username=usuario.get_username(),
            email=usuario.email,
            first_name=usuario.first_name,
            last_name=usuario.last_name,
        )
        try:
            validate_password(attrs["password"], user=usuario_temporal)
        except DjangoValidationError as exc:
            raise serializers.ValidationError({"password": exc.messages}) from exc

        attrs["usuario"] = usuario
        attrs["codigo_obj"] = codigo_obj
        return attrs

    @transaction.atomic
    def save(self, **kwargs):
        usuario = self.validated_data["usuario"]
        usuario.set_password(self.validated_data["password"])
        usuario.save(update_fields=["password"])
        self.validated_data["codigo_obj"].marcar_como_usado()
        return {"usuario": usuario}

    def to_representation(self, instance):
        return {
            "detalle": "Contrasena actualizada correctamente.",
            "usuario": UsuarioBasicoSerializer(instance["usuario"]).data,
        }
