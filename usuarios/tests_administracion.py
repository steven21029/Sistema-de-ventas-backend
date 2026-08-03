from django.contrib.auth import get_user_model
from django.urls import reverse
from rest_framework import status
from rest_framework.test import APITestCase
from rest_framework_simplejwt.token_blacklist.models import BlacklistedToken
from rest_framework_simplejwt.tokens import RefreshToken

from empresas.models import Empresa
from .models import PerfilUsuario


User = get_user_model()


class UsuariosAdministrativosAPITests(APITestCase):
    def setUp(self):
        self.analiza = Empresa.objects.create(
            nombre="Analiza",
            slug="analiza",
            subdominio="analiza",
        )
        self.otra = Empresa.objects.create(
            nombre="Otra empresa",
            slug="otra",
            subdominio="otra",
        )
        self.superuser = User.objects.create_superuser(
            username="root",
            email="root@example.com",
            password="Prueba12345!",
        )
        self.admin = self._crear_usuario(
            "admin",
            PerfilUsuario.Rol.ADMINISTRADOR_EMPRESA,
            self.analiza,
            puede_crear=True,
        )
        self.gerente = self._crear_usuario(
            "gerente",
            PerfilUsuario.Rol.GERENTE,
            self.analiza,
        )
        self.comprador = self._crear_usuario(
            "comprador",
            PerfilUsuario.Rol.COMPRADOR,
            self.analiza,
        )
        self.comprador_otra = self._crear_usuario(
            "comprador-otra",
            PerfilUsuario.Rol.COMPRADOR,
            self.otra,
        )

    def _crear_usuario(self, username, rol, empresa, puede_crear=False):
        usuario = User.objects.create_user(
            username=username,
            email=f"{username}@example.com",
            password="Prueba12345!",
        )
        perfil = usuario.perfil
        perfil.rol = rol
        perfil.empresa = empresa
        perfil.correo_verificado = True
        perfil.puede_crear_usuarios = puede_crear
        perfil.activo = True
        perfil.save()
        return usuario

    def test_superusuario_crea_administrador_sin_exponer_password(self):
        self.client.force_authenticate(self.superuser)
        respuesta = self.client.post(
            reverse("usuarios-administracion-list"),
            {
                "username": "nuevo-admin",
                "email": "nuevo-admin@example.com",
                "password": "ClaveNueva123!",
                "empresa": self.otra.pk,
                "rol": PerfilUsuario.Rol.ADMINISTRADOR_EMPRESA,
                "correo_verificado": True,
            },
            format="json",
        )

        self.assertEqual(respuesta.status_code, status.HTTP_201_CREATED)
        self.assertNotIn("password", respuesta.data)
        perfil = PerfilUsuario.objects.get(pk=respuesta.data["id"])
        self.assertEqual(perfil.empresa, self.otra)
        self.assertTrue(perfil.usuario.check_password("ClaveNueva123!"))

    def test_usuario_nuevo_sin_verificacion_queda_inactivo(self):
        self.client.force_authenticate(self.superuser)
        respuesta = self.client.post(
            reverse("usuarios-administracion-list"),
            {
                "username": "usuario-no-verificado",
                "email": "sin-verificar@example.com",
                "password": "ClaveNueva123!",
                "empresa": self.analiza.pk,
                "rol": PerfilUsuario.Rol.COMPRADOR,
            },
            format="json",
        )

        self.assertEqual(respuesta.status_code, status.HTTP_201_CREATED)
        perfil = PerfilUsuario.objects.get(pk=respuesta.data["id"])
        self.assertFalse(perfil.correo_verificado)
        self.assertFalse(perfil.usuario.is_active)

    def test_admin_fuerza_su_empresa_aunque_reciba_otra(self):
        self.client.force_authenticate(self.admin)
        respuesta = self.client.post(
            reverse("usuarios-administracion-list"),
            {
                "username": "nuevo-gerente",
                "email": "nuevo-gerente@example.com",
                "password": "ClaveNueva123!",
                "empresa": self.otra.pk,
                "rol": PerfilUsuario.Rol.GERENTE,
                "correo_verificado": True,
            },
            format="json",
        )

        self.assertEqual(respuesta.status_code, status.HTTP_201_CREATED)
        perfil = PerfilUsuario.objects.get(pk=respuesta.data["id"])
        self.assertEqual(perfil.empresa, self.analiza)

    def test_admin_no_puede_consultar_otra_empresa(self):
        self.client.force_authenticate(self.admin)
        respuesta = self.client.get(
            reverse("usuarios-administracion-list"),
            {"empresa_slug": self.otra.slug},
        )

        self.assertEqual(respuesta.status_code, status.HTTP_403_FORBIDDEN)

    def test_gerente_sin_permiso_no_puede_crear_usuario(self):
        self.client.force_authenticate(self.gerente)
        respuesta = self.client.post(
            reverse("usuarios-administracion-list"),
            {
                "username": "nuevo-comprador",
                "email": "nuevo-comprador@example.com",
                "password": "ClaveNueva123!",
                "rol": PerfilUsuario.Rol.COMPRADOR,
            },
            format="json",
        )

        self.assertEqual(respuesta.status_code, status.HTTP_403_FORBIDDEN)

    def test_comprador_no_accede_a_administracion(self):
        self.client.force_authenticate(self.comprador)
        respuesta = self.client.get(reverse("usuarios-administracion-list"))

        self.assertEqual(respuesta.status_code, status.HTTP_403_FORBIDDEN)

    def test_lista_es_paginada_y_no_mezcla_empresas(self):
        self.client.force_authenticate(self.admin)
        respuesta = self.client.get(reverse("usuarios-administracion-list"))

        self.assertEqual(respuesta.status_code, status.HTTP_200_OK)
        self.assertIn("results", respuesta.data)
        ids = {item["id"] for item in respuesta.data["results"]}
        self.assertIn(self.comprador.perfil.pk, ids)
        self.assertNotIn(self.comprador_otra.perfil.pk, ids)

    def test_bloquear_inactiva_usuario_y_revoca_refresh(self):
        refresh = RefreshToken.for_user(self.comprador)
        self.client.force_authenticate(self.admin)
        respuesta = self.client.post(
            reverse(
                "usuarios-administracion-bloquear",
                kwargs={"pk": self.comprador.perfil.pk},
            )
        )

        self.assertEqual(respuesta.status_code, status.HTTP_200_OK)
        self.comprador.refresh_from_db()
        self.comprador.perfil.refresh_from_db()
        self.assertFalse(self.comprador.is_active)
        self.assertFalse(self.comprador.perfil.activo)
        self.assertTrue(
            BlacklistedToken.objects.filter(
                token__jti=refresh["jti"],
            ).exists()
        )

        self.client.force_authenticate(user=None)
        login = self.client.post(
            reverse("usuarios-login"),
            {"email": self.comprador.email, "password": "Prueba12345!"},
            format="json",
        )
        self.assertIn(
            login.status_code,
            [status.HTTP_401_UNAUTHORIZED, status.HTTP_403_FORBIDDEN],
        )

    def test_desbloquear_reactiva_usuario_verificado(self):
        self.comprador.is_active = False
        self.comprador.save(update_fields=["is_active"])
        self.comprador.perfil.activo = False
        self.comprador.perfil.save(update_fields=["activo"])
        self.client.force_authenticate(self.admin)

        respuesta = self.client.post(
            reverse(
                "usuarios-administracion-desbloquear",
                kwargs={"pk": self.comprador.perfil.pk},
            )
        )

        self.assertEqual(respuesta.status_code, status.HTTP_200_OK)
        self.comprador.refresh_from_db()
        self.comprador.perfil.refresh_from_db()
        self.assertTrue(self.comprador.is_active)
        self.assertTrue(self.comprador.perfil.activo)

    def test_patch_inactivo_revoca_refresh_existente(self):
        refresh = RefreshToken.for_user(self.comprador)
        self.client.force_authenticate(self.admin)

        respuesta = self.client.patch(
            reverse(
                "usuarios-administracion-detail",
                kwargs={"pk": self.comprador.perfil.pk},
            ),
            {"activo": False},
            format="json",
        )

        self.assertEqual(respuesta.status_code, status.HTTP_200_OK)
        self.assertTrue(
            BlacklistedToken.objects.filter(token__jti=refresh["jti"]).exists()
        )
