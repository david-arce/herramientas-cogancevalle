"""
Pruebas del presupuesto por área (tabla vertical presupuesto_area).

    python manage.py test presupuestoApp
"""
import datetime
import io
import json

import pandas as pd
from django.contrib.auth.models import User
from django.db import connection
from django.db.migrations.executor import MigrationExecutor
from unittest import mock
from urllib.parse import unquote

from django.db.models import Sum
from django.test import TestCase, TransactionTestCase
from django.urls import reverse
from django.utils import timezone

from . import views, views_presupuesto_areas as vpa
from .models import Cuenta5Presupuestado, OrdenCuenta
from .models_presupuesto import (
    AsignacionPresupuesto, MESES, PlazoEdicionArea, PresupuestoArea, anio_elaboracion, anio_presupuesto, fecha_mes,
    filas_verticales,
)

AREA = "logistica"
# Nada de años fijos: todo se calcula a partir de la fecha de hoy.
ANIO = anio_presupuesto()


def fila(detalle, base=1000, **extra):
    """Fila horizontal como la envía la grilla."""
    return {
        "mcnzona": "001", "zonnombre": "ALMACEN TULUA", "mcnccosto": "020202",
        "responsable": "PILAR LOZANO", "mcncuenta": "513525", "ctanombre": "ACUEDUCTO",
        "mcndetalle": detalle, "sede_distribucion": 1.0, "proveedor": "EPM",
        **{m: base * i for i, m in enumerate(MESES, start=1)},
        "total": 0, "comentario": "ok", **extra,
    }


def asignar(usuario, presupuesto):
    """El área entra a su presupuesto porque lo tiene asignado (Ajustes → Asignación)."""
    return AsignacionPresupuesto.objects.create(usuario=usuario, presupuesto=presupuesto)


def total_de(f):
    return sum(f[m] for m in MESES)


class AnioAutomaticoTests(TestCase):
    def test_anio_es_el_siguiente_al_actual(self):
        hoy = timezone.localdate()
        self.assertEqual(anio_presupuesto(), hoy.year + 1)
        self.assertEqual(anio_elaboracion(), hoy.year)

    def test_cambia_solo_al_pasar_de_anio(self):
        with mock.patch("django.utils.timezone.localdate", return_value=datetime.date(2030, 12, 31)):
            self.assertEqual(anio_presupuesto(), 2031)
            self.assertEqual(vpa.fecha_limite_automatica(AREA), datetime.date(2030, 10, 15))
            self.assertEqual(vpa.fecha_limite_automatica("gerencia"), datetime.date(2030, 10, 8))
        with mock.patch("django.utils.timezone.localdate", return_value=datetime.date(2031, 1, 1)):
            self.assertEqual(anio_presupuesto(), 2032)
            self.assertEqual(vpa.fecha_limite_automatica(AREA), datetime.date(2031, 10, 15))

    def test_filas_nuevas_usan_el_anio_automatico(self):
        with mock.patch("django.utils.timezone.localdate", return_value=datetime.date(2030, 5, 1)):
            registros = filas_verticales([fila("A")], area=AREA, etapa="auxiliar")
        self.assertEqual({r.fecha.year for r in registros}, {2031})


def abrir_plazo(area=AREA, dias=365):
    """Deja el plazo del área abierto, para que las pruebas no dependan de la fecha de hoy."""
    PlazoEdicionArea.objects.update_or_create(
        area=area, defaults={"fecha_limite": timezone.localdate() + datetime.timedelta(days=dias)}
    )


class PlazoEdicionTests(TestCase):
    """Fecha límite configurable para el ÁREA; el aprobador no tiene fecha límite."""

    @classmethod
    def setUpTestData(cls):
        cls.usuario_area = User.objects.create_user("PLOZANO")
        cls.aprobador = User.objects.create_user("NICOLAS")
        asignar(cls.usuario_area, AREA)

    def post_json(self, nombre, datos, *args):
        return self.client.post(reverse(nombre, args=[AREA, *args]), json.dumps(datos),
                                content_type="application/json")

    def test_sin_configurar_usa_la_automatica(self):
        self.assertEqual(vpa.fecha_limite_edicion(AREA), (vpa.fecha_limite_automatica(AREA), False))
        abrir_plazo(dias=3)
        self.assertEqual(vpa.fecha_limite_edicion(AREA),
                         (timezone.localdate() + datetime.timedelta(days=3), True))

    def test_el_ultimo_dia_todavia_se_puede_editar(self):
        abrir_plazo(dias=0)
        self.client.force_login(self.usuario_area)
        r = self.client.get(reverse("tabla_auxiliar_sede", args=[AREA]))
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, "Puedes editar hasta el")

    def test_plazo_vencido_bloquea_al_area_en_todo(self):
        abrir_plazo(dias=-1)
        self.client.force_login(self.usuario_area)
        self.assertEqual(self.client.get(reverse("tabla_auxiliar_sede", args=[AREA])).status_code, 403)
        r = self.post_json("guardar_temp_sede", [fila("A")])
        self.assertEqual(r.status_code, 403)
        self.assertIn("cerró", r.json()["message"])
        self.assertEqual(self.client.post(reverse("cargar_base_sede", args=[AREA])).status_code, 403)
        PresupuestoArea.objects.bulk_create(filas_verticales([fila("A")], area=AREA, etapa="auxiliar"))
        r = self.client.post(reverse("subir_presupuesto_sede", args=[AREA]))
        self.assertEqual(r.status_code, 403)
        self.assertIn("cerró", r.json()["msg"])
        self.assertFalse(PresupuestoArea.objects.filter(etapa="proyectado").exists())

    def test_aprobador_no_tiene_fecha_limite(self):
        abrir_plazo(dias=-30)
        self.client.force_login(self.aprobador)
        r = self.client.get(reverse("tabla_auxiliar_sede", args=[AREA]))
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, "sin fecha límite")
        self.assertEqual(self.post_json("guardar_temp_sede", [fila("A")]).json()["status"], "ok")
        self.assertEqual(self.client.post(reverse("subir_presupuesto_sede", args=[AREA])).status_code, 200)
        r = self.client.post(reverse("aprobar_version_sede", args=[AREA, 1]))
        self.assertTrue(r.json()["success"], r.content)

    def test_aprobar_no_depende_de_ninguna_fecha(self):
        PresupuestoArea.objects.bulk_create(
            filas_verticales([fila("A")], area=AREA, etapa="proyectado", version=1))
        self.client.force_login(self.aprobador)
        with mock.patch("django.utils.timezone.localdate", return_value=datetime.date(2099, 12, 31)):
            r = self.client.post(reverse("aprobar_version_sede", args=[AREA, 1]))
        self.assertTrue(r.json()["success"], r.content)

    # ── Pantalla de ajustes ──
    def test_ajustes_solo_aprobador(self):
        self.client.force_login(self.usuario_area)
        self.assertEqual(self.client.get(reverse("ajustes_plazos_edicion")).status_code, 403)
        self.assertEqual(self.client.post(reverse("ajustes_plazos_edicion"), {}).status_code, 403)

    def test_ajustes_guardar_y_quitar(self):
        self.client.force_login(self.aprobador)
        r = self.client.get(reverse("ajustes_plazos_edicion"))
        self.assertEqual(r.status_code, 200)
        self.assertEqual(len(r.context["filas"]), 14)

        fecha = timezone.localdate() + datetime.timedelta(days=10)
        datos = {f"fecha_{a}": "" for a in vpa.SEDE_CONFIG}
        datos[f"fecha_{AREA}"] = fecha.isoformat()
        datos["fecha_gerencia"] = (timezone.localdate() - datetime.timedelta(days=1)).isoformat()
        r = self.client.post(reverse("ajustes_plazos_edicion"), datos)
        self.assertRedirects(r, reverse("ajustes_plazos_edicion") + "?guardado=1")
        self.assertEqual(PlazoEdicionArea.objects.get(area=AREA).fecha_limite, fecha)
        self.assertEqual(PlazoEdicionArea.objects.get(area=AREA).actualizado_por, "NICOLAS")

        r = self.client.get(reverse("ajustes_plazos_edicion") + "?guardado=1")
        self.assertContains(r, "Plazos guardados")
        filas = {f["area"]: f for f in r.context["filas"]}
        self.assertTrue(filas[AREA]["abierto"])
        self.assertEqual(filas[AREA]["dias"], 10)
        self.assertFalse(filas["gerencia"]["abierto"])
        self.assertIsNone(filas["tecnologia"]["configurada"])

        datos[f"fecha_{AREA}"] = ""                       # vacío -> vuelve a la automática
        self.client.post(reverse("ajustes_plazos_edicion"), datos)
        self.assertFalse(PlazoEdicionArea.objects.filter(area=AREA).exists())
        self.assertTrue(PlazoEdicionArea.objects.filter(area="gerencia").exists())

    def test_ajustes_fecha_invalida_no_guarda_nada(self):
        self.client.force_login(self.aprobador)
        datos = {f"fecha_{a}": "" for a in vpa.SEDE_CONFIG}
        datos[f"fecha_{AREA}"] = "2026-02-30"
        datos["fecha_gerencia"] = "2026-12-01"
        r = self.client.post(reverse("ajustes_plazos_edicion"), datos)
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, "fecha inválida")
        self.assertFalse(PlazoEdicionArea.objects.exists())


class ConversionTests(TestCase):
    def test_horizontal_a_vertical_y_de_vuelta(self):
        filas = [fila("A", 100), fila("B", 7)]
        PresupuestoArea.objects.bulk_create(filas_verticales(filas, area=AREA, etapa="auxiliar"))

        self.assertEqual(PresupuestoArea.objects.count(), 24)
        fechas = list(
            PresupuestoArea.objects.filter(linea=1).order_by("fecha").values_list("fecha", flat=True)
        )
        self.assertEqual(fechas, [datetime.date(ANIO, m, 1) for m in range(1, 13)])
        self.assertEqual(PresupuestoArea.objects.de(AREA, "auxiliar").cantidad_lineas(), 2)

        salida = PresupuestoArea.objects.de(AREA, "auxiliar").horizontal()
        self.assertEqual([f["mcndetalle"] for f in salida], ["A", "B"])
        for original, leida in zip(filas, salida):
            for m in MESES:
                self.assertEqual(leida[m], original[m])
            self.assertEqual(leida["total"], total_de(original))
            self.assertEqual(leida["anio"], ANIO)

    def test_anio_de_la_fila_se_respeta(self):
        PresupuestoArea.objects.bulk_create(
            filas_verticales([fila("A", anio=ANIO - 1)], area=AREA, etapa="auxiliar")
        )
        self.assertEqual(
            set(PresupuestoArea.objects.values_list("fecha__year", flat=True)), {ANIO - 1}
        )

    def test_fecha_mes(self):
        self.assertEqual(fecha_mes(ANIO, "marzo"), datetime.date(ANIO, 3, 1))
        self.assertEqual(fecha_mes(ANIO, 12), datetime.date(ANIO, 12, 1))


class FlujoAreaTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.usuario_area = User.objects.create_user("PLOZANO", password="x")
        cls.aprobador = User.objects.create_user("NICOLAS", password="x")
        cls.intruso = User.objects.create_user("OTRO", password="x")
        asignar(cls.usuario_area, AREA)
        abrir_plazo()

    def post_json(self, url, datos):
        return self.client.post(url, json.dumps(datos), content_type="application/json")

    def guardar_borrador(self, filas):
        self.client.force_login(self.usuario_area)
        r = self.post_json(reverse("guardar_temp_sede", args=[AREA]), filas)
        self.assertEqual(r.status_code, 200, r.content)
        return r.json()

    # ── Área ──
    def test_guardar_y_leer_borrador(self):
        filas = [fila("A", 10), fila("B", 3)]
        filas[1]["enero"] = ""         # vacío -> 0
        filas[1]["febrero"] = "1500"   # texto numérico
        filas[1]["sede_distribucion"] = ""  # vacío -> 0
        resp = self.guardar_borrador(filas)
        self.assertEqual(resp["msg"], "2 filas guardadas ✅")

        # En la BD: vertical, 12 registros por fila, uno por mes.
        qs = PresupuestoArea.objects.de(AREA, "auxiliar")
        self.assertEqual(qs.count(), 24)
        self.assertEqual(qs.filter(linea=2, fecha=datetime.date(ANIO, 1, 1)).get().valor, 0)
        self.assertEqual(qs.filter(linea=2, fecha=datetime.date(ANIO, 2, 1)).get().valor, 1500)
        self.assertEqual(qs.filter(linea=1).first().zonnombre, "ALMACEN TULUA")
        self.assertEqual(set(qs.filter(linea=2).values_list("sede_distribucion", flat=True)), {0})

        # La API devuelve horizontal, con los nombres nuevos y el total.
        datos = self.client.get(reverse("obtener_temp_sede", args=[AREA])).json()
        self.assertEqual(len(datos), 2)
        a, b = datos
        for campo in ("mcnzona", "zonnombre", "mcnccosto", "mcncuenta", "ctanombre", "mcndetalle"):
            self.assertIn(campo, a)
        for viejo in ("centro_tra", "nombre_cen", "codcosto", "cuenta", "cuenta_mayor", "detalle_cuenta"):
            self.assertNotIn(viejo, a)
        self.assertEqual(a["mcncuenta"], 513525)
        self.assertEqual(a["total"], total_de(filas[0]))
        self.assertEqual(b["enero"], 0)
        self.assertEqual(b["febrero"], 1500)
        self.assertEqual(b["total"], 1500 + sum(3 * i for i in range(3, 13)))

    def test_guardar_reemplaza_y_conserva_el_anio(self):
        self.guardar_borrador([fila("A")])
        leidas = self.client.get(reverse("obtener_temp_sede", args=[AREA])).json()
        leidas[0]["anio"] = ANIO - 1           # p. ej. una fila existente de otro año
        leidas[0]["marzo"] = 99
        self.guardar_borrador(leidas + [fila("nueva")])

        qs = PresupuestoArea.objects.de(AREA, "auxiliar")
        self.assertEqual(qs.count(), 24)
        self.assertEqual(qs.filter(linea=1).values_list("fecha__year", flat=True).distinct().get(), ANIO - 1)
        self.assertEqual(qs.filter(linea=2).values_list("fecha__year", flat=True).distinct().get(), ANIO)
        self.assertEqual(qs.get(linea=1, fecha=datetime.date(ANIO - 1, 3, 1)).valor, 99)

    def test_guardar_no_toca_otras_areas(self):
        PresupuestoArea.objects.bulk_create(filas_verticales([fila("X")], area="tecnologia", etapa="auxiliar"))
        self.guardar_borrador([])
        self.assertEqual(PresupuestoArea.objects.filter(area="tecnologia").count(), 12)

    def test_permisos(self):
        self.client.force_login(self.intruso)
        r = self.post_json(reverse("guardar_temp_sede", args=[AREA]), [fila("A")])
        self.assertEqual(r.status_code, 403)
        self.assertEqual(self.client.get(reverse("tabla_auxiliar_sede", args=[AREA])).status_code, 403)
        self.assertFalse(PresupuestoArea.objects.exists())

    def test_pantallas_renderizan(self):
        self.guardar_borrador([fila("A")])
        self.assertEqual(self.client.get(reverse("tabla_auxiliar_sede", args=[AREA])).status_code, 200)
        self.assertEqual(self.client.get(reverse("presupuesto_aprobado_sede", args=[AREA])).status_code, 200)

    # ── Versiones ──
    def subir(self):
        self.client.force_login(self.usuario_area)
        r = self.client.post(reverse("subir_presupuesto_sede", args=[AREA]))
        self.assertEqual(r.status_code, 200, r.content)
        return r.json()["version"]

    def test_subir_crea_version_con_mismas_fechas(self):
        self.guardar_borrador([fila("A"), fila("B"), fila("C")])
        self.assertEqual(self.subir(), 1)
        self.assertEqual(self.subir(), 2)

        v1 = PresupuestoArea.objects.de(AREA, "proyectado").filter(version=1)
        self.assertEqual(v1.count(), 36)
        self.assertEqual(set(v1.values_list("fecha_version", flat=True)), {timezone.now().date()})
        self.assertEqual(
            sorted(set(v1.values_list("fecha", flat=True))),
            [datetime.date(ANIO, m, 1) for m in range(1, 13)],
        )

        # El resumen de versiones cuenta filas de la grilla, no registros mensuales.
        self.client.force_login(self.aprobador)
        r = self.client.get(reverse("presupuesto_sede", args=[AREA]))
        self.assertEqual(r.status_code, 200)
        self.assertEqual([v["filas"] for v in r.context["versiones"]], [3, 3])
        self.assertEqual(r.context["versiones"][0]["fecha"], timezone.now().date())
        self.assertContains(r, "3 filas")

    def test_subir_sin_datos(self):
        self.client.force_login(self.usuario_area)
        r = self.client.post(reverse("subir_presupuesto_sede", args=[AREA]))
        self.assertEqual(r.status_code, 400)

    def test_aprobador_edita_aprueba_y_borra(self):
        self.guardar_borrador([fila("A", 5), fila("B", 6)])
        self.subir()
        PresupuestoArea.objects.filter(version=1).update(fecha_version=datetime.date(2026, 9, 1))

        self.client.force_login(self.aprobador)
        datos = self.client.get(reverse("obtener_presupuesto_sede", args=[AREA]) + "?version=1").json()["data"]
        self.assertEqual(len(datos), 2)
        self.assertEqual(datos[0]["version"], 1)

        datos[1]["diciembre"] = 1
        r = self.post_json(reverse("guardar_version_sede", args=[AREA, 1]), datos)
        self.assertEqual(r.json()["status"], "ok")
        v1 = PresupuestoArea.objects.de(AREA, "proyectado").filter(version=1)
        self.assertEqual(set(v1.values_list("fecha_version", flat=True)), {datetime.date(2026, 9, 1)})
        self.assertEqual(v1.get(linea=2, fecha=datetime.date(ANIO, 12, 1)).valor, 1)

        r = self.client.post(reverse("aprobar_version_sede", args=[AREA, 1]))
        self.assertTrue(r.json()["success"], r.content)
        aprobadas = self.client.get(reverse("obtener_presupuesto_aprobado_sede", args=[AREA])).json()["data"]
        self.assertEqual([f["mcndetalle"] for f in aprobadas], ["A", "B"])
        self.assertEqual(aprobadas[1]["diciembre"], 1)
        self.assertEqual(aprobadas[0]["total"], total_de(fila("A", 5)))

        # Aprobar de nuevo reemplaza, no duplica.
        self.client.post(reverse("aprobar_version_sede", args=[AREA, 1]))
        self.assertEqual(PresupuestoArea.objects.de(AREA, "aprobado").count(), 24)

        r = self.post_json(reverse("borrar_presupuesto_sede", args=[AREA]), {"version": 1})
        self.assertEqual(r.json()["status"], "ok")
        self.assertFalse(PresupuestoArea.objects.filter(version=1).exists())
        self.assertEqual(PresupuestoArea.objects.de(AREA, "auxiliar").count(), 24)

    def test_area_no_puede_aprobar(self):
        self.guardar_borrador([fila("A")])
        self.subir()
        r = self.client.post(reverse("aprobar_version_sede", args=[AREA, 1]))
        self.assertEqual(r.status_code, 403)

    # ── Consolidado y export ──
    def test_consolidado_con_alias(self):
        self.client.force_login(self.aprobador)
        r = self.post_json(reverse("guardar_presupuesto_consolidado", args=["gh"]), [fila("GH", 2)])
        self.assertEqual(r.json()["status"], "ok")
        qs = PresupuestoArea.objects.de("gestion-humana", "aprobado")
        self.assertEqual(qs.count(), 12)
        self.assertEqual(set(qs.values_list("version", flat=True)), {1})
        datos = self.client.get(reverse("obtener_presupuesto_consolidado", args=["gh"])).json()["data"]
        self.assertEqual(datos[0]["total"], total_de(fila("GH", 2)))

    def test_exportar_excel(self):
        PresupuestoArea.objects.bulk_create(
            filas_verticales([fila("A", 1), fila("B", 2)], area=AREA, etapa="aprobado", version=1)
            + filas_verticales([fila("T", 3)], area="tecnologia", etapa="aprobado", version=2)
        )
        r = self.client.get(reverse("exportar_excel_presupuestos"))
        self.assertEqual(r.status_code, 200)
        df = pd.read_excel(io.BytesIO(r.content))
        self.assertEqual(len(df), 36)
        for col in ("origen", "linea", "zonnombre", "mcncuenta", "ctanombre", "mes", "fecha", "valor"):
            self.assertIn(col, df.columns)
        self.assertEqual(df["valor"].sum(), total_de(fila("A", 1)) + total_de(fila("B", 2)) + total_de(fila("T", 3)))
        self.assertEqual(list(df["origen"].unique()), ["Logística", "Tecnología"])  # orden de SEDE_CONFIG
        primera = df.iloc[0]
        self.assertEqual((primera["mes"], pd.Timestamp(primera["fecha"]).date()), ("enero", datetime.date(ANIO, 1, 1)))

    def test_exportar_excel_vacio(self):
        self.assertEqual(self.client.get(reverse("exportar_excel_presupuestos")).status_code, 200)


class CargarPlantillaTests(TestCase):
    """cargar_base_sede lee la tabla externa plantillagastosAAAA del año que corresponda."""

    def crear_plantilla(self, anio, filas):
        tabla = f"plantillagastos{anio}"
        meses = ", ".join(f"{m} double precision" for m in MESES)
        with connection.cursor() as cur:
            cur.execute(
                f'CREATE TABLE {tabla} ("CENTRO_TRA" varchar, "NOMBRE_CEN" varchar, "CODCOSTO" varchar, '
                f'"RESPONSABLE" varchar, "CUENTA" bigint, "CUENTA MAYOR" varchar, "DETALLE CUENTA" varchar, '
                f'"SEDE  DISTRIBUCION" double precision, proveedor varchar, {meses})'
            )
            for f in filas:
                cur.execute(
                    f'INSERT INTO {tabla} VALUES ({", ".join(["%s"] * (9 + 12))})',
                    [f.get(c) for c in ("centro", "nombre", "costo", "resp", "cuenta", "cmayor", "det", "sede", "prov")]
                    + [f.get(m) for m in MESES],
                )

    def setUp(self):
        abrir_plazo()
        usuario = User.objects.create_user("PLOZANO")
        asignar(usuario, AREA)
        self.client.force_login(usuario)

    def cargar(self):
        return self.client.post(reverse("cargar_base_sede", args=[AREA]))

    def test_sin_plantillas(self):
        self.assertEqual(self.cargar().status_code, 404)

    def test_elige_la_del_anio_de_elaboracion(self):
        actual = anio_elaboracion()
        self.crear_plantilla(actual - 1, [{"resp": "PILAR LOZANO", "det": "vieja", "enero": 1}])
        self.crear_plantilla(actual, [{"resp": "PILAR LOZANO", "det": "actual", "enero": 2}])
        r = self.cargar().json()
        self.assertEqual(r["anio_plantilla"], actual)
        self.assertEqual(PresupuestoArea.objects.get(fecha__month=1).mcndetalle, "actual")

    def test_usa_la_mas_reciente_si_aun_no_existe_la_del_anio(self):
        actual = anio_elaboracion()
        self.crear_plantilla(actual - 3, [{"resp": "PILAR LOZANO", "det": "muy vieja"}])
        self.crear_plantilla(actual - 1, [{"resp": "PILAR LOZANO", "det": "reciente"}])
        self.assertEqual(self.cargar().json()["anio_plantilla"], actual - 1)
        self.assertEqual(set(PresupuestoArea.objects.values_list("mcndetalle", flat=True)), {"reciente"})

    def test_cargar_base(self):
        self.crear_plantilla(anio_elaboracion(), [
            {"centro": "001", "nombre": "ADMINISTRACIÓN", "costo": "0102", "resp": "pilar lozano",
             "cuenta": 513525, "cmayor": "ACUEDUCTO", "det": "agua", "prov": "EPM",
             **{m: i * 10 for i, m in enumerate(MESES, 1)}, "abril": 40.0},
            {"resp": "OTRO", "enero": 1},
        ])
        r = self.cargar()
        self.assertEqual(r.json()["msg"], f"1 filas cargadas desde plantilla {anio_elaboracion()} 📂")

        datos = self.client.get(reverse("obtener_temp_sede", args=[AREA])).json()
        self.assertEqual(len(datos), 1)
        f = datos[0]
        self.assertEqual(
            (f["mcnzona"], f["zonnombre"], f["mcnccosto"], f["mcncuenta"], f["ctanombre"], f["mcndetalle"]),
            ("001", "ADMINISTRACIÓN", "0102", 513525, "ACUEDUCTO", "agua"),
        )
        self.assertEqual(f["sede_distribucion"], 0)
        self.assertEqual(f["total"], sum(i * 10 for i in range(1, 13)))
        self.assertEqual(PresupuestoArea.objects.count(), 12)


class MigracionVerticalTests(TransactionTestCase):
    """0030 convierte las filas horizontales en verticales sin perder datos, y se revierte."""

    antes = [("presupuestoApp", "0029_drop_tablas_legacy")]
    despues = [("presupuestoApp", "0030_presupuestoarea_vertical")]

    def migrar(self, destino):
        executor = MigrationExecutor(connection)
        executor.loader.build_graph()
        executor.migrate(destino)
        return executor.loader.project_state(destino).apps

    def tearDown(self):
        self.migrar(MigrationExecutor(connection).loader.graph.leaf_nodes())

    def test_ida_y_vuelta(self):
        SUBIDA = datetime.date(ANIO - 2, 10, 20)   # versión subida hace dos ciclos
        apps = self.migrar(self.antes)
        Viejo = apps.get_model("presupuestoApp", "PresupuestoArea")
        meses_a = {m: i * 100 for i, m in enumerate(MESES, 1)}
        meses_b = {**{m: 5 for m in MESES}, "marzo": None}
        comunes = dict(centro_tra="001", nombre_cen="ALMACEN BUGA", codcosto="020200", responsable="R",
                       cuenta=513525, cuenta_mayor="ACUEDUCTO", detalle_cuenta="d", comentario="c")
        Viejo.objects.create(area="logistica", etapa="auxiliar", **comunes, **meses_a, total=7800)
        Viejo.objects.create(area="logistica", etapa="auxiliar", **comunes, **meses_b, total=55)
        Viejo.objects.create(area="logistica", etapa="aprobado", version=3,
                             fecha=SUBIDA, **comunes, **meses_a, total=7800)

        apps = self.migrar(self.despues)
        Nuevo = apps.get_model("presupuestoApp", "PresupuestoArea")
        self.assertEqual(Nuevo.objects.count(), 36)
        aux = Nuevo.objects.filter(etapa="auxiliar")
        self.assertEqual(sorted(set(aux.values_list("linea", flat=True))), [1, 2])
        self.assertEqual(aux.get(linea=1, fecha__month=4).valor, 400)
        self.assertEqual(aux.get(linea=2, fecha__month=3).valor, 0)   # NULL -> 0
        r = aux.first()
        self.assertEqual((r.mcnzona, r.zonnombre, r.mcnccosto, r.mcncuenta, r.ctanombre, r.mcndetalle),
                         ("001", "ALMACEN BUGA", "020200", 513525, "ACUEDUCTO", "d"))
        # Versión subida en el año N -> presupuesto N+1; borrador -> año siguiente al actual.
        apr = Nuevo.objects.filter(etapa="aprobado")
        self.assertEqual(set(apr.values_list("fecha__year", flat=True)), {SUBIDA.year + 1})
        self.assertEqual(set(apr.values_list("fecha_version", flat=True)), {SUBIDA})
        self.assertEqual(set(aux.values_list("fecha__year", flat=True)), {datetime.date.today().year + 1})

        apps = self.migrar(self.antes)
        Viejo = apps.get_model("presupuestoApp", "PresupuestoArea")
        self.assertEqual(Viejo.objects.count(), 3)
        a = Viejo.objects.get(etapa="aprobado")
        self.assertEqual((a.version, a.fecha, a.total, a.abril, a.cuenta_mayor),
                         (3, SUBIDA, 7800, 400, "ACUEDUCTO"))
        self.assertEqual(sorted(Viejo.objects.filter(etapa="auxiliar").values_list("total", flat=True)), [55, 7800])


class Cuenta5EnvioTests(TestCase):
    """Subir la última versión aprobada de un área a Cuenta 5 presupuestado."""

    @classmethod
    def setUpTestData(cls):
        cls.aprobador = User.objects.create_user("NICOLAS")
        cls.usuario_area = User.objects.create_user("PLOZANO")

    def setUp(self):
        self.client.force_login(self.aprobador)

    def aprobar(self, filas, version):
        PresupuestoArea.objects.filter(area=AREA, etapa="aprobado", version=version).delete()
        PresupuestoArea.objects.bulk_create(filas_verticales(
            filas, area=AREA, etapa="aprobado", version=version, fecha_version=timezone.localdate(),
        ))

    def subir(self, area=AREA):
        return self.client.post(reverse("subir_cuenta5_sede", args=[area]))

    def filas_base(self):
        a = fila("A", 100, comentario="revisar enero", responsable="")   # responsable vacío -> el del área
        a["febrero"] = 0                                                  # los meses en 0 no se suben
        b = fila("B", 10, responsable="OTRA PERSONA", comentario="")
        b["marzo"] = -500                                                 # negativo -> crédito
        sin_cuenta = fila("sin cuenta", 1, mcncuenta=0)
        return [a, b, sin_cuenta]

    def test_estado_sin_aprobar_y_no_permite_subir(self):
        self.assertEqual(vpa.estado_cuenta5(AREA)["estado"], "sin_aprobar")
        r = self.subir()
        self.assertEqual(r.status_code, 400)
        self.assertEqual(r.json()["estado"]["estado"], "sin_aprobar")
        self.assertFalse(Cuenta5Presupuestado.objects.exists())

    def test_permisos_y_metodo(self):
        self.aprobar([fila("A")], 1)
        self.client.force_login(self.usuario_area)
        self.assertEqual(self.subir().status_code, 403)
        self.client.force_login(self.aprobador)
        self.assertEqual(self.client.get(reverse("subir_cuenta5_sede", args=[AREA])).status_code, 405)
        self.assertEqual(self.subir("no-existe").status_code, 404)

    def test_sube_la_ultima_version_aprobada(self):
        self.aprobar([fila("vieja", 999)], 1)
        self.aprobar(self.filas_base(), 2)
        self.assertEqual(vpa.estado_cuenta5(AREA)["estado"], "pendiente")

        r = self.subir()
        self.assertEqual(r.status_code, 200, r.content)
        datos = r.json()
        self.assertTrue(datos["success"])
        self.assertEqual(datos["registros"], 11 + 12)     # A sin febrero + B completo
        self.assertEqual(datos["sin_cuenta"], 1)
        self.assertEqual(datos["estado"]["estado"], "subido")
        self.assertEqual(datos["estado"]["version_subida"], 2)

        qs = Cuenta5Presupuestado.objects.filter(origen_area=AREA)
        self.assertFalse(qs.filter(mcndetalle="vieja").exists())
        self.assertEqual(set(qs.values_list("origen_version", flat=True)), {2})

        enero_a = qs.get(mcndetalle="A", mcnfecha=vpa._serial_excel(datetime.date(ANIO, 1, 1)))
        self.assertEqual(views.excel_serial_to_date(enero_a.mcnfecha), f"{ANIO}-01-01")
        self.assertEqual((enero_a.mcnvaldebi, enero_a.mcnvalcred), (100.0, 0.0))
        self.assertEqual(enero_a.mcncuenta, "513525")
        self.assertEqual((enero_a.mcnccosto, enero_a.mcnzona, enero_a.zonnombre, enero_a.ctanombre),
                         ("020202", "001", "ALMACEN TULUA", "ACUEDUCTO"))
        self.assertIsNone(enero_a.vinnombre)          # no se llena desde presupuesto_area
        self.assertEqual(enero_a.comentario, "revisar enero")
        self.assertEqual(enero_a.responsable, "PILAR LOZANO")          # el del área
        self.assertEqual(qs.filter(mcndetalle="B").first().responsable, "OTRA PERSONA")
        self.assertIsNone(qs.filter(mcndetalle="B").first().comentario)

        marzo_b = qs.get(mcndetalle="B", mcnfecha=vpa._serial_excel(datetime.date(ANIO, 3, 1)))
        self.assertEqual((marzo_b.mcnvaldebi, marzo_b.mcnvalcred), (0.0, 500.0))

        aprobado = PresupuestoArea.objects.de(AREA, "aprobado").filter(version=2).exclude(mcncuenta=0)
        total_aprobado = sum(aprobado.values_list("valor", flat=True))
        total_c5 = sum(d - c for d, c in qs.values_list("mcnvaldebi", "mcnvalcred"))
        self.assertEqual(total_c5, total_aprobado)

    def test_volver_a_subir_reemplaza_y_no_toca_lo_cargado_por_excel(self):
        Cuenta5Presupuestado.objects.create(mcncuenta="510506", mcnvaldebi=7, mcnfecha=46023)
        self.aprobar(self.filas_base(), 1)
        self.subir()
        r = self.subir().json()
        self.assertEqual(r["reemplazados"], 23)
        self.assertEqual(Cuenta5Presupuestado.objects.filter(origen_area=AREA).count(), 23)
        self.assertEqual(Cuenta5Presupuestado.objects.filter(origen_area__isnull=True).count(), 1)

    def test_detecta_desactualizado(self):
        self.aprobar(self.filas_base(), 1)
        self.subir()
        self.assertEqual(vpa.estado_cuenta5(AREA)["estado"], "subido")

        # Re-aprobada la MISMA versión con un cambio -> desactualizado.
        cambiadas = self.filas_base()
        cambiadas[0]["enero"] = 1
        self.aprobar(cambiadas, 1)
        e = vpa.estado_cuenta5(AREA)
        self.assertEqual(e["estado"], "desactualizado")
        self.assertIn("cambió", e["detalle"])

        # Nueva versión aprobada -> desactualizado y lo dice.
        self.aprobar(self.filas_base(), 2)
        e = vpa.estado_cuenta5(AREA)
        self.assertEqual(e["estado"], "desactualizado")
        self.assertIn("v1", e["detalle"])
        self.assertIn("v2", e["detalle"])
        self.subir()
        self.assertEqual(vpa.estado_cuenta5(AREA)["estado"], "subido")

        # Si se borra lo subido (p. ej. "borrar cuenta 5"), vuelve a pendiente.
        Cuenta5Presupuestado.objects.all().delete()
        self.assertEqual(vpa.estado_cuenta5(AREA)["estado"], "pendiente")

    def test_entra_al_consolidado_presupuestado(self):
        self.aprobar([fila("A", 100)], 1)
        self.subir()
        resultado = views.calcular_movimientos("presupuestado", "total")
        self.assertTrue(resultado["success"], resultado)
        enero = sum(reg["meses"].get("Enero", 0) for reg in resultado["data"].values())
        self.assertEqual(enero, 100)
        diciembre = sum(reg["meses"].get("Diciembre", 0) for reg in resultado["data"].values())
        self.assertEqual(diciembre, 1200)

    def test_dashboard_muestra_estado_y_boton(self):
        self.aprobar([fila("A")], 1)
        r = self.client.get(reverse("dashboardPresupuesto"))
        self.assertEqual(r.status_code, 200)
        tarjetas = {t["clave"]: t for t in r.context["tarjetas"]}
        self.assertEqual(len(tarjetas), 15)                     # 14 áreas + nómina
        self.assertEqual(tarjetas["nomina"]["cuenta5"]["estado"], "sin_datos")
        self.assertEqual(tarjetas[AREA]["cuenta5"]["estado"], "pendiente")
        self.assertEqual(tarjetas["tecnologia"]["cuenta5"]["estado"], "sin_aprobar")
        self.assertContains(r, reverse("subir_cuenta5_sede", args=[AREA]))
        self.assertContains(r, "Pendiente de subir")
        self.assertContains(r, '<span class="c5-texto">Sin versión aprobada</span>', count=13)
        self.assertContains(r, reverse("subir_cuenta5_nomina"))

    def test_pantalla_cuenta5_devuelve_comentario_y_responsable(self):
        self.aprobar([fila("A", comentario="nota")], 1)
        self.subir()
        datos = self.client.get(reverse("obtener_cuenta5_presupuestado") + "?length=100").json()["data"]
        self.assertEqual(datos[0]["comentario"], "nota")
        self.assertEqual(datos[0]["responsable"], "PILAR LOZANO")


class EstaticosVersionadosTests(TestCase):
    """{% static_v %} cambia la URL cuando cambia el archivo (evita JS viejo en caché)."""

    def test_url_lleva_version_y_no_falla_si_no_existe(self):
        from django.template import Context, Template
        html = Template("{% load estaticos %}{% static_v 'js/cuenta5_presupuestado.js' %}").render(Context())
        self.assertRegex(html, r"^/static/js/cuenta5_presupuestado\.js\?v=\d+$")
        html = Template("{% load estaticos %}{% static_v 'js/no_existe.js' %}").render(Context())
        self.assertEqual(html, "/static/js/no_existe.js")

    def test_pantalla_cuenta5_carga_js_versionado(self):
        self.client.force_login(User.objects.create_user("NICOLAS"))
        r = self.client.get(reverse("cuenta5_presupuestado"))
        self.assertEqual(r.status_code, 200)
        self.assertRegex(r.content.decode(), r"js/cuenta5_presupuestado\.js\?v=\d+")
        self.assertContains(r, "COMENTARIO")
        self.assertContains(r, "RESPONSABLE")


# ═══════════════════════════════════════════════════════════════════════
#  Nómina en vertical
# ═══════════════════════════════════════════════════════════════════════
from .models_nomina import (  # noqa: E402
    ConceptosNomina, ConfiguracionNomina, PresupuestoNomina, PresupuestoNominaMes,
)
from . import nomina_motor  # noqa: E402


def confirmar_nomina(listo):
    ConfiguracionNomina.objects.update_or_create(pk=1, defaults={"listo": listo})

MESES_N = list(MESES)


def linea_nomina(**kw):
    datos = dict(tipo="sueldos", cedula="1001", nombre="ANA PEREZ", centro="ALMACEN TULUA",
                 area="VENTAS", cargo="ASESOR", concepto="SUELDO", cuenta="510506")
    datos.update({m: 1000 * i for i, m in enumerate(MESES_N, 1)})
    datos.update(kw)
    return PresupuestoNomina(**datos)


class NominaVerticalTests(TestCase):
    """La tabla presupuesto_nomina es vertical; PresupuestoNomina (vista) la muestra horizontal."""

    def test_guardar_crea_12_registros_con_fecha(self):
        f = linea_nomina(); f.save()
        regs = PresupuestoNominaMes.objects.filter(linea=f.pk).order_by("fecha")
        self.assertEqual(regs.count(), 12)
        self.assertEqual([r.fecha for r in regs], [datetime.date(ANIO, m, 1) for m in range(1, 13)])
        self.assertEqual([r.valor for r in regs], [1000 * i for i in range(1, 13)])
        self.assertEqual({r.cedula for r in regs}, {"1001"})
        leida = PresupuestoNomina.objects.get(pk=f.pk)
        self.assertEqual((leida.total, leida.anio), (78000, ANIO))

    def test_editar_borrar_y_operaciones_en_lote(self):
        a = linea_nomina(); a.save()
        a.marzo = -5; a.nombre = "ANA P."; a.save()
        self.assertEqual(PresupuestoNominaMes.objects.get(linea=a.pk, fecha__month=3).valor, -5)
        self.assertEqual(set(PresupuestoNominaMes.objects.filter(linea=a.pk).values_list("nombre", flat=True)),
                         {"ANA P."})

        nuevas = PresupuestoNomina.objects.bulk_create([linea_nomina(cedula=str(i)) for i in range(3)])
        self.assertEqual(len({n.pk for n in nuevas}), 3)
        for n in nuevas:
            n.enero = 1
            n.cuenta = "520506"
        PresupuestoNomina.objects.bulk_update(nuevas, MESES_N + ["total", "cuenta"])
        self.assertEqual(PresupuestoNominaMes.objects.filter(cuenta="520506").count(), 36)
        self.assertEqual(PresupuestoNominaMes.objects.filter(cuenta="520506", fecha__month=1, valor=1).count(), 3)

        suma = PresupuestoNomina.objects.aggregate(e=Sum("enero"), t=Sum("total"))
        self.assertEqual(suma["e"], 1000 + 3)

        PresupuestoNomina.objects.filter(pk__in=[n.pk for n in nuevas]).delete()
        a.delete()
        self.assertFalse(PresupuestoNominaMes.objects.exists())

    def test_json_se_conservan(self):
        f = linea_nomina(historico={"enero": 5}, excluir_de=["prima"]); f.save()
        leida = PresupuestoNomina.objects.get(pk=f.pk)
        self.assertEqual((leida.historico, leida.excluir_de), ({"enero": 5}, ["prima"]))

    def test_pantalla_guardar_edicion(self):
        linea_nomina().save()
        admin = User.objects.create_user("admin")
        self.client.force_login(admin)
        filas = self.client.get(reverse("nomina_datos", args=["sueldos"])).json()["data"]
        self.assertEqual(len(filas), 1)
        filas[0]["abril"] = 999
        r = self.client.post(reverse("nomina_guardar", args=["sueldos"]), json.dumps(filas),
                             content_type="application/json")
        self.assertEqual(r.json()["status"], "ok", r.content)
        self.assertEqual(PresupuestoNominaMes.objects.get(linea=filas[0]["id"], fecha__month=4).valor, 999)
        self.assertEqual(self.client.get(reverse("nomina_resumen")).status_code, 200)


class Cuenta5NominaTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.aprobador = User.objects.create_user("NICOLAS")

    def setUp(self):
        self.client.force_login(self.aprobador)
        confirmar_nomina(True)

    def subir(self):
        return self.client.post(reverse("subir_cuenta5_nomina"))

    def test_sin_datos(self):
        self.assertEqual(vpa.estado_cuenta5_nomina()["estado"], "sin_datos")
        self.assertEqual(self.subir().status_code, 400)

    def test_permisos(self):
        self.client.force_login(User.objects.create_user("OTRO"))
        self.assertEqual(self.subir().status_code, 403)
        self.client.force_login(self.aprobador)
        self.assertEqual(self.client.get(reverse("subir_cuenta5_nomina")).status_code, 405)

    def test_sube_con_el_mapeo_pedido(self):
        a = linea_nomina(codcosto="020202"); a.febrero = 0; a.marzo = -300; a.save()   # 0 no se sube; negativo -> crédito
        linea_nomina(cedula="2002", nombre="LUIS", cuenta="").save()      # sin cuenta: no se sube
        self.assertEqual(vpa.estado_cuenta5_nomina()["estado"], "pendiente")

        r = self.subir().json()
        self.assertTrue(r["success"], r)
        self.assertEqual((r["registros"], r["sin_cuenta"]), (11, 1))
        self.assertEqual(r["estado"]["estado"], "subido")

        qs = Cuenta5Presupuestado.objects.filter(origen_area="nomina")
        enero = qs.get(mcnfecha=vpa._serial_excel(datetime.date(ANIO, 1, 1)))
        self.assertEqual((enero.mcncuenta, enero.mcnccosto, enero.zonnombre, enero.mcnvincula, enero.vinnombre),
                         ("510506", "020202", "ALMACEN TULUA", "1001", "ANA PEREZ"))
        self.assertEqual((enero.mcnvaldebi, enero.mcnvalcred), (1000.0, 0.0))
        # Solo esos campos: lo demás queda vacío.
        self.assertEqual(set(qs.values_list("responsable", flat=True)), {"nomina"})
        for campo in ("mcnzona", "ctanombre", "mcndetalle", "comentario"):
            self.assertIsNone(getattr(enero, campo), campo)
        marzo = qs.get(mcnfecha=vpa._serial_excel(datetime.date(ANIO, 3, 1)))
        self.assertEqual((marzo.mcnvaldebi, marzo.mcnvalcred), (0.0, 300.0))
        self.assertEqual(views.excel_serial_to_date(enero.mcnfecha), f"{ANIO}-01-01")

    def test_sin_codcosto_queda_vacio(self):
        linea_nomina(codcosto="").save()
        self.subir()
        self.assertEqual(set(Cuenta5Presupuestado.objects.values_list("mcnccosto", flat=True)), {None})

    def test_reemplaza_y_detecta_cambios(self):
        Cuenta5Presupuestado.objects.create(mcncuenta="510506", mcnvaldebi=1, mcnfecha=1)   # cargado por Excel
        a = linea_nomina(); a.save()
        self.subir()
        self.assertEqual(self.subir().json()["reemplazados"], 12)
        self.assertEqual(Cuenta5Presupuestado.objects.filter(origen_area="nomina").count(), 12)
        self.assertEqual(Cuenta5Presupuestado.objects.filter(origen_area__isnull=True).count(), 1)

        a.enero = 1; a.save()
        self.assertEqual(vpa.estado_cuenta5_nomina()["estado"], "desactualizado")
        self.subir()
        self.assertEqual(vpa.estado_cuenta5_nomina()["estado"], "subido")

    def test_no_se_mezcla_con_las_areas(self):
        linea_nomina().save()
        PresupuestoArea.objects.bulk_create(filas_verticales(
            [fila("A")], area=AREA, etapa="aprobado", version=1, fecha_version=timezone.localdate()))
        self.client.post(reverse("subir_cuenta5_sede", args=[AREA]))
        self.subir()
        self.assertEqual(Cuenta5Presupuestado.objects.filter(origen_area="nomina").count(), 12)
        self.assertEqual(Cuenta5Presupuestado.objects.filter(origen_area=AREA).count(), 12)
        self.assertEqual(vpa.estado_cuenta5(AREA)["estado"], "subido")


class MigracionNominaVerticalTests(TransactionTestCase):
    antes = [("presupuestoApp", "0033_plazo_edicion_area")]
    despues = [("presupuestoApp", "0034_presupuesto_nomina_vertical")]

    def migrar(self, destino):
        executor = MigrationExecutor(connection)
        executor.loader.build_graph()
        executor.migrate(destino)

    def tearDown(self):
        self.migrar(MigrationExecutor(connection).loader.graph.leaf_nodes())

    def test_ida_y_vuelta(self):
        self.migrar(self.antes)
        meses = ", ".join(MESES_N)
        with connection.cursor() as cur:
            for i, (tipo, marzo) in enumerate([("sueldos", 300), ("cesantias", -7)], start=1):
                valores = [i * 10 + m for m in range(1, 13)]
                valores[2] = marzo
                cur.execute(
                    f"INSERT INTO presupuesto_nomina (id, tipo, cedula, nombre, centro, area, cargo, concepto, "
                    f"cuenta, base, factor, historico, {meses}, total, origen, clave, centro_origen, "
                    f"area_origen, excluir_de, creado, actualizado, actualizado_por) VALUES "
                    f"(%s, %s, '1', 'N', 'C', 'A', 'G', 'X', '510506', 0, 1, '{{\"enero\": 1}}', "
                    f"{', '.join(['%s'] * 12)}, %s, 'sistema', 'k', '', '', '[]', now(), now(), '')",
                    [40 + i, tipo, *valores, sum(valores)],
                )
        # (SQL directo: los modelos actuales tienen columnas de migraciones posteriores)
        def uno(sql, params=()):
            with connection.cursor() as cur:
                cur.execute(sql, params)
                return cur.fetchone()

        self.migrar(self.despues)
        self.assertEqual(uno("SELECT COUNT(*) FROM presupuesto_nomina")[0], 24)
        self.assertEqual(uno("SELECT valor FROM presupuesto_nomina WHERE linea = 42 "
                             "AND EXTRACT(MONTH FROM fecha) = 3")[0], -7)
        tipo, marzo, historico = uno("SELECT tipo, marzo, historico FROM presupuesto_nomina_lineas WHERE id = 41")
        self.assertEqual((tipo, marzo, json.loads(historico) if isinstance(historico, str) else historico),
                         ("sueldos", 300, {"enero": 1}))
        # Las filas nuevas continúan después de los ids que ya existían.
        nueva = uno("INSERT INTO presupuesto_nomina_lineas (tipo, cedula, nombre, centro, area, cargo, "
                    "concepto, cuenta, base, factor, historico, origen, clave, centro_origen, area_origen, "
                    "excluir_de, creado, actualizado, actualizado_por, enero) VALUES ('t', '', '', '', '', '', "
                    "'', '', 0, 1, '{}', 'manual', '', '', '', '[]', now(), now(), '', 5) RETURNING id")[0]
        self.assertGreater(nueva, 42)
        uno("DELETE FROM presupuesto_nomina_lineas WHERE id = %s RETURNING id", [nueva])

        # 0035 borra la tabla de respaldo.
        self.migrar([("presupuestoApp", "0035_borrar_presupuesto_nomina_respaldo")])
        self.assertNotIn("presupuesto_nomina_respaldo", connection.introspection.table_names())
        self.assertEqual(uno("SELECT COUNT(*) FROM presupuesto_nomina")[0], 24)

        # Y todo se puede revertir: los datos vuelven a la tabla horizontal.
        self.migrar(self.antes)
        with connection.cursor() as cur:
            cur.execute("SELECT id, tipo, marzo, total FROM presupuesto_nomina ORDER BY id")
            filas = cur.fetchall()
        self.assertEqual(filas[0][:3], (41, "sueldos", 300))
        self.assertEqual(filas[1][:3], (42, "cesantias", -7))


class NominaCodcostoTests(TestCase):
    """codcosto sale de conceptos_nomina según el área (NOMCOSTO), igual que la cuenta."""

    def setUp(self):
        anio = timezone.localdate().year
        for nomcosto, codcosto, cuenta in [("VENTAS", "020202", "510506"), ("Ventas", "020202", "510506"),
                                           ("VENTAS", "999999", "510506"),        # minoritario: se ignora
                                           ("ADMINISTRACIÓN", "0102", "510510")]:
            ConceptosNomina.objects.create(anio=anio, archivo="prueba", nomcosto=nomcosto,
                                           codcosto=codcosto, cuenta=cuenta)
        self.client.force_login(User.objects.create_user("admin"))

    def guardar(self, filas):
        r = self.client.post(reverse("nomina_guardar", args=["sueldos"]), json.dumps(filas),
                             content_type="application/json")
        self.assertEqual(r.json()["status"], "ok", r.content)

    def datos(self):
        return self.client.get(reverse("nomina_datos", args=["sueldos"])).json()["data"]

    def test_mapa_por_area(self):
        mapa = nomina_motor.mapa_codcostos()
        self.assertEqual(nomina_motor.cuenta_para(mapa, "ventas"), "020202")
        self.assertEqual(nomina_motor.cuenta_para(mapa, "Administracion"), "0102")

    def test_se_asigna_al_guardar_y_cambia_con_el_area(self):
        self.guardar([{"cedula": "1", "nombre": "ANA", "area": "VENTAS", "centro": "TULUA",
                       **{m: 10 for m in MESES_N}}])
        fila = self.datos()[0]
        self.assertEqual((fila["codcosto"], fila["cuenta"]), ("020202", "510506"))
        self.assertEqual(set(PresupuestoNominaMes.objects.values_list("codcosto", flat=True)), {"020202"})

        fila["area"] = "ADMINISTRACIÓN"
        self.guardar([fila])
        self.assertEqual(self.datos()[0]["codcosto"], "0102")

    def test_asignar_cuentas_completa_codcosto(self):
        linea_nomina(area="VENTAS", codcosto="", cuenta="").save()
        n = nomina_motor.asignar_cuentas()
        self.assertEqual(n, 1)
        self.assertEqual(PresupuestoNomina.objects.get().codcosto, "020202")

    def test_exportar_incluye_codcosto(self):
        linea_nomina(codcosto="020202").save()
        r = self.client.get(reverse("exportar_excel"))
        df = pd.read_excel(io.BytesIO(r.content))
        self.assertIn("codcosto", df.columns)


class NominaConfirmacionTests(TestCase):
    """Sin confirmar "presupuesto listo" no se puede subir la nómina a Cuenta 5."""

    @classmethod
    def setUpTestData(cls):
        cls.admin = User.objects.create_user("admin")
        cls.aprobador = User.objects.create_user("NICOLAS")

    def confirmar(self, listo, usuario=None):
        self.client.force_login(usuario or self.admin)
        return self.client.post(reverse("presupuestoNomina"), {"action": "confirmar_listo", "listo": "1" if listo else "0"},
                                HTTP_X_REQUESTED_WITH="XMLHttpRequest")

    def test_sin_confirmar_no_se_sube(self):
        linea_nomina().save()
        self.assertEqual(vpa.estado_cuenta5_nomina()["estado"], "sin_confirmar")
        self.client.force_login(self.aprobador)
        r = self.client.post(reverse("subir_cuenta5_nomina"))
        self.assertEqual(r.status_code, 400)
        self.assertIn("no está confirmado", r.json()["msg"])
        self.assertFalse(Cuenta5Presupuestado.objects.exists())

        r = self.client.get(reverse("dashboardPresupuesto"))
        tarjeta = {t["clave"]: t for t in r.context["tarjetas"]}["nomina"]
        self.assertEqual(tarjeta["cuenta5"]["texto"], "Sin confirmar como listo")

    def test_confirmar_y_quitar(self):
        linea_nomina().save()
        r = self.confirmar(True)
        self.assertEqual(r.json()["status"], "ok")
        config = ConfiguracionNomina.actual()
        self.assertTrue(config.listo)
        self.assertEqual(config.listo_por, "admin")
        self.assertIsNotNone(config.listo_en)
        self.assertEqual(vpa.estado_cuenta5_nomina()["estado"], "pendiente")

        self.client.force_login(self.aprobador)
        self.assertTrue(self.client.post(reverse("subir_cuenta5_nomina")).json()["success"])
        self.assertEqual(vpa.estado_cuenta5_nomina()["estado"], "subido")

        self.confirmar(False)
        config.refresh_from_db()
        self.assertEqual((config.listo, config.listo_por, config.listo_en), (False, "", None))
        self.assertEqual(vpa.estado_cuenta5_nomina()["estado"], "sin_confirmar")

    def test_pantalla_muestra_boton(self):
        self.client.force_login(self.admin)
        r = self.client.get(reverse("presupuestoNomina"))
        self.assertContains(r, "Confirmar presupuesto listo")
        self.confirmar(True)
        r = self.client.get(reverse("presupuestoNomina"))
        self.assertContains(r, "Presupuesto confirmado como listo")
        self.assertContains(r, "Quitar confirmación")

    def test_solo_usuarios_de_nomina(self):
        r = self.confirmar(True, usuario=User.objects.create_user("OTRO"))
        self.assertEqual(r.status_code, 403)
        self.assertFalse(ConfiguracionNomina.actual().listo)


# ═══════════════════════════════════════════════════════════════════════
#  URL única (/mi-presupuesto/) y asignación de presupuestos
# ═══════════════════════════════════════════════════════════════════════
class MiPresupuestoTests(TestCase):
    """Una sola URL para todos: cada usuario termina en la plantilla que tiene asignada."""

    @classmethod
    def setUpTestData(cls):
        cls.usuario = User.objects.create_user("PLOZANO")
        cls.aprobador = User.objects.create_user("NICOLAS")

    def setUp(self):
        abrir_plazo()
        self.url = reverse("mi_presupuesto")

    def test_sin_sesion_va_al_login_y_vuelve(self):
        r = self.client.get(self.url)
        self.assertEqual(r.status_code, 302)
        self.assertIn("next=" + self.url, unquote(r["Location"]))

    def test_aprobador_va_al_dashboard(self):
        self.client.force_login(self.aprobador)
        self.assertRedirects(self.client.get(self.url), reverse("dashboardPresupuesto"),
                             fetch_redirect_response=False)

    def test_un_area_abierta_entra_directo(self):
        asignar(self.usuario, AREA)
        self.client.force_login(self.usuario)
        r = self.client.get(self.url)
        self.assertRedirects(r, reverse("tabla_auxiliar_sede", args=[AREA]), fetch_redirect_response=False)
        self.assertEqual(self.client.get(r["Location"]).status_code, 200)

    def test_nomina_y_comercial_entran_directo(self):
        for clave, destino in (("nomina", "presupuestoNomina"), ("comercial", "baseComercial")):
            AsignacionPresupuesto.objects.filter(usuario=self.usuario).delete()
            asignar(self.usuario, clave)
            self.client.force_login(self.usuario)
            self.assertRedirects(self.client.get(self.url), reverse(destino), fetch_redirect_response=False)

    def test_sin_asignacion_ve_aviso(self):
        self.client.force_login(self.usuario)
        r = self.client.get(self.url)
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, "Todavía no tienes un presupuesto asignado")

    def test_varios_presupuestos_elige(self):
        asignar(self.usuario, AREA)
        asignar(self.usuario, "tecnologia")
        abrir_plazo("tecnologia")
        self.client.force_login(self.usuario)
        r = self.client.get(self.url)
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, reverse("tabla_auxiliar_sede", args=[AREA]))
        self.assertContains(r, reverse("tabla_auxiliar_sede", args=["tecnologia"]))

    def test_plazo_cerrado_no_redirige_y_ofrece_solo_consulta(self):
        asignar(self.usuario, AREA)
        abrir_plazo(dias=-1)
        self.client.force_login(self.usuario)
        r = self.client.get(self.url)
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, "Plazo cerrado")
        self.assertContains(r, reverse("presupuesto_aprobado_sede", args=[AREA]))
        self.assertNotContains(r, reverse("tabla_auxiliar_sede", args=[AREA]))

    def test_ignora_claves_que_ya_no_existen(self):
        AsignacionPresupuesto.objects.create(usuario=self.usuario, presupuesto="area-borrada")
        asignar(self.usuario, AREA)
        self.client.force_login(self.usuario)
        self.assertRedirects(self.client.get(self.url), reverse("tabla_auxiliar_sede", args=[AREA]),
                             fetch_redirect_response=False)


class PermisosPorAsignacionTests(TestCase):
    """La asignación es lo que da (y quita) el permiso de entrar."""

    @classmethod
    def setUpTestData(cls):
        cls.usuario = User.objects.create_user("PLOZANO")
        cls.otro = User.objects.create_user("PQUINTERO")

    def setUp(self):
        abrir_plazo()

    def test_area_sin_asignacion_no_entra_y_con_asignacion_si(self):
        url = reverse("tabla_auxiliar_sede", args=[AREA])
        self.client.force_login(self.usuario)
        self.assertEqual(self.client.get(url).status_code, 403)
        a = asignar(self.usuario, AREA)
        self.assertEqual(self.client.get(url).status_code, 200)
        # Solo SU área.
        self.assertEqual(self.client.get(reverse("tabla_auxiliar_sede", args=["tecnologia"])).status_code, 403)
        a.delete()
        self.assertEqual(self.client.get(url).status_code, 403)

    def test_nomina_por_asignacion(self):
        url = reverse("presupuestoNomina")
        self.client.force_login(self.otro)
        self.assertEqual(self.client.get(url).status_code, 403)
        asignar(self.otro, "nomina")
        self.assertNotEqual(self.client.get(url).status_code, 403)

    def test_comercial_por_asignacion(self):
        url = reverse("baseComercial")
        self.client.force_login(self.otro)
        self.assertEqual(self.client.get(url).status_code, 403)
        asignar(self.otro, "comercial")
        self.assertEqual(self.client.get(url).status_code, 200)

    def test_admin_sigue_entrando_sin_asignacion(self):
        self.client.force_login(User.objects.create_user("admin"))
        self.assertEqual(self.client.get(reverse("baseComercial")).status_code, 200)
        self.assertEqual(self.client.get(reverse("tabla_auxiliar_sede", args=[AREA])).status_code, 200)


class PanelAsignacionesTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.aprobador = User.objects.create_user("NICOLAS")
        cls.usuario = User.objects.create_user("PLOZANO", first_name="Pilar", last_name="Lozano")
        cls.inactivo = User.objects.create_user("VIEJO", is_active=False)

    def guardar(self, **datos):
        return self.client.post(reverse("guardar_asignacion"), json.dumps(datos), content_type="application/json")

    def test_solo_el_aprobador(self):
        self.client.force_login(self.usuario)
        self.assertEqual(self.client.get(reverse("ajustes_asignaciones")).status_code, 403)
        r = self.guardar(usuario=self.usuario.id, presupuesto=AREA, accion="asignar")
        self.assertEqual(r.status_code, 403)
        self.assertFalse(AsignacionPresupuesto.objects.exists())

    def test_pantalla_lista_usuarios_presupuestos_y_url_unica(self):
        asignar(self.usuario, AREA)
        self.client.force_login(self.aprobador)
        r = self.client.get(reverse("ajustes_asignaciones"))
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, "http://testserver" + reverse("mi_presupuesto"))
        datos = r.context["datos"]
        self.assertEqual([u["username"] for u in datos["usuarios"]], ["NICOLAS", "PLOZANO"])  # sin inactivos
        self.assertTrue(next(u for u in datos["usuarios"] if u["username"] == "NICOLAS")["aprobador"])
        claves = [p["clave"] for p in datos["presupuestos"]]
        self.assertEqual(set(claves), {*vpa.SEDE_CONFIG, "nomina", "comercial"})
        self.assertEqual(datos["asignaciones"], [{"usuario": self.usuario.id, "presupuesto": AREA}])

    def test_url_unica_con_https_detras_del_proxy(self):
        self.client.force_login(self.aprobador)
        r = self.client.get(reverse("ajustes_asignaciones"), HTTP_X_FORWARDED_PROTO="https",
                            HTTP_HOST="herramientas.up.railway.app")
        self.assertEqual(r.context["url_unica"], "https://herramientas.up.railway.app" + reverse("mi_presupuesto"))

    def test_asignar_y_quitar(self):
        self.client.force_login(self.aprobador)
        r = self.guardar(usuario=self.usuario.id, presupuesto=AREA, accion="asignar")
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.json()["asignaciones"], [{"usuario": self.usuario.id, "presupuesto": AREA}])
        a = AsignacionPresupuesto.objects.get()
        self.assertEqual((a.usuario, a.presupuesto, a.asignado_por), (self.usuario, AREA, "NICOLAS"))

        # Repetir no duplica.
        self.guardar(usuario=self.usuario.id, presupuesto=AREA, accion="asignar")
        self.assertEqual(AsignacionPresupuesto.objects.count(), 1)

        r = self.guardar(usuario=self.usuario.id, presupuesto=AREA, accion="quitar")
        self.assertEqual(r.json()["asignaciones"], [])
        self.assertFalse(AsignacionPresupuesto.objects.exists())

    def test_datos_invalidos(self):
        self.client.force_login(self.aprobador)
        self.assertEqual(self.guardar(usuario=self.usuario.id, presupuesto="no-existe", accion="asignar").status_code, 400)
        self.assertEqual(self.guardar(usuario=self.usuario.id, presupuesto=AREA, accion="borrar").status_code, 400)
        self.assertEqual(self.guardar(usuario=999999, presupuesto=AREA, accion="asignar").status_code, 404)
        self.assertEqual(self.guardar(usuario=self.inactivo.id, presupuesto=AREA, accion="asignar").status_code, 404)
        self.assertEqual(self.guardar(usuario="x", presupuesto=AREA, accion="asignar").status_code, 404)
        self.assertEqual(self.client.get(reverse("guardar_asignacion")).status_code, 405)
        self.assertFalse(AsignacionPresupuesto.objects.exists())

    def test_link_en_el_menu_de_ajustes(self):
        self.client.force_login(self.aprobador)
        r = self.client.get(reverse("ajustes_plazos_edicion"))
        self.assertContains(r, reverse("ajustes_asignaciones"))


class MigracionAsignacionesTests(TransactionTestCase):
    """0037 copia a la tabla los usuarios que antes estaban fijos en el código."""

    antes = [("presupuestoApp", "0036_nomina_codcosto_y_confirmacion")]
    despues = [("presupuestoApp", "0037_asignacion_presupuesto")]

    def migrar(self, destino):
        executor = MigrationExecutor(connection)
        executor.loader.build_graph()
        executor.migrate(destino)
        return executor.loader.project_state(destino).apps

    def tearDown(self):
        self.migrar(MigrationExecutor(connection).loader.graph.leaf_nodes())

    def test_siembra_usuarios_existentes(self):
        self.migrar(self.antes)
        for nombre in ("PLOZANO", "EVALENCIA", "pquintero", "NICOLAS", "admin"):
            User.objects.create_user(nombre)
        apps = self.migrar(self.despues)
        Asignacion = apps.get_model("presupuestoApp", "AsignacionPresupuesto")
        pares = set(Asignacion.objects.values_list("usuario__username", "presupuesto"))
        self.assertEqual(pares, {
            ("PLOZANO", "logistica"),
            ("EVALENCIA", "comercial-costos"), ("EVALENCIA", "comercial"),
            ("pquintero", "nomina"),            # coincide sin importar mayúsculas
        })
        self.migrar(self.antes)                 # reversible
        self.assertNotIn("presupuesto_asignacion", connection.introspection.table_names())


# ═══════════════════════════════════════════════════════════════════════
#  Agrupación y nombres de cuentas (tabla AgrupacionCuenta)
# ═══════════════════════════════════════════════════════════════════════
def _agrupar_como_antes(cuenta, costo):
    """Copia de la lógica que había fija en views.py antes de la tabla."""
    grupos = {
        '54100207_54100211': ['54100207', '54100208', '54100209', '54100210', '54100211'],
        '541009_541033': ['541009', '541033', '54103301', '54103302'],
        '541015_541016': ['541015', '541016'],
        '511015_511016': ['511015', '511016'],
        '51109501_51109502': ['51109501', '51109502'],
    }
    exactas = {c: d for d, cs in grupos.items() for c in cs}
    if cuenta.startswith('4'):
        return cuenta
    if costo.startswith('02040'): cuenta = '5'
    if costo == '020201' and cuenta.startswith('5405'): cuenta = '5405'
    if costo == '0101': cuenta = '5105'
    if cuenta.startswith('541001'): cuenta = '541001'
    if cuenta in exactas:
        return exactas[cuenta]
    for prefijo in ('5230', '541003', '541005', '541006', '541024', '541027', '5415'):
        if cuenta.startswith(prefijo):
            return prefijo
    return cuenta


class AgrupacionMigradaTests(TestCase):
    """La migración copia las reglas del código: el resultado no cambia."""

    def test_mismo_resultado_que_las_reglas_fijas(self):
        from .agrupacion_cuentas import cargar_reglas
        reglas = cargar_reglas()
        cuentas = [
            '54100207', '54100208', '54100211', '54100212', '541009', '54103301', '541033', '541015',
            '541016', '511015', '51109501', '51109502', '5230', '523005', '52300501', '541003',
            '54100301', '541005', '54100501', '541006', '54100699', '541024', '54102401', '541027',
            '5415', '541505', '54150501', '541001', '54100101', '54100199', '541010', '541011',
            '5405', '540505', '510506', '5105', '521015', '615035', '613522', '41750201', '4175',
            '420560', '41659505', '511', '5', '54', '5410', '541', '5412', '54101201',
        ]
        costos = ['020202', '020400', '020401', '020201', '0101', '0203', 'SIN COSTO']
        for cuenta in cuentas:
            for costo in costos:
                self.assertEqual(views.aplicar_agrupaciones(cuenta, costo, reglas),
                                 _agrupar_como_antes(cuenta, costo), (cuenta, costo))

    def test_nombres_migrados(self):
        from .agrupacion_cuentas import cargar_reglas
        reglas = cargar_reglas()
        self.assertEqual(reglas.nombre('54100207_54100211'), 'Tasas Bomberil-otras')
        self.assertEqual(reglas.nombre('541001'), 'Honorarios')
        self.assertEqual(reglas.nombre('AT-00003'), 'Convenio Elanco')
        self.assertEqual(reglas.nombre('5'), 'Proyecto de Aftosa')
        self.assertIsNone(reglas.nombre('541010'))


class AgrupacionCuentasPantallaTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.aprobador = User.objects.create_user("NICOLAS")
        cls.area = User.objects.create_user("PLOZANO")

    def post(self, nombre, datos):
        return self.client.post(reverse(nombre), json.dumps(datos), content_type="application/json")

    def guardar(self, **datos):
        return self.post("guardar_agrupacion_cuenta", datos)

    def test_solo_el_aprobador(self):
        self.client.force_login(self.area)
        self.assertEqual(self.client.get(reverse("ajustes_agrupacion_cuentas")).status_code, 403)
        self.assertEqual(self.guardar(codigo="X1", nombre="x").status_code, 403)
        self.assertEqual(self.post("eliminar_agrupacion_cuenta", {"id": 1}).status_code, 403)
        self.assertEqual(self.post("vista_previa_agrupacion_cuenta", {}).status_code, 403)

    def test_pantalla_lista_las_reglas_migradas(self):
        self.client.force_login(self.aprobador)
        r = self.client.get(reverse("ajustes_agrupacion_cuentas"))
        self.assertEqual(r.status_code, 200)
        filas = {f["codigo"]: f for f in r.context["datos"]["filas"]}
        self.assertEqual(filas["54100207_54100211"]["cuentas"][0], "54100207")
        self.assertEqual(filas["5230"]["prefijos"], ["5230"])
        self.assertContains(r, reverse("ajustes_agrupacion_cuentas"))     # enlace en el menú

    def test_agregar_cuenta_a_un_grupo_cambia_el_consolidado(self):
        from .agrupacion_cuentas import cargar_reglas
        from .models import AgrupacionCuenta
        self.client.force_login(self.aprobador)
        self.assertEqual(views.aplicar_agrupaciones("54100212", "020202"), "54100212")
        g = AgrupacionCuenta.objects.get(codigo="54100207_54100211")
        r = self.guardar(id=g.id, codigo=g.codigo, nombre="Tasas y otras",
                         cuentas=g.cuentas + ["54100212"], prefijos=[])
        self.assertEqual(r.status_code, 200, r.content)
        reglas = cargar_reglas()
        self.assertEqual(views.aplicar_agrupaciones("54100212", "020202", reglas), "54100207_54100211")
        self.assertEqual(reglas.nombre("54100207_54100211"), "Tasas y otras")

    def test_crear_prefijo_y_eliminar(self):
        from .models import AgrupacionCuenta
        self.client.force_login(self.aprobador)
        OrdenCuenta.objects.create(mcncuenta="541010", orden=10)
        r = self.guardar(codigo="5410_SERV", nombre="Servicios", cuentas="541010, 541011", prefijos=["541045"])
        self.assertEqual(r.status_code, 200, r.content)
        self.assertTrue(r.json()["agregada_orden"])
        self.assertTrue(OrdenCuenta.objects.filter(mcncuenta="5410_SERV", visible_total=True).exists())
        self.assertEqual(views.aplicar_agrupaciones("54104501", "020202"), "5410_SERV")
        self.assertEqual(views.aplicar_agrupaciones("541011", "020202"), "5410_SERV")
        # El prefijo más largo gana sobre uno más corto de otra fila.
        self.guardar(codigo="5410_GEN", nombre="General", prefijos=["5410"])
        self.assertEqual(views.aplicar_agrupaciones("54104501", "020202"), "5410_SERV")
        self.assertEqual(views.aplicar_agrupaciones("54109999", "020202"), "5410_GEN")

        fila = AgrupacionCuenta.objects.get(codigo="5410_SERV")
        r = self.post("eliminar_agrupacion_cuenta", {"id": fila.id})
        self.assertEqual(r.status_code, 200)
        self.assertEqual(views.aplicar_agrupaciones("541011", "020202"), "5410_GEN")

    def test_validaciones(self):
        from .models import AgrupacionCuenta
        self.client.force_login(self.aprobador)
        casos = [
            dict(codigo="", nombre="x"),
            dict(codigo="mal código", nombre="x"),
            dict(codigo="5230", nombre="duplicado"),
            dict(codigo="N1", nombre=""),
            dict(codigo="N2", nombre="x", cuentas=["41750201"]),
            dict(codigo="N3", nombre="x", prefijos=["4175"]),
            dict(codigo="N4", nombre="x", cuentas=["54100208"]),     # ya está en otra fila
            dict(codigo="N5", nombre="x", prefijos=["5230"]),        # prefijo repetido
            dict(codigo="N6", nombre="x", prefijos=["5"]),           # muy corto
            dict(codigo="N7", nombre="x", cuentas=["54a"]),
        ]
        antes = AgrupacionCuenta.objects.count()
        for caso in casos:
            r = self.guardar(**caso)
            self.assertEqual(r.status_code, 400, caso)
            self.assertTrue(r.json()["errores"], caso)
        self.assertEqual(AgrupacionCuenta.objects.count(), antes)
        g = AgrupacionCuenta.objects.get(codigo="5230")
        r = self.guardar(id=g.id, codigo="OTRO", nombre="x", prefijos=["5230"])
        self.assertEqual(r.status_code, 400)          # el código no se cambia
        self.assertEqual(self.post("eliminar_agrupacion_cuenta", {"id": 999999}).status_code, 404)

    def test_vista_previa(self):
        from .models import AgrupacionCuenta
        self.client.force_login(self.aprobador)
        for cta, nom in (("52300501", "IVA OBSEQUIOS"), ("54100208", "TASA BOMBERIL"), ("54100299", "OTRA TASA")):
            Cuenta5Presupuestado.objects.create(mcncuenta=cta, ctanombre=nom)
        g = AgrupacionCuenta.objects.get(codigo="54100207_54100211")
        r = self.post("vista_previa_agrupacion_cuenta",
                      {"id": g.id, "codigo": g.codigo, "cuentas": ["54100208"], "prefijos": ["541002"]}).json()
        por_cuenta = {f["cuenta"]: f for f in r["filas"]}
        self.assertTrue(por_cuenta["54100208"]["aqui"])
        self.assertEqual(por_cuenta["54100208"]["motivo"], "cuenta exacta")
        self.assertEqual(por_cuenta["54100299"]["motivo"], "empieza por 541002")
        self.assertNotIn("52300501", por_cuenta)
        # Una cuenta exacta de OTRA fila gana sobre el prefijo nuevo.
        r = self.post("vista_previa_agrupacion_cuenta", {"codigo": "NUEVA", "prefijos": ["5410"]}).json()
        f = {x["cuenta"]: x for x in r["filas"]}["54100208"]
        self.assertFalse(f["aqui"])
        self.assertEqual(f["destino"], "54100207_54100211")


class CerrarSesionEnGrillasTests(TestCase):
    def test_pantallas_de_presupuesto_tienen_cerrar_sesion(self):
        usuario = User.objects.create_user("PLOZANO", first_name="Pilar")
        asignar(usuario, AREA)
        abrir_plazo()
        self.client.force_login(usuario)
        for url in (reverse("tabla_auxiliar_sede", args=[AREA]), reverse("presupuesto_aprobado_sede", args=[AREA])):
            r = self.client.get(url)
            self.assertContains(r, 'action="%s"' % reverse("logout"))
            self.assertContains(r, "Hola, Pilar")
        self.client.force_login(User.objects.create_user("NICOLAS"))
        self.assertContains(self.client.get(reverse("presupuesto_sede", args=[AREA])), "Cerrar sesión")


class ComercialGastosTests(TransactionTestCase):
    """0039: 'comercial-costos' pasa a 'comercial-gastos' sin perder datos."""

    antes = [("presupuestoApp", "0038_agrupacion_cuenta")]
    despues = [("presupuestoApp", "0039_renombrar_comercial_gastos")]

    def migrar(self, destino):
        executor = MigrationExecutor(connection)
        executor.loader.build_graph()
        executor.migrate(destino)
        return executor.loader.project_state(destino).apps

    def tearDown(self):
        self.migrar(MigrationExecutor(connection).loader.graph.leaf_nodes())

    def test_migracion_ida_y_vuelta(self):
        apps = self.migrar(self.antes)
        usuario = User.objects.create_user("EVALENCIA")
        Area = apps.get_model("presupuestoApp", "PresupuestoArea")
        Plazo = apps.get_model("presupuestoApp", "PlazoEdicionArea")
        Asig = apps.get_model("presupuestoApp", "AsignacionPresupuesto")
        C5 = apps.get_model("presupuestoApp", "Cuenta5Presupuestado")
        Area.objects.create(area="comercial-costos", etapa="auxiliar", linea=1, fecha=datetime.date(ANIO, 1, 1), valor=5)
        Area.objects.create(area="logistica", etapa="auxiliar", linea=1, fecha=datetime.date(ANIO, 1, 1), valor=7)
        Plazo.objects.create(area="comercial-costos", fecha_limite=datetime.date(ANIO, 1, 1))
        Asig.objects.create(usuario_id=usuario.id, presupuesto="comercial-costos")
        C5.objects.create(mcncuenta="511001", origen_area="comercial-costos")

        apps = self.migrar(self.despues)
        for modelo, campo in (("PresupuestoArea", "area"), ("PlazoEdicionArea", "area"),
                              ("AsignacionPresupuesto", "presupuesto"), ("Cuenta5Presupuestado", "origen_area")):
            M = apps.get_model("presupuestoApp", modelo)
            self.assertFalse(M.objects.filter(**{campo: "comercial-costos"}).exists(), modelo)
            self.assertTrue(M.objects.filter(**{campo: "comercial-gastos"}).exists(), modelo)
        self.assertTrue(apps.get_model("presupuestoApp", "PresupuestoArea").objects.filter(area="logistica").exists())

        apps = self.migrar(self.antes)
        self.assertTrue(apps.get_model("presupuestoApp", "PresupuestoArea").objects.filter(area="comercial-costos").exists())


class ComercialGastosVistasTests(TestCase):
    def test_nombre_y_enlaces(self):
        self.assertEqual(vpa.SEDE_CONFIG["comercial-gastos"]["label"], "Comercial y Gastos")
        self.assertNotIn("comercial-costos", vpa.SEDE_CONFIG)
        usuario = User.objects.create_user("EVALENCIA")
        asignar(usuario, "comercial-gastos")
        abrir_plazo("comercial-gastos")
        self.client.force_login(usuario)
        r = self.client.get(reverse("mi_presupuesto"))
        self.assertRedirects(r, "/presupuesto/area/comercial-gastos/auxiliar/", fetch_redirect_response=False)
        self.assertContains(self.client.get(r["Location"]), "Presupuesto Comercial y Gastos")
        # Un enlace viejo guardado sigue funcionando.
        self.assertRedirects(self.client.get("/presupuesto/area/comercial-costos/auxiliar/"),
                             "/presupuesto/area/comercial-gastos/auxiliar/", fetch_redirect_response=False)

    def test_tarjeta_del_dashboard(self):
        self.client.force_login(User.objects.create_user("NICOLAS"))
        r = self.client.get(reverse("dashboardPresupuesto"))
        self.assertContains(r, "Comercial y Gastos")
        self.assertContains(r, "/presupuesto/area/comercial-gastos/")


class OrdenCuentasNombresTests(TestCase):
    """Sincronizar completa los nombres vacíos y el nombre se comparte con Agrupación de cuentas."""

    @classmethod
    def setUpTestData(cls):
        cls.aprobador = User.objects.create_user("NICOLAS")

    def setUp(self):
        self.client.force_login(self.aprobador)

    def test_sincronizar_completa_nombres_vacios_y_respeta_los_escritos(self):
        from .models import AgrupacionCuenta
        OrdenCuenta.objects.create(mcncuenta="54100207_54100211", orden=10)              # agrupación
        OrdenCuenta.objects.create(mcncuenta="1", orden=20)                              # cuenta clave
        OrdenCuenta.objects.create(mcncuenta="541010", orden=30)                         # con movimientos
        OrdenCuenta.objects.create(mcncuenta="541011", orden=40, ctanombre="Mi nombre")  # ya escrito
        OrdenCuenta.objects.create(mcncuenta="999999", orden=50)                         # desconocida
        Cuenta5Presupuestado.objects.create(mcncuenta="541010", ctanombre="ASEO Y ELEMENTOS",
                                            mcnfecha=46023, mcnvaldebi=10, mcnccosto="020202")
        r = self.client.post(reverse("sincronizar_orden_cuentas"))
        self.assertEqual(r.status_code, 200, r.content)
        self.assertGreaterEqual(r.json()["nombres"], 3)
        nombres = dict(OrdenCuenta.objects.values_list("mcncuenta", "ctanombre"))
        self.assertEqual(nombres["54100207_54100211"], "Tasas Bomberil-otras")
        self.assertEqual(nombres["1"], "Ventas a crédito")
        self.assertEqual(nombres["541010"], "Aseo y elementos")
        self.assertEqual(nombres["541011"], "Mi nombre")
        self.assertEqual(nombres["999999"], "")
        # listar trae el sugerido para las vacías
        data = {d["mcncuenta"]: d for d in self.client.get(reverse("listar_orden_cuentas")).json()["data"]}
        self.assertEqual(data["54100207_54100211"]["sugerido"], "Tasas Bomberil-otras")

    def test_nombre_compartido_en_las_dos_pantallas(self):
        from .models import AgrupacionCuenta
        OrdenCuenta.objects.create(mcncuenta="5230", orden=10, ctanombre="Viejo")
        # Orden de cuentas -> Agrupación
        self.client.post(reverse("guardar_orden_cuentas"), json.dumps({"cuentas": [
            {"mcncuenta": "5230", "ctanombre": "IVA obsequios", "visible_total": True, "visible_sede": True}]}),
            content_type="application/json")
        self.assertEqual(AgrupacionCuenta.objects.get(codigo="5230").nombre, "IVA obsequios")
        # Agrupación -> Orden de cuentas
        g = AgrupacionCuenta.objects.get(codigo="5230")
        self.client.post(reverse("guardar_agrupacion_cuenta"), json.dumps(
            {"id": g.id, "codigo": "5230", "nombre": "Gastos no operacionales", "cuentas": [], "prefijos": ["5230"]}),
            content_type="application/json")
        self.assertEqual(OrdenCuenta.objects.get(mcncuenta="5230").ctanombre, "Gastos no operacionales")

    def test_aviso_de_orden_vacia_solo_si_esta_vacia(self):
        r = self.client.get(reverse("ajustes_agrupacion_cuentas"))
        self.assertTrue(r.context["datos"]["orden_vacia"])
        OrdenCuenta.objects.create(mcncuenta="1", orden=10)
        r = self.client.get(reverse("ajustes_agrupacion_cuentas"))
        self.assertFalse(r.context["datos"]["orden_vacia"])
