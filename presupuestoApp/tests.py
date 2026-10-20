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
from .models_nomina import CorreccionPersonaNomina, FilaEliminadaNomina  # noqa: E402
from .models_nomina import (  # noqa: E402
    ConceptosNomina, ConfiguracionNomina, PresupuestoNomina, PresupuestoNominaMes,
)
from . import nomina_motor  # noqa: E402
from . import nomina_conceptos as origen_nomina  # noqa: E402


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


class CambiarCodigoFilaTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.aprobador = User.objects.create_user("NICOLAS")

    def setUp(self):
        self.client.force_login(self.aprobador)

    def guardar(self, fila, **cambios):
        datos = {"id": fila.id, "codigo": fila.codigo, "nombre": fila.nombre,
                 "cuentas": fila.cuentas, "prefijos": fila.prefijos, **cambios}
        return self.client.post(reverse("guardar_agrupacion_cuenta"), json.dumps(datos),
                                content_type="application/json")

    def test_cambia_el_codigo_y_se_lleva_orden_y_comentarios(self):
        from .models import AgrupacionCuenta, ComentarioComparativo
        g = AgrupacionCuenta.objects.get(codigo="54100207_54100211")
        OrdenCuenta.objects.create(mcncuenta=g.codigo, orden=70, visible_sede=True)
        ComentarioComparativo.objects.create(sede="tulua", fila_key=g.codigo, mcncuenta=g.codigo, comentario="ojo")
        r = self.guardar(g, codigo="5410_TASAS")
        self.assertEqual(r.status_code, 200, r.content)
        self.assertIn("54100207_54100211 → 5410_TASAS", r.json()["msg"])
        self.assertFalse(AgrupacionCuenta.objects.filter(codigo="54100207_54100211").exists())
        o = OrdenCuenta.objects.get(mcncuenta="5410_TASAS")
        self.assertEqual((o.orden, o.visible_sede, o.ctanombre), (70, True, "Tasas Bomberil-otras"))
        self.assertEqual(ComentarioComparativo.objects.get(sede="tulua").fila_key, "5410_TASAS")
        self.assertEqual(views.aplicar_agrupaciones("54100208", "020202"), "5410_TASAS")

    def test_no_se_puede_cambiar(self):
        from .models import AgrupacionCuenta
        casos = [
            (AgrupacionCuenta.objects.get(codigo="54100207_54100211"), "51_TASAS"),   # cambia de subtotal
            (AgrupacionCuenta.objects.get(codigo="5230"), "5230_IVA"),                # lo usan las tablas
            (AgrupacionCuenta.objects.get(codigo="5"), "5X"),                         # regla fija
            (AgrupacionCuenta.objects.get(codigo="AT-00003"), "AT-99"),               # solo nombre
            (AgrupacionCuenta.objects.get(codigo="541009_541033"), "541015_541016"),  # ya existe
        ]
        for fila, nuevo in casos:
            r = self.guardar(fila, codigo=nuevo)
            self.assertEqual(r.status_code, 400, (fila.codigo, nuevo))
            self.assertTrue(AgrupacionCuenta.objects.filter(codigo=fila.codigo).exists())
        OrdenCuenta.objects.create(mcncuenta="541099", orden=1)
        self.assertEqual(self.guardar(AgrupacionCuenta.objects.get(codigo="541009_541033"),
                                      codigo="541099").status_code, 400)

    def test_lista_indica_si_el_codigo_es_fijo(self):
        r = self.client.get(reverse("ajustes_agrupacion_cuentas"))
        filas = {f["codigo"]: f for f in r.context["datos"]["filas"]}
        self.assertEqual(filas["54100207_54100211"]["codigo_fijo"], "")
        self.assertTrue(filas["5415"]["codigo_fijo"])
        self.assertTrue(filas["AT-00003"]["codigo_fijo"])


class FilasCalculadasTests(TestCase):
    """Ajustes → Filas calculadas: qué cuentas suma cada fila sin cuenta propia."""

    @classmethod
    def setUpTestData(cls):
        cls.aprobador = User.objects.create_user("NICOLAS")
        cls.area = User.objects.create_user("PLOZANO")

    def post(self, nombre, datos):
        return self.client.post(reverse(nombre), json.dumps(datos), content_type="application/json")

    def test_por_defecto_son_las_cuentas_que_estaban_en_las_plantillas(self):
        from .subtotales import configuracion_para_tablas
        c = configuracion_para_tablas()
        self.assertEqual(c["OtrosIngresos"]["cuentas"], [
            "41659505", "41659501", "422004", "422507", "422529", "4240900202", "4240900301",
            "4240900401", "4240909501", "4240909503", "4240909901", "4", "420560"])
        self.assertEqual(c["GastosPorServicios"]["cuentas"], ["5", "6", "7", "8", "5230"])
        self.assertEqual(c["51"]["prefijos"], ["51"])
        self.assertEqual(c["54"]["prefijos"], ["54"])
        self.assertEqual(c["VentasNetas"]["prefijos"], ["1", "2", "41750201"])
        self.assertEqual(c["GastosFinancieros"]["prefijos"], ["521005", "521015", "521020", "3", "615035"])
        self.assertEqual(c["AsistenciaTecnica"]["prefijos"], ["AT", "VT"])

    def test_solo_el_aprobador(self):
        self.client.force_login(self.area)
        self.assertEqual(self.client.get(reverse("ajustes_filas_calculadas")).status_code, 403)
        self.assertEqual(self.post("guardar_fila_calculada", {"clave": "51"}).status_code, 403)
        self.assertEqual(self.post("restaurar_fila_calculada", {"clave": "51"}).status_code, 403)
        self.assertEqual(self.post("vista_previa_fila_calculada", {"clave": "51"}).status_code, 403)

    def test_guardar_y_restaurar(self):
        from .models import SubtotalCuentas
        self.client.force_login(self.aprobador)
        self.assertEqual(self.client.get(reverse("ajustes_filas_calculadas")).status_code, 200)
        r = self.post("guardar_fila_calculada",
                      {"clave": "OtrosIngresos", "cuentas": "41659505, at-00003 41659505", "prefijos": ["4250"]})
        self.assertEqual(r.status_code, 200, r.content)
        fila = next(f for f in r.json()["filas"] if f["clave"] == "OtrosIngresos")
        self.assertEqual(fila["cuentas"], ["41659505", "AT-00003"])     # sin repetidos, en mayúsculas
        self.assertEqual(fila["prefijos"], ["4250"])
        self.assertTrue(fila["personalizado"])
        self.assertEqual(SubtotalCuentas.objects.get(clave="OtrosIngresos").actualizado_por, "NICOLAS")

        r = self.post("restaurar_fila_calculada", {"clave": "OtrosIngresos"})
        fila = next(f for f in r.json()["filas"] if f["clave"] == "OtrosIngresos")
        self.assertFalse(fila["personalizado"])
        self.assertEqual(len(fila["cuentas"]), 13)
        self.assertFalse(SubtotalCuentas.objects.exists())

    def test_validacion(self):
        self.client.force_login(self.aprobador)
        self.assertEqual(self.post("guardar_fila_calculada", {"clave": "51", "cuentas": ["51 01!"]}).status_code, 400)
        r = self.post("guardar_fila_calculada", {"clave": "51", "cuentas": ["5105"], "prefijos": ["5105"]})
        self.assertEqual(r.status_code, 400)
        self.assertIn("cuenta exacta y como prefijo", r.json()["msg"])
        self.assertEqual(self.post("guardar_fila_calculada", {"clave": "NoExiste"}).status_code, 404)
        # Vacía se permite (la fila queda en 0) y se avisa
        r = self.post("guardar_fila_calculada", {"clave": "GastosFinancieros", "cuentas": [], "prefijos": []})
        self.assertEqual(r.status_code, 200)
        self.assertIn("quedará en 0", r.json()["msg"])

    def test_vista_previa_y_avisos(self):
        OrdenCuenta.objects.create(mcncuenta="511001", ctanombre="Sueldos", orden=10, visible_total=True, visible_sede=True)
        OrdenCuenta.objects.create(mcncuenta="41750105", ctanombre="Devolución", orden=20, visible_total=True, visible_sede=False)
        self.client.force_login(self.aprobador)
        r = self.post("vista_previa_fila_calculada",
                      {"clave": "OtrosIngresos", "cuentas": ["41750105", "511001", "999999"]}).json()
        filas = {f["cuenta"]: f for f in r["filas"]}
        self.assertEqual(set(filas), {"41750105", "511001"})
        self.assertEqual(filas["41750105"]["oculta"], "solo en Total Base")
        self.assertEqual(filas["511001"]["tambien"], ["Gastos de Administración"])   # se contaría dos veces
        self.assertTrue(any("999999 no está en Orden de cuentas" in a for a in r["avisos"]))
        self.assertTrue(any("otra fila calculada" in a for a in r["avisos"]))

    def test_las_tablas_reciben_la_configuracion(self):
        self.client.force_login(self.aprobador)
        self.post("guardar_fila_calculada", {"clave": "GastosPorServicios", "cuentas": ["5", "6", "5230", "529595"]})
        for nombre in ("consolidado_general", "presupuestado_general", "comparativo_general"):
            r = self.client.get(reverse(nombre))
            self.assertEqual(r.status_code, 200, nombre)
            self.assertEqual(r.context["subtotales"]["GastosPorServicios"]["cuentas"], ["5", "6", "5230", "529595"])
            html = r.content.decode()
            self.assertIn('id="configSubtotales"', html, nombre)
            self.assertRegex(html, r"js/subtotales\.js\?v=\d+")


class SubidaLotesExcelTests(TestCase):
    """Subida de los Excel de Cuenta 4 / 5 por lotes: bulk_create, formato compacto y gzip."""

    COLS = ["mcncuenta", "mcnfecha", "mcnvaldebi", "mcnvalcred", "ctanombre"]

    def subir(self, nombre, datos, gzip_=False, **extra):
        import gzip
        cuerpo = json.dumps(datos).encode()
        if gzip_:
            return self.client.post(reverse(nombre), gzip.compress(cuerpo), content_type="application/octet-stream",
                                    HTTP_X_COMPRESION="gzip", **extra)
        return self.client.post(reverse(nombre), cuerpo, content_type="application/json", **extra)

    def test_formato_compacto_con_gzip_conserva_orden_y_valores(self):
        from .models import Cuenta5Base
        filas = [[f"5105{i:02d}", 46023.0 + i, 1000.0 * i, 0.0, "SUELDOS"] for i in range(25)]
        r = self.subir("subir_excel_cuenta5", {"columnas": self.COLS, "filas": filas}, gzip_=True, HTTP_X_LOTE="1/1")
        self.assertEqual(r.json(), {"status": "ok", "insertados": 25})
        guardadas = list(Cuenta5Base.objects.order_by("id").values_list("mcncuenta", "mcnfecha", "mcnvaldebi"))
        self.assertEqual(guardadas, [(f[0], f[1], f[2]) for f in filas])

    def test_formato_anterior_sigue_funcionando_en_las_cuatro_cargas(self):
        from .models import Cuenta4Base, Cuenta4Presupuestado, Cuenta5Base, Cuenta5Presupuestado
        registro = {"mcncuenta": "510506", "mcnfecha": 46023, "mcnvaldebi": 5.0, "mcnvalcred": None}
        for nombre, modelo in (("subir_excel_cuenta5", Cuenta5Base), ("subir_excel_cuenta5_presupuestado", Cuenta5Presupuestado),
                               ("subir_excel_cuenta4", Cuenta4Base), ("subir_excel_cuenta4_presupuestado", Cuenta4Presupuestado)):
            r = self.subir(nombre, {"registros": [registro, registro]})
            self.assertEqual(r.json()["insertados"], 2, nombre)
            self.assertEqual(modelo.objects.filter(mcncuenta="510506").count(), 2, nombre)

    def test_errores_no_guardan_nada_del_lote(self):
        from .models import Cuenta5Base
        r = self.subir("subir_excel_cuenta5", {"columnas": self.COLS + ["no_existe"], "filas": [[1, 2, 3, 4, 5, 6]]})
        self.assertEqual(r.status_code, 400)
        self.assertIn("no_existe", r.json()["message"])
        r = self.subir("subir_excel_cuenta5", {"columnas": self.COLS, "filas": [["5105", 1, 2, 3, "x"], ["5105", 1]]})
        self.assertEqual(r.status_code, 400)
        self.assertIn("fila 2", r.json()["message"])
        r = self.subir("subir_excel_cuenta5", {"registros": [{"id": 99, "mcncuenta": "1"}]})   # la llave no se puede mandar
        self.assertEqual(r.status_code, 400)
        r = self.subir("subir_excel_cuenta5", {"columnas": self.COLS, "filas": [["5105", "no-es-numero", 1, 0, "x"]]})
        self.assertEqual(r.status_code, 400)
        self.assertFalse(Cuenta5Base.objects.exists())

    def test_inserta_en_pocas_consultas(self):
        filas = [[f"5105{i % 90:02d}", 46023.0, 1.0, 0.0, "X"] for i in range(2500)]
        from django.db import connection
        from django.test.utils import CaptureQueriesContext
        with CaptureQueriesContext(connection) as ctx:
            r = self.subir("subir_excel_cuenta5", {"columnas": self.COLS, "filas": filas})
        self.assertEqual(r.json()["insertados"], 2500)
        inserts = [q for q in ctx.captured_queries if q["sql"].lstrip().upper().startswith("INSERT")]
        self.assertLess(len(inserts), 100)          # antes: 2.500 INSERT (uno por fila)


class FilasCalculadasEnOrdenTests(TestCase):
    """Las filas calculadas (CALC-...) están en Orden de cuentas y las tablas las ubican por esa lista."""

    @classmethod
    def setUpTestData(cls):
        cls.aprobador = User.objects.create_user("NICOLAS")

    def test_ubicar_las_pone_donde_estaban_y_no_mueve_nada(self):
        from . import filas_calculadas as fc
        base = ["1", "2", "41750201", "613522", "4240900101", "4240909502", "5405", "5415", "542005",
                "5105", "511534", "521005", "615035", "AT-00004", "VT-00001", "41659505", "5", "5230"]
        r = fc.ubicar(base)
        self.assertEqual([c for c in r if not fc.es_calculada(c)], base)       # las cuentas no se mueven
        self.assertEqual(r[0], "CALC-VENTAS-NETAS")
        siguiente = lambda c: r[r.index(c) + 1]
        self.assertEqual(siguiente("613522"), "CALC-PCT-COSTO-VENTAS")
        self.assertEqual(siguiente("4240909502"), "CALC-MARGEN-CONTRIBUCION")
        self.assertEqual(r[r.index("5405") - 1], "CALC-GASTOS-VENTAS")
        self.assertEqual(siguiente("511534"), "CALC-UTILIDAD-OPERACIONAL")
        self.assertEqual(r[r.index("5") - 1], "CALC-GASTOS-SERVICIOS")
        self.assertEqual(r[-2:], ["CALC-EXCEDENTES", "CALC-PCT-EXCEDENTES"])
        self.assertEqual(fc.ubicar(r), r)                                       # idempotente
        movida = [c for c in r if c != "CALC-MARGEN-BRUTO"] + ["CALC-MARGEN-BRUTO"]
        self.assertEqual(fc.ubicar(movida), movida)                             # respeta lo que movió el usuario

    def test_migracion_agrega_las_calculadas_a_un_orden_existente(self):
        import importlib
        from django.apps import apps
        from . import filas_calculadas as fc
        mig = importlib.import_module("presupuestoApp.migrations.0041_orden_filas_calculadas")
        cuentas = ["1", "2", "613522", "5405", "5105", "5230"]
        for i, c in enumerate(cuentas):
            OrdenCuenta.objects.create(mcncuenta=c, orden=i * 7 + 3, visible_sede=c != "5230")
        mig.agregar(apps, None)
        filas = list(OrdenCuenta.objects.order_by("orden"))
        self.assertEqual([o.mcncuenta for o in filas], fc.ubicar(cuentas))
        self.assertEqual([o.orden for o in filas], [(i + 1) * 10 for i in range(len(filas))])
        vn = OrdenCuenta.objects.get(mcncuenta="CALC-VENTAS-NETAS")
        self.assertEqual((vn.ctanombre, vn.visible_total, vn.visible_sede), ("VENTAS NETAS", True, True))
        self.assertFalse(OrdenCuenta.objects.get(mcncuenta="CALC-OTROS-INGRESOS").visible_sede)
        mig.agregar(apps, None)
        self.assertEqual(OrdenCuenta.objects.count(), len(filas))
        mig.quitar(apps, None)
        self.assertEqual(sorted(OrdenCuenta.objects.values_list("mcncuenta", flat=True)), sorted(cuentas))

    def test_sincronizar_vuelve_a_agregar_las_que_falten(self):
        for i, c in enumerate(["1", "613522", "5405", "CALC-VENTAS-NETAS"]):
            OrdenCuenta.objects.create(mcncuenta=c, orden=(i + 1) * 10)
        self.client.force_login(self.aprobador)
        with mock.patch.object(views, "_cuentas_detectadas", return_value={}):
            r = self.client.post(reverse("sincronizar_orden_cuentas"))
        self.assertTrue(r.json()["success"], r.content)
        codigos = list(OrdenCuenta.objects.order_by("orden").values_list("mcncuenta", flat=True))
        self.assertEqual(codigos.count("CALC-VENTAS-NETAS"), 1)
        self.assertEqual(codigos[codigos.index("613522") + 1], "CALC-PCT-COSTO-VENTAS")
        self.assertEqual(sum(c.startswith("CALC-") for c in codigos), 17)
        listado = {d["mcncuenta"]: d for d in self.client.get(reverse("listar_orden_cuentas")).json()["data"]}
        self.assertTrue(listado["CALC-MARGEN-BRUTO"]["calculada"])
        self.assertFalse(listado["613522"]["calculada"])

    def test_las_tablas_reciben_el_orden_con_las_calculadas_y_sus_nombres(self):
        self.client.force_login(self.aprobador)
        with mock.patch.object(views, "calcular_movimientos", return_value={"success": True, "data": {}}):
            total = self.client.get(reverse("obtener_consolidado")).json()
            sede = self.client.get(reverse("obtener_presupuestado") + "?sede=tulua").json()
            self.assertEqual(sum(c.startswith("CALC-") for c in total["orden"]), 17)
            self.assertIn("CALC-GASTOS-FINANCIEROS", total["orden"])
            self.assertNotIn("CALC-GASTOS-FINANCIEROS", sede["orden"])     # solo en Total
            self.assertIn("CALC-UTILIDAD-OPERACIONAL", sede["orden"])
            self.assertEqual(total["calculadas"]["CALC-MARGEN-BRUTO"], "Margen Bruto")
            # Renombrada en Orden de cuentas -> las tablas usan ese nombre
            OrdenCuenta.objects.create(mcncuenta="CALC-MARGEN-BRUTO", ctanombre="MARGEN BRUTO TOTAL", orden=10)
            OrdenCuenta.objects.create(mcncuenta="1", orden=5)
            total = self.client.get(reverse("obtener_consolidado")).json()
        self.assertEqual(total["orden"], ["1", "CALC-MARGEN-BRUTO"])
        self.assertEqual(total["calculadas"], {"CALC-MARGEN-BRUTO": "MARGEN BRUTO TOTAL"})

    def test_agrupacion_no_puede_usar_codigos_calc(self):
        self.client.force_login(self.aprobador)
        r = self.client.post(reverse("guardar_agrupacion_cuenta"), json.dumps(
            {"codigo": "CALC-MIO", "nombre": "x", "cuentas": ["541099"]}), content_type="application/json")
        self.assertEqual(r.status_code, 400)
        self.assertIn("reservados", r.json()["msg"])


class CodigoCostoPorCentroTests(TestCase):
    """El código de costo sale SIEMPRE del centro ("Nombre asignación del gasto")."""

    @classmethod
    def setUpTestData(cls):
        cls.aprobador = User.objects.create_user("NICOLAS")

    def setUp(self):
        self.client.force_login(self.aprobador)

    def aprobar_tal_cual(self, filas):
        """Guarda la versión aprobada SIN pasar por filas_verticales (como datos viejos)."""
        registros = []
        for linea, f in enumerate(filas, start=1):
            for mes in MESES:
                registros.append(PresupuestoArea(
                    area=AREA, etapa="aprobado", version=1, fecha_version=timezone.localdate(),
                    linea=linea, fecha=fecha_mes(ANIO, mes), valor=f[mes],
                    **{c: f.get(c) for c in ("mcnzona", "zonnombre", "mcnccosto", "responsable",
                                             "mcncuenta", "ctanombre", "mcndetalle")},
                ))
        PresupuestoArea.objects.bulk_create(registros)

    def test_subir_usa_el_codigo_del_centro_aunque_lo_guardado_sea_otro(self):
        # Caso reportado: Tuluá es 020202 pero la línea quedó guardada con 020201
        # (cuenta 540531 o plantilla con un código viejo).
        self.aprobar_tal_cual([
            fila("tulua", 100, mcncuenta="540531", mcnccosto="020201"),
            fila("buga", 100, zonnombre="ALMACEN BUGA", mcnccosto="020202"),
            fila("otro centro", 100, zonnombre="CENTRO NUEVO", mcnccosto="9999"),
        ])
        r = self.client.post(reverse("subir_cuenta5_sede", args=[AREA]))
        self.assertEqual(r.status_code, 200, r.content)
        qs = Cuenta5Presupuestado.objects.filter(origen_area=AREA)
        self.assertEqual(set(qs.filter(mcndetalle="tulua").values_list("mcnccosto", flat=True)), {"020202"})
        self.assertEqual(set(qs.filter(mcndetalle="buga").values_list("mcnccosto", flat=True)), {"020200"})
        # Centro desconocido: se conserva el código guardado.
        self.assertEqual(set(qs.filter(mcndetalle="otro centro").values_list("mcnccosto", flat=True)), {"9999"})

    def test_al_guardar_se_corrige_el_codigo(self):
        regs = filas_verticales([fila("x", 1, zonnombre="almacen tulua ", mcnccosto="020201")],
                                area=AREA, etapa="auxiliar")
        self.assertEqual({r.mcnccosto for r in regs}, {"020202"})

    def test_mapa_igual_al_de_la_grilla(self):
        import pathlib, re as _re
        from .models_presupuesto import CODIGO_COSTO_POR_CENTRO
        js = (pathlib.Path(__file__).parent / "static/js/grilla_presupuesto.js").read_text(encoding="utf-8")
        bloque = _re.search(r"const OPCIONES_NOMBRE_CENTRO = \{(.*?)\};", js, _re.S).group(1)
        en_js = dict(_re.findall(r'"([^"]+)":\s*\{\s*codigoCosto:\s*"([^"]+)"', bloque))
        self.assertEqual(en_js, CODIGO_COSTO_POR_CENTRO)
        # Ya no hay cuentas que fuercen otro código de costo.
        self.assertNotIn('row.mcnccosto = "020201"', js)
        self.assertNotIn('row.mcnccosto = "0101"', js)


class TablaDinamicaResponsableYBusquedaTests(TestCase):
    """Filtro "responsable" y búsqueda general ("q") en la tabla dinámica."""

    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user("NICOLAS")
        enero = vpa._serial_excel(datetime.date(ANIO, 1, 1))
        C = Cuenta5Presupuestado.objects.create
        C(mcncuenta="513525", ctanombre="ACUEDUCTO", vinnombre="EPM", mcndetalle="agua sede",
          responsable="PILAR LOZANO", mcnfecha=enero, mcnvaldebi=100, mcnvalcred=0)
        C(mcncuenta="513525", ctanombre="ACUEDUCTO", vinnombre="EPM", mcndetalle="agua bodega",
          responsable="JUAN PEREZ", mcnfecha=enero, mcnvaldebi=50, mcnvalcred=0)
        C(mcncuenta="512010", ctanombre="ARRENDAMIENTOS", vinnombre="INMOBILIARIA", mcndetalle="local centro",
          responsable="JUAN PEREZ", mcnfecha=enero, mcnvaldebi=300, mcnvalcred=0)

    def setUp(self):
        self.client.force_login(self.user)

    def tabla(self, **params):
        r = self.client.get(reverse("obtener_tabla_dinamica_flexible"),
                            {"group_by": "ctanombre,vinnombre,mcndetalle,mcncuenta", **params})
        self.assertEqual(r.status_code, 200, r.content)
        return {d["mcndetalle"]: d["enero"] for d in r.json()["data"]}

    def test_lista_de_responsables_sale_de_cuenta5_presupuestado(self):
        r = self.client.get(reverse("obtener_valores_filtros"), {"campo": "responsable"})
        self.assertEqual(r.json()["valores"], ["JUAN PEREZ", "PILAR LOZANO"])
        # En cascada: con un filtro de cuenta, solo los responsables de esa cuenta.
        r = self.client.get(reverse("obtener_valores_filtros"), {"campo": "responsable", "mcncuenta": "512010"})
        self.assertEqual(r.json()["valores"], ["JUAN PEREZ"])

    def test_filtro_responsable(self):
        self.assertEqual(self.tabla(responsable="PILAR LOZANO"), {"agua sede": 100})
        self.assertEqual(self.tabla(responsable="JUAN PEREZ"), {"agua bodega": 50, "local centro": 300})

    def test_busqueda_general(self):
        self.assertEqual(self.tabla(q="agua"), {"agua sede": 100, "agua bodega": 50})
        self.assertEqual(self.tabla(q="arrend"), {"local centro": 300})           # nombre de cuenta
        self.assertEqual(self.tabla(q="pilar"), {"agua sede": 100})              # responsable
        self.assertEqual(self.tabla(q="512010"), {"local centro": 300})          # código de cuenta
        self.assertEqual(self.tabla(q="agua", responsable="JUAN PEREZ"), {"agua bodega": 50})
        # La búsqueda también acota las listas de los filtros.
        r = self.client.get(reverse("obtener_valores_filtros"), {"campo": "ctanombre", "q": "pilar"})
        self.assertEqual(r.json()["valores"], ["ACUEDUCTO"])

    def test_registros_del_detalle_respetan_filtros(self):
        r = self.client.get(reverse("obtener_registros_detalle"),
                            {"ctanombre": "ACUEDUCTO", "vinnombre": "EPM", "mcndetalle": "agua sede",
                             "responsable": "JUAN PEREZ"})
        self.assertEqual(r.json()["total"], 0)

    def test_redistribuir_solo_toca_lo_filtrado(self):
        r = self.client.post(reverse("redistribuir_mes"), json.dumps({
            "nivel": "cuenta", "ctanombre": "ACUEDUCTO", "mes": 1, "nuevo_total": 80,
            "filtros": {"responsable": ["JUAN PEREZ"]},
        }), content_type="application/json")
        self.assertEqual(r.status_code, 200, r.content)
        self.assertEqual(r.json()["actualizados"], 1)
        self.assertEqual(Cuenta5Presupuestado.objects.get(mcndetalle="agua bodega").mcnvaldebi, 80)
        self.assertEqual(Cuenta5Presupuestado.objects.get(mcndetalle="agua sede").mcnvaldebi, 100)

    def test_inflacion_respeta_la_busqueda(self):
        r = self.client.post(reverse("aplicar_inflacion"), json.dumps({
            "porcentaje": 10, "objetivos": [{"nivel": "cuenta", "ctanombre": "ACUEDUCTO"}],
            "filtros": {"q": "bodega"},
        }), content_type="application/json")
        self.assertEqual(r.status_code, 200, r.content)
        self.assertEqual(Cuenta5Presupuestado.objects.get(mcndetalle="agua bodega").mcnvaldebi, 55)
        self.assertEqual(Cuenta5Presupuestado.objects.get(mcndetalle="agua sede").mcnvaldebi, 100)


class QuitarCuenta5YRevisionTests(TestCase):
    """Quitar de Cuenta 5 lo subido por un área, y los controles en la pantalla de revisión."""

    @classmethod
    def setUpTestData(cls):
        cls.aprobador = User.objects.create_user("NICOLAS")
        cls.usuario_area = User.objects.create_user("PLOZANO")

    def setUp(self):
        self.client.force_login(self.aprobador)
        PresupuestoArea.objects.bulk_create(filas_verticales(
            [fila("A", 100)], area=AREA, etapa="aprobado", version=1, fecha_version=timezone.localdate()))
        # También una versión enviada, para que la pantalla de revisión tenga qué mostrar.
        PresupuestoArea.objects.bulk_create(filas_verticales(
            [fila("A", 100)], area=AREA, etapa="proyectado", version=1, fecha_version=timezone.localdate()))

    def quitar(self, area=AREA):
        return self.client.post(reverse("quitar_cuenta5_sede", args=[area]))

    def test_quita_solo_lo_del_area(self):
        Cuenta5Presupuestado.objects.create(mcncuenta="510506", mcnvaldebi=7, mcnfecha=46023)        # Excel
        Cuenta5Presupuestado.objects.create(mcncuenta="510506", mcnvaldebi=7, mcnfecha=46023,
                                            origen_area="tecnologia")                                # otra área
        self.client.post(reverse("subir_cuenta5_sede", args=[AREA]))
        self.assertEqual(vpa.estado_cuenta5(AREA)["estado"], "subido")

        r = self.quitar()
        self.assertEqual(r.status_code, 200, r.content)
        datos = r.json()
        self.assertTrue(datos["success"])
        self.assertEqual(datos["eliminados"], 12)
        self.assertEqual(datos["estado"]["estado"], "pendiente")
        self.assertFalse(Cuenta5Presupuestado.objects.filter(origen_area=AREA).exists())
        self.assertEqual(Cuenta5Presupuestado.objects.count(), 2)
        # La versión aprobada sigue ahí: se puede volver a subir.
        self.assertTrue(self.client.post(reverse("subir_cuenta5_sede", args=[AREA])).json()["success"])

    def test_sin_nada_subido(self):
        datos = self.quitar().json()
        self.assertTrue(datos["success"])
        self.assertEqual(datos["eliminados"], 0)

    def test_permisos_y_metodo(self):
        self.client.force_login(self.usuario_area)
        self.assertEqual(self.quitar().status_code, 403)
        self.client.force_login(self.aprobador)
        self.assertEqual(self.client.get(reverse("quitar_cuenta5_sede", args=[AREA])).status_code, 405)
        self.assertEqual(self.quitar("no-existe").status_code, 404)

    def test_revision_muestra_estado_y_botones(self):
        r = self.client.get(reverse("presupuesto_sede", args=[AREA]))
        self.assertEqual(r.status_code, 200)
        self.assertEqual(r.context["cuenta5"]["estado"], "pendiente")
        self.assertContains(r, 'id="estadoCuenta5"')
        self.assertContains(r, "Subir presupuesto")
        self.assertContains(r, "Quitar de Cuenta 5")
        self.assertContains(r, reverse("quitar_cuenta5_sede", args=[AREA]))


class TextosYAniosTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.admin = User.objects.create_user("admin")

    def setUp(self):
        self.client.force_login(self.admin)

    def test_tarjetas_dicen_subir_presupuesto(self):
        r = self.client.get(reverse("dashboardPresupuesto"))
        self.assertContains(r, "Subir presupuesto")
        self.assertNotContains(r, "Subir a Cuenta 5")

    def test_comparativo_usa_anio_actual_y_siguiente(self):
        r = self.client.get(reverse("comparativo_general"))
        actual = timezone.localdate().year
        self.assertContains(r, f"const ANIO_C = '-{actual % 100:02d}';")
        self.assertContains(r, f"const ANIO_P = '-{(actual + 1) % 100:02d}';")


class TextosBotonesGrillaTests(TestCase):
    def test_textos_de_la_barra_de_la_grilla(self):
        User.objects.create_user("NICOLAS")
        self.client.force_login(User.objects.get(username="NICOLAS"))
        PresupuestoArea.objects.bulk_create(filas_verticales(
            [fila("A")], area=AREA, etapa="proyectado", version=1, fecha_version=timezone.localdate()))
        r = self.client.get(reverse("presupuesto_sede", args=[AREA]))
        for texto in ("Exportar a Excel esta tabla", "Descargar plantilla vacía", "Importar archivo Excel"):
            self.assertContains(r, texto)


class EliminarConsolidadoBaseTests(TestCase):
    """Carga consolidado base: eliminar TODO lo filtrado (no solo lo visible) en la base de datos."""

    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user("admin")

    def setUp(self):
        from .models import ConsolidadoTotalBase as T
        self.T = T
        self.client.force_login(self.user)
        objs = []
        for i in range(1500):   # más de las 1.000 filas que pinta la pantalla
            objs.append(T(mcncuenta=str(510000 + i), ctanombre=f"GASTO {i}", mcnfecha=datetime.date(2025, 1, 1),
                          valor=1, sede="tulua", origen="ejecutado"))
        objs += [T(mcncuenta="610000", ctanombre="OTRA", mcnfecha=datetime.date(2025, 2, 1), valor=1,
                   sede="buga", origen="ejecutado"),
                 T(mcncuenta="710000", ctanombre="PPTO", mcnfecha=datetime.date(2026, 1, 1), valor=1,
                   sede="tulua", origen="presupuestado"),
                 T(mcncuenta="810000", ctanombre="VIEJO", mcnfecha=datetime.date(2025, 1, 1), valor=1,
                   sede="TULUA ", origen="ejecutado")]           # dato viejo con mayúsculas/espacio
        T.objects.bulk_create(objs)

    def post(self, **body):
        return self.client.post(reverse("eliminar_filtrado_consolidado_total_base"),
                                json.dumps(body), content_type="application/json")

    def test_contar_no_borra(self):
        r = self.post(accion="contar", filtros={"sede": ["tulua"], "origen": ["ejecutado"]})
        self.assertEqual(r.json()["total"], 1500)
        self.assertEqual(self.T.objects.count(), 1503)

    def test_elimina_todo_lo_filtrado_no_solo_1000(self):
        f = {"sede": ["tulua"], "origen": ["ejecutado"]}
        r = self.post(accion="eliminar", filtros=f, esperado=1500)
        self.assertEqual(r.status_code, 200, r.content)
        self.assertEqual(r.json()["eliminados"], 1500)
        self.assertEqual(sorted(self.T.objects.values_list("ctanombre", flat=True)), ["OTRA", "PPTO", "VIEJO"])

    def test_busqueda_y_fecha(self):
        self.assertEqual(self.post(accion="contar", filtros={"q": "gasto 14"}).json()["total"], 111)  # 14, 140-149, 1400-1499
        self.assertEqual(self.post(accion="contar", filtros={"q": "510000 gasto 0"}).json()["total"], 1)  # "cuenta nombre"
        self.assertEqual(self.post(accion="contar", filtros={"mcnfecha": ["2025-02-01"]}).json()["total"], 1)

    def test_espacios_en_lo_guardado_y_lista_vacia(self):
        # La pantalla muestra "TULUA" (sin espacio): también se encuentra el guardado "TULUA ".
        self.assertEqual(self.post(accion="contar", filtros={"sede": ["TULUA"]}).json()["total"], 1)
        # Filtro activo con "ninguno" marcado: no coincide nada (no borra todo).
        self.assertEqual(self.post(accion="contar", filtros={"sede": []}).json()["total"], 0)

    def test_si_cambiaron_los_datos_no_borra(self):
        r = self.post(accion="eliminar", filtros={"sede": ["buga"]}, esperado=5)
        self.assertEqual(r.status_code, 409)
        self.assertEqual(self.T.objects.count(), 1503)
        self.assertEqual(self.post(accion="eliminar", filtros={"sede": ["buga"]}).status_code, 400)  # sin "esperado"

    def test_por_ids(self):
        ids = list(self.T.objects.filter(sede="buga").values_list("pk", flat=True))
        self.assertEqual(self.post(accion="eliminar", filtros={"ids": ids}, esperado=1).json()["eliminados"], 1)
        self.assertFalse(self.T.objects.filter(sede="buga").exists())

    def test_requiere_sesion(self):
        self.client.logout()
        self.assertEqual(self.post(accion="contar", filtros={}).status_code, 302)

    def test_borrar_todo_por_sede_tolera_mayusculas(self):
        r = self.client.post(reverse("borrar_consolidado_total_base"),
                             json.dumps({"sede": "tulua", "origen": "ejecutado"}), content_type="application/json")
        self.assertEqual(r.json()["eliminados"], 1501)       # 1500 + "TULUA "
        self.assertEqual(self.T.objects.count(), 2)


class PresupuestoVentasRepartoTests(TestCase):
    """Ventas a crédito / contado / descuentos = proyección del mes × participación (sin el "1 +")."""

    # Ejecutado Tuluá, enero (pantalla Ejecutado) y proyección del centro (Proyección por centro de operación)
    CREDITO, CONTADO, DESCUENTO = 759_222_744, 479_318_539, -6_508_501
    PROYECCION = 1_238_511_267

    def participacion(self):
        netas = self.CREDITO + self.CONTADO + self.DESCUENTO
        return {"1": self.CREDITO / netas, "2": self.CONTADO / netas, "41750201": self.DESCUENTO / netas}

    def test_reparto_tulua_enero(self):
        v = views.repartir_proyeccion(self.PROYECCION, self.participacion())
        # 1.238.511.267 × 61,6236 % = 763.215.018,6. Redondeadas por separado, las tres
        # cuentas suman $1 más que la proyección; ese $1 se le quita a crédito (la de mayor peso).
        self.assertEqual(v["1"], 763_215_018)
        self.assertEqual(v["2"], 481_838_974)          # × 38,9047 %
        self.assertEqual(v["41750201"], -6_542_725)    # × -0,5283 %
        self.assertEqual(sum(v.values()), self.PROYECCION)   # suma exacta (sin $1 de redondeo)

    def test_genera_y_guarda_en_consolidado_total_base(self):
        from .models import ConsolidadoTotalBase as T
        anio_base = timezone.now().year
        for cta, nombre, valor in (("1", "Ventas a crédito", self.CREDITO),
                                   ("2", "Ventas a contado", self.CONTADO),
                                   ("41750201", "Descuentos otorgados x pto pago", self.DESCUENTO)):
            T.objects.create(mcncuenta=cta, ctanombre=nombre, mcnfecha=datetime.date(anio_base, 1, 1),
                             valor=valor, sede="tulua", origen="ejecutado")
        proyeccion = {"ALMACEN TULUA": {m: self.PROYECCION for m in range(1, 13)}}
        with mock.patch.object(views, "_proyeccion_ventas_por_centro", return_value=proyeccion):
            r = views.generar_presupuesto_ventas()
        self.assertEqual(r["sedes_procesadas"], ["tulua"])

        enero = datetime.date(anio_base + 1, 1, 1)
        ppto = dict(T.objects.filter(origen="presupuestado", sede="tulua", mcnfecha=enero)
                    .values_list("mcncuenta", "valor"))
        self.assertEqual(ppto, {"1": 763_215_018, "2": 481_838_974, "41750201": -6_542_725})
        # Ventas netas presupuestadas = proyección (antes daba ~3 veces: 3.715.533.802).
        self.assertEqual(sum(ppto.values()), self.PROYECCION)

        # Volver a generar reemplaza (no duplica).
        with mock.patch.object(views, "_proyeccion_ventas_por_centro", return_value=proyeccion):
            views.generar_presupuesto_ventas()
        self.assertEqual(T.objects.filter(origen="presupuestado", sede="tulua").count(), 36)


class GuardadoDuranteDespliegueTests(TestCase):
    """Si la base de datos no responde (p. ej. durante un despliegue) se responde 503 = "reintenta"."""

    @classmethod
    def setUpTestData(cls):
        cls.aprobador = User.objects.create_user("NICOLAS")

    def setUp(self):
        self.client.force_login(self.aprobador)

    def test_error_de_base_de_datos_responde_503(self):
        from django.db import OperationalError
        with mock.patch.object(vpa.PresupuestoArea.objects, "bulk_create", side_effect=OperationalError("server closed")):
            r = self.client.post(reverse("guardar_temp_sede", args=[AREA]), json.dumps([fila("A")]),
                                 content_type="application/json")
        self.assertEqual(r.status_code, 503)
        self.assertTrue(r.json()["reintentar"])

    def test_datos_invalidos_siguen_siendo_400(self):
        r = self.client.post(reverse("guardar_temp_sede", args=[AREA]), "no es json",
                             content_type="application/json")
        self.assertEqual(r.status_code, 400)

    def test_reintentar_el_mismo_guardado_no_duplica(self):
        url = reverse("guardar_temp_sede", args=[AREA])
        for _ in range(3):   # la respuesta "se perdió" y el navegador reenvía
            self.assertEqual(self.client.post(url, json.dumps([fila("A"), fila("B")]),
                                              content_type="application/json").status_code, 200)
        self.assertEqual(PresupuestoArea.objects.filter(area=AREA, etapa="auxiliar").count(), 24)

    def test_pantallas_cargan_envio_seguro_antes_que_la_grilla(self):
        PresupuestoArea.objects.bulk_create(filas_verticales(
            [fila("A")], area=AREA, etapa="proyectado", version=1, fecha_version=timezone.localdate()))
        html = self.client.get(reverse("presupuesto_sede", args=[AREA])).content.decode()
        self.assertLess(html.index("js/envio_seguro.js"), html.index("js/grilla_presupuesto.js"))
        self.assertIn('usuario: "NICOLAS"', html)


class PresupuestoComercialGuardadoTests(TestCase):
    """Autoguardado del presupuesto comercial: rápido, solo lo que cambió, seguro de repetir."""

    @classmethod
    def setUpTestData(cls):
        cls.user = User.objects.create_user("admin")

    def setUp(self):
        from .models import PresupuestoComercial
        self.PC = PresupuestoComercial
        self.anio = timezone.now().year
        self.client.force_login(self.user)

    def fila(self, linea, crec, centro="ALMACEN BUGA", clase="CLIENTES", year=None):
        return {"linea": linea, "year": year or self.anio, "nombre_centro_de_operacion": centro,
                "nombre_clase_cliente": clase, "crecimiento_ventas": crec}

    def guardar(self, filas):
        return self.client.post(reverse("guardar_presupuesto_comercial"), json.dumps(filas),
                                content_type="application/json")

    def test_cuenta_solo_cambios_reales_y_es_idempotente(self):
        r = self.guardar([self.fila("L1", 5), self.fila("L2", 0)])
        self.assertEqual(r.json()["cambios"], 2)                 # dos filas nuevas
        r = self.guardar([self.fila("L1", 5), self.fila("L2", 3)])
        self.assertEqual(r.json()["cambios"], 1)                 # solo L2 cambió
        r = self.guardar([self.fila("L1", 5), self.fila("L2", 3)])   # reintento del mismo envío
        self.assertEqual(r.json()["cambios"], 0)
        self.assertEqual(self.PC.objects.filter(year=self.anio).count(), 2)
        self.assertEqual(self.PC.objects.get(linea="L2").crecimiento_ventas, 3)

    def test_ignora_otros_anios(self):
        r = self.guardar([self.fila("L1", 9, year=self.anio - 1)])
        self.assertEqual(r.json()["cambios"], 0)
        self.assertFalse(self.PC.objects.exists())

    def test_muchas_filas_con_pocas_consultas(self):
        from django.db import connection
        from django.test.utils import CaptureQueriesContext
        filas = [self.fila(f"L{i}", i % 7) for i in range(3000)]
        self.guardar(filas)
        filas = [self.fila(f"L{i}", (i % 7) + 1) for i in range(3000)]
        with CaptureQueriesContext(connection) as q:
            r = self.guardar(filas)
        self.assertEqual(r.json()["cambios"], 3000)
        self.assertLess(len(q), 40)          # antes: 2 consultas por fila (6.000)

    def test_error_de_base_de_datos_responde_503(self):
        from django.db import OperationalError
        with mock.patch.object(self.PC.objects, "bulk_create", side_effect=OperationalError("caida")):
            r = self.guardar([self.fila("L1", 5)])
        self.assertEqual(r.status_code, 503)

    def test_datos_invalidos_400(self):
        self.assertEqual(self.guardar({"no": "lista"}).status_code, 400)

    def test_presupuestado_general_ya_no_genera_ventas_al_entrar(self):
        html = self.client.get(reverse("presupuestado_general")).content.decode()
        self.assertNotIn(reverse("generar_presupuesto_ventas"), html)

    def test_pantalla_comercial_usa_envio_seguro_y_genera_ventas(self):
        html = self.client.get(reverse("presupuestoComercial")).content.decode()
        self.assertIn("js/envio_seguro.js", html)
        self.assertIn(reverse("generar_presupuesto_ventas"), html)
        self.assertIn('name="csrf-token"', html)


class CerrarSesionComercialTests(TestCase):
    def test_pantallas_comerciales_tienen_cerrar_sesion(self):
        User.objects.create_user("admin", first_name="Ana")
        self.client.force_login(User.objects.get(username="admin"))
        for nombre in ("presupuestoComercial", "vistaComparativoAnual"):
            r = self.client.get(reverse(nombre))
            self.assertContains(r, "Cerrar sesión")
            self.assertContains(r, f'action="{reverse("logout")}"')
            self.assertContains(r, "Hola, Ana")


class DobleVersionAlSubirTests(TestCase):
    """Al subir se crean 2 copias: lo que envió el área (auditoría) y la versión de trabajo del revisor."""

    @classmethod
    def setUpTestData(cls):
        cls.usuario_area = User.objects.create_user("PLOZANO", password="x")
        cls.aprobador = User.objects.create_user("NICOLAS", password="x")
        cls.intruso = User.objects.create_user("OTRO", password="x")
        asignar(cls.usuario_area, AREA)
        abrir_plazo()

    def post_json(self, url, datos):
        return self.client.post(url, json.dumps(datos), content_type="application/json")

    def subir(self, filas):
        self.client.force_login(self.usuario_area)
        self.post_json(reverse("guardar_temp_sede", args=[AREA]), filas)
        r = self.client.post(reverse("subir_presupuesto_sede", args=[AREA]))
        self.assertTrue(r.json()["success"], r.content)
        return r.json()["version"]

    def enviado(self, version):
        return self.client.get(reverse("obtener_presupuesto_preaprobado_sede", args=[AREA, version])).json()["data"]

    def test_subir_crea_dos_copias_iguales(self):
        v = self.subir([fila("A", 5), fila("B", 6)])
        self.assertEqual(v, 1)
        pre = PresupuestoArea.objects.de(AREA, "preaprobado").filter(version=1)
        pro = PresupuestoArea.objects.de(AREA, "proyectado").filter(version=1)
        self.assertEqual(pre.count(), 24)
        self.assertEqual(pro.count(), 24)
        campos = ("linea", "fecha", "valor", "mcndetalle", "mcncuenta", "mcnccosto")
        self.assertEqual(sorted(pre.values_list(*campos)), sorted(pro.values_list(*campos)))
        self.assertEqual(self.subir([fila("C", 1)]), 2)       # la numeración sigue

    def test_el_revisor_edita_y_aprueba_sin_tocar_lo_enviado(self):
        self.subir([fila("A", 5), fila("B", 6)])
        self.client.force_login(self.aprobador)
        datos = self.client.get(reverse("obtener_presupuesto_sede", args=[AREA]) + "?version=1").json()["data"]
        datos[0]["enero"] = 999_999
        datos = datos[:1]                                      # y borra la fila B
        self.assertEqual(self.post_json(reverse("guardar_version_sede", args=[AREA, 1]), datos).json()["status"], "ok")
        self.assertTrue(self.client.post(reverse("aprobar_version_sede", args=[AREA, 1])).json()["success"])

        enviado = self.enviado(1)                              # auditoría intacta
        self.assertEqual([f["mcndetalle"] for f in enviado], ["A", "B"])
        self.assertEqual(enviado[0]["enero"], fila("A", 5)["enero"])
        aprobado = self.client.get(reverse("obtener_presupuesto_aprobado_sede", args=[AREA])).json()["data"]
        self.assertEqual([(f["mcndetalle"], f["enero"]) for f in aprobado], [("A", 999_999)])

        r = self.client.get(reverse("presupuesto_sede", args=[AREA]))
        v1 = r.context["versiones"][0]
        self.assertTrue(v1["con_copia"])
        self.assertEqual(v1["total_enviado"], total_de(fila("A", 5)) + total_de(fila("B", 6)))
        self.assertContains(r, reverse("presupuesto_preaprobado_sede", args=[AREA, 999999]))

    def test_borrar_version_borra_las_tres_copias(self):
        self.subir([fila("A", 5)])
        self.client.force_login(self.aprobador)
        self.client.post(reverse("aprobar_version_sede", args=[AREA, 1]))
        r = self.post_json(reverse("borrar_presupuesto_sede", args=[AREA]), {"version": 1})
        self.assertEqual(r.json()["status"], "ok")
        self.assertFalse(PresupuestoArea.objects.filter(area=AREA, version=1).exists())

    def test_vista_de_auditoria(self):
        self.subir([fila("A", 5)])
        self.client.force_login(self.aprobador)
        r = self.client.get(reverse("presupuesto_preaprobado_sede", args=[AREA, 1]))
        self.assertContains(r, "lo que envió el área (v1)")
        self.assertContains(r, reverse("obtener_presupuesto_preaprobado_sede", args=[AREA, 1]))
        self.client.force_login(self.intruso)
        self.assertEqual(self.client.get(reverse("presupuesto_preaprobado_sede", args=[AREA, 1])).status_code, 403)
        self.assertEqual(self.client.get(reverse("obtener_presupuesto_preaprobado_sede", args=[AREA, 1])).status_code, 403)

    def test_version_antigua_sin_copia(self):
        # Versiones subidas antes del cambio: solo existe la proyectada.
        PresupuestoArea.objects.bulk_create(filas_verticales(
            [fila("A")], area=AREA, etapa="proyectado", version=1, fecha_version=timezone.localdate()))
        self.client.force_login(self.aprobador)
        r = self.client.get(reverse("presupuesto_sede", args=[AREA]))
        self.assertFalse(r.context["versiones"][0]["con_copia"])
        r = self.client.get(reverse("presupuesto_preaprobado_sede", args=[AREA, 1]))
        self.assertContains(r, "no tiene copia de lo que envió el área")

    def test_la_copia_no_entra_en_cuenta5_ni_en_consolidados(self):
        self.subir([fila("A", 5)])
        self.client.force_login(self.aprobador)
        self.client.post(reverse("aprobar_version_sede", args=[AREA, 1]))
        self.client.post(reverse("subir_cuenta5_sede", args=[AREA]))
        self.assertEqual(Cuenta5Presupuestado.objects.filter(origen_area=AREA).count(), 12)


class ActualizarBorradorDelAreaTests(TestCase):
    """El revisor pasa su tabla (preaprobado/trabajo o aprobado) al borrador del área, sin que el área la pise."""

    @classmethod
    def setUpTestData(cls):
        cls.usuario_area = User.objects.create_user("PLOZANO", password="x")
        cls.aprobador = User.objects.create_user("NICOLAS", password="x")
        asignar(cls.usuario_area, AREA)
        abrir_plazo()

    def post_json(self, url, datos, **extra):
        return self.client.post(url, json.dumps(datos), content_type="application/json", **extra)

    def preparar(self):
        """El área sube A=5, B=6; el revisor deja solo A con enero=777."""
        self.client.force_login(self.usuario_area)
        self.post_json(reverse("guardar_temp_sede", args=[AREA]), [fila("A", 5), fila("B", 6)])
        self.client.post(reverse("subir_presupuesto_sede", args=[AREA]))
        self.client.force_login(self.aprobador)
        datos = self.client.get(reverse("obtener_presupuesto_sede", args=[AREA]) + "?version=1").json()["data"]
        datos[0]["enero"] = 777
        self.post_json(reverse("guardar_version_sede", args=[AREA, 1]), datos[:1])

    def borrador(self):
        return self.client.get(reverse("obtener_temp_sede", args=[AREA])).json()

    def test_pasa_la_version_de_trabajo_al_borrador(self):
        self.preparar()
        r = self.post_json(reverse("actualizar_borrador_sede", args=[AREA]), {"origen": "trabajo", "version": 1})
        self.assertTrue(r.json()["success"], r.content)
        b = self.borrador()
        self.assertEqual([(f["mcndetalle"], f["enero"]) for f in b], [("A", 777)])
        # Lo que envió el área (auditoría) no cambia.
        self.assertEqual(len(PresupuestoArea.objects.de(AREA, "preaprobado").values("linea").distinct()), 2)

    def test_pasa_el_aprobado(self):
        self.preparar()
        r = self.post_json(reverse("actualizar_borrador_sede", args=[AREA]), {"origen": "aprobado"})
        self.assertEqual(r.status_code, 400)                      # aún no hay aprobado
        self.client.post(reverse("aprobar_version_sede", args=[AREA, 1]))
        r = self.post_json(reverse("actualizar_borrador_sede", args=[AREA]), {"origen": "aprobado"})
        self.assertTrue(r.json()["success"])
        self.assertEqual([f["enero"] for f in self.borrador()], [777])

    def test_solo_el_revisor(self):
        self.preparar()
        self.client.force_login(self.usuario_area)
        r = self.post_json(reverse("actualizar_borrador_sede", args=[AREA]), {"origen": "trabajo", "version": 1})
        self.assertEqual(r.status_code, 403)

    def test_el_area_no_pisa_la_tabla_del_revisor(self):
        self.client.force_login(self.usuario_area)
        self.post_json(reverse("guardar_temp_sede", args=[AREA]), [fila("A", 5), fila("B", 6)])
        token = self.client.get(reverse("obtener_temp_sede", args=[AREA]) + "?con_token=1").json()["token"]
        self.client.post(reverse("subir_presupuesto_sede", args=[AREA]))

        # Con su token vigente, el área guarda normal y recibe uno nuevo.
        r = self.post_json(reverse("guardar_temp_sede", args=[AREA]), [fila("A", 5)], HTTP_X_BORRADOR_TOKEN=str(token))
        self.assertEqual(r.status_code, 200)
        token = r.json()["token"]

        # Reintento del MISMO guardado con el token viejo: no es conflicto.
        r2 = self.post_json(reverse("guardar_temp_sede", args=[AREA]), [fila("A", 5)], HTTP_X_BORRADOR_TOKEN="1")
        self.assertEqual(r2.status_code, 200, r2.content)

        # El revisor reemplaza el borrador…
        self.client.force_login(self.aprobador)
        self.post_json(reverse("actualizar_borrador_sede", args=[AREA]), {"origen": "trabajo", "version": 1})
        # …y el área, con su pantalla vieja, intenta guardar: se rechaza (409) sin tocar nada.
        self.client.force_login(self.usuario_area)
        r = self.post_json(reverse("guardar_temp_sede", args=[AREA]), [fila("X", 1)], HTTP_X_BORRADOR_TOKEN=str(token))
        self.assertEqual(r.status_code, 409)
        self.assertTrue(r.json()["conflicto"])
        self.assertEqual([f["mcndetalle"] for f in self.borrador()], ["A", "B"])
        # Sin token (pantallas viejas) se guarda como antes.
        self.assertEqual(self.post_json(reverse("guardar_temp_sede", args=[AREA]), [fila("Y", 1)]).status_code, 200)

    def test_revision_muestra_boton_y_busqueda(self):
        self.preparar()
        r = self.client.get(reverse("presupuesto_sede", args=[AREA]))
        self.assertContains(r, "Actualizar preaprobado o aprobado")
        self.assertContains(r, 'id="busquedaGrilla"')
        self.assertEqual(r.context["borrador_filas"], 2)


class NominaAutoguardadoTests(TestCase):
    """El autoguardado de las tablas de nómina reenvía la tabla completa.

    - Las filas nuevas llevan `_uid`; el servidor devuelve {_uid: id}.
    - Si un envío sí se guardó pero la respuesta se perdió, el reintento
      (mismo contenido, fila nueva aún sin id) NO crea un duplicado.
    """

    def setUp(self):
        self.client.force_login(User.objects.create_user("admin"))
        self.existente = linea_nomina(origen="manual")
        self.existente.save()

    def enviar(self, filas):
        r = self.client.post(reverse("nomina_guardar", args=["sueldos"]), json.dumps({"filas": filas}),
                             content_type="application/json")
        self.assertEqual(r.status_code, 200, r.content)
        return r.json()

    def tabla(self):
        return self.client.get(reverse("nomina_datos", args=["sueldos"])).json()["data"]

    def nueva(self, **kw):
        fila = {"_uid": "u-1", "cedula": "2002", "nombre": "PEDRO GIL", "centro": "ALMACEN BUGA",
                "area": "VENTAS", "cargo": "CAJERO", "concepto": "SUELDO", **{m: 500 for m in MESES_N}}
        fila.update(kw)
        return fila

    def test_devuelve_el_id_de_cada_fila_nueva(self):
        r = self.enviar(self.tabla() + [self.nueva()])
        self.assertIn("u-1", r["nuevos"])
        self.assertTrue(PresupuestoNomina.objects.filter(pk=r["nuevos"]["u-1"], nombre="PEDRO GIL").exists())

    def test_reintento_con_respuesta_perdida_no_duplica(self):
        envio = self.tabla() + [self.nueva()]
        primero = self.enviar(envio)
        segundo = self.enviar(envio)              # el mismo envío otra vez (la fila nueva sigue sin id)
        self.assertEqual(PresupuestoNomina.objects.filter(tipo="sueldos", nombre="PEDRO GIL").count(), 1)
        self.assertEqual(segundo["nuevos"]["u-1"], primero["nuevos"]["u-1"])
        self.assertEqual(segundo["resumen"].get("reutilizadas"), 1)

    def test_fila_nueva_igual_a_una_existente_mencionada_si_se_crea(self):
        # Duplicar a propósito una fila que sigue en la tabla: son dos filas.
        tabla = self.tabla()
        copia = {k: v for k, v in tabla[0].items() if k not in ("id", "clave")}
        self.enviar(tabla + [dict(copia, _uid="u-2")])
        self.assertEqual(PresupuestoNomina.objects.filter(tipo="sueldos", nombre="ANA PEREZ").count(), 2)

    def test_lo_que_no_llega_se_borra(self):
        self.enviar([])
        self.assertFalse(PresupuestoNomina.objects.filter(tipo="sueldos").exists())

    def test_base_de_datos_caida_responde_503(self):
        from django.db import OperationalError
        with mock.patch.object(nomina_motor, "guardar", side_effect=OperationalError("sin conexión")):
            r = self.client.post(reverse("nomina_guardar", args=["sueldos"]), json.dumps({"filas": []}),
                                 content_type="application/json")
        self.assertEqual(r.status_code, 503)

    def test_pantalla_sin_boton_guardar_y_con_autoguardado(self):
        html = self.client.get(reverse("nomina_tabla", args=["sueldos"])).content.decode()
        self.assertNotIn('data-rol="guardar"', html)
        self.assertIn('data-rol="estado"', html)
        self.assertIn('"usuario": "admin"', html)

    def test_tablero_boton_parametros_en_su_panel(self):
        html = self.client.get(reverse("presupuestoNomina")).content.decode()
        barra = html.split('<div class="pt-barra">')[1].split("</div>")[0]
        self.assertNotIn("btnActualizar", barra)
        panel = html.split("Parámetros del presupuesto")[1].split("Resumen consolidado")[0]
        self.assertIn('id="btnActualizar"', panel)


class SueldoMinimoProyectadoTests(TestCase):
    """Sueldos con mínimo 1.423.500 e incremento 7 % (mínimo proyectado 1.523.145)."""

    def setUp(self):
        self.p = nomina_motor.Parametros(incremento_salarial=7, salario_minimo=1423500)
        self.c = nomina_motor.CONCEPTOS["sueldos"]
        self.minimo_proy = 1423500 * 1.07                     # 1.523.145

    def meses(self, base):
        return nomina_motor.f_retroactivo(linea_nomina(base=base), self.c, self.p)

    def test_quien_gana_el_minimo_toma_el_minimo_proyectado_todo_el_anio(self):
        self.assertEqual(set(self.meses(1423500).values()), {self.minimo_proy})

    def test_un_poco_mas_del_minimo(self):
        # ene-feb: mínimo proyectado · desde marzo: salario + 7 % con retroactivo sobre lo pagado
        meses = self.meses(1500000)
        nuevo = 1500000 * 1.07                                # 1.605.000
        self.assertEqual(meses["enero"], self.minimo_proy)
        self.assertEqual(meses["febrero"], self.minimo_proy)
        self.assertAlmostEqual(meses["marzo"], nuevo + 2 * (nuevo - self.minimo_proy))   # 1.768.710
        self.assertAlmostEqual(meses["abril"], nuevo)
        self.assertAlmostEqual(meses["diciembre"], nuevo)

    def test_por_encima_del_minimo_proyectado(self):
        meses = self.meses(2000000)
        self.assertEqual(meses["enero"], 2000000)
        self.assertEqual(meses["febrero"], 2000000)
        self.assertAlmostEqual(meses["abril"], 2140000)
        self.assertAlmostEqual(meses["marzo"], 2140000 + 2 * 140000)


class NominaCorreccionPersonaTests(TestCase):
    """Cédula / nombre corregidos en un concepto base llegan a TODOS los conceptos
    (aunque no dependan de él, como medios de transporte) y se respetan al
    volver a cargar desde Conceptos."""

    def setUp(self):
        anio = timezone.localdate().year
        comunes = dict(anio=anio, archivo="prueba", nombre_cen="ALMACEN TULUA", nomcosto="VENTAS",
                       nombrecar="ASESOR", cuenta="520506")
        for cedula, nombre in [(111, "ANA MAL ESCRITA"), (222, "LUIS PEREZ")]:
            meses = {m: 1500000 for m in MESES_N[:8]}
            ConceptosNomina.objects.create(concepto="001", cedula=cedula, nombre=nombre,
                                           concepto_f=1500000, **comunes, **meses)
            ConceptosNomina.objects.create(concepto="011", cedula=cedula, nombre=nombre,
                                           concepto_f=100000, **comunes, **{m: 100000 for m in MESES_N[:8]})
            ConceptosNomina.objects.create(concepto="389", cedula=cedula, nombre=nombre,
                                           **comunes, **{m: 300000 for m in MESES_N[:8]})
        nomina_motor.recargar_bases()
        self.client.force_login(User.objects.create_user("admin"))

    def personas(self, tipo):
        return sorted(PresupuestoNomina.objects.filter(tipo=tipo).values_list("cedula", "nombre").distinct())

    def editar_sueldo(self, de, **cambios):
        filas = self.client.get(reverse("nomina_datos", args=["sueldos"])).json()["data"]
        for f in filas:
            if f["cedula"] == de:
                f.update(cambios)
        r = self.client.post(reverse("nomina_guardar", args=["sueldos"]), json.dumps({"filas": filas}),
                             content_type="application/json")
        self.assertEqual(r.status_code, 200, r.content)
        return r.json()

    def test_editar_en_sueldos_corrige_todos_los_conceptos(self):
        r = self.editar_sueldo("111", cedula="999", nombre="ANA BIEN ESCRITA")
        self.assertIn("todos los conceptos", r["aviso"])
        esperado = [("222", "LUIS PEREZ"), ("999", "ANA BIEN ESCRITA")]
        for tipo in ("sueldos", "medios_transporte", "comisiones", "cesantias", "prima"):
            self.assertEqual(self.personas(tipo), esperado, tipo)
        self.assertFalse(PresupuestoNomina.objects.filter(cedula="111").exists())

    def test_la_correccion_se_respeta_al_recargar_desde_conceptos(self):
        self.editar_sueldo("111", cedula="999", nombre="ANA BIEN ESCRITA")
        nomina_motor.recargar_bases()
        for tipo in ("sueldos", "medios_transporte", "comisiones"):
            self.assertEqual(self.personas(tipo), [("222", "LUIS PEREZ"), ("999", "ANA BIEN ESCRITA")], tipo)
        # las comisiones reales (bonificación foco) también se buscan con la cédula corregida
        self.assertIn("999", nomina_motor.comisiones_reales(nomina_motor.Contexto()))

    def test_solo_nombre(self):
        self.editar_sueldo("111", nombre="ANA BIEN ESCRITA")
        self.assertEqual(self.personas("medios_transporte"), [("111", "ANA BIEN ESCRITA"), ("222", "LUIS PEREZ")])

    def test_cedula_de_otra_persona_no_se_propaga(self):
        r = self.editar_sueldo("111", cedula="222")
        self.assertIn("ya es de otra persona", r["aviso"])
        self.assertIn(("111", "ANA MAL ESCRITA"), self.personas("medios_transporte"))

    def test_herramienta_del_tablero_para_un_cambio_ya_hecho(self):
        # Caso real: en Sueldos ya se había cambiado la cédula antes de existir la propagación.
        PresupuestoNomina.objects.filter(tipo="sueldos", cedula="111").update(cedula="999", nombre="ANA BIEN")
        r = self.client.post(reverse("presupuestoNomina"),
                             {"action": "corregir_persona", "cedula_actual": "111", "cedula_nueva": "999",
                              "nombre_nuevo": "ana bien"}, HTTP_X_REQUESTED_WITH="XMLHttpRequest")
        self.assertEqual(r.json()["status"], "ok", r.content)
        self.assertEqual(self.personas("medios_transporte"), [("222", "LUIS PEREZ"), ("999", "ANA BIEN")])
        self.assertTrue(CorreccionPersonaNomina.objects.filter(cedula_origen="111", cedula="999").exists())
        html = self.client.get(reverse("presupuestoNomina")).content.decode()
        self.assertIn("Correcciones que se aplican al cargar desde Conceptos", html)

    def test_volver_a_la_original_quita_la_correccion(self):
        self.editar_sueldo("111", cedula="999")
        self.editar_sueldo("999", cedula="111")
        self.assertFalse(CorreccionPersonaNomina.objects.exists())


class NominaDeshacerEliminarTests(TestCase):
    """Deshacer la eliminación de una fila calculada la devuelve calculada
    (con su clave y su histórico), no como fila manual."""

    def setUp(self):
        self.client.force_login(User.objects.create_user("admin"))
        self.fila = linea_nomina(origen="sistema", clave="1001#0", base=1000, historico={"enero": 1000})
        # sus meses son los calculados (como cualquier fila calculada)
        nomina_motor.aplicar_formula(self.fila, nomina_motor.CONCEPTOS["sueldos"], nomina_motor.Parametros.cargar())
        self.fila.save()

    def enviar(self, filas):
        r = self.client.post(reverse("nomina_guardar", args=["sueldos"]), json.dumps({"filas": filas}),
                             content_type="application/json")
        self.assertEqual(r.status_code, 200, r.content)
        return r.json()

    def test_fila_restaurada_vuelve_calculada(self):
        datos = self.client.get(reverse("nomina_datos", args=["sueldos"])).json()["data"]
        self.enviar([])                                            # se eliminó por error
        restaurada = dict(datos[0], id=None, _uid="u-r", _restaurada=True)
        r = self.enviar([restaurada])                              # Deshacer
        nueva = PresupuestoNomina.objects.get(pk=r["nuevos"]["u-r"])
        self.assertEqual((nueva.origen, nueva.clave, nueva.historico), ("sistema", "1001#0", {"enero": 1000}))

    def test_sin_marca_una_fila_nueva_sigue_siendo_manual(self):
        datos = self.client.get(reverse("nomina_datos", args=["sueldos"])).json()["data"]
        r = self.enviar(datos + [dict(datos[0], id=None, _uid="u-n", nombre="OTRA")])
        self.assertEqual(PresupuestoNomina.objects.get(pk=r["nuevos"]["u-n"]).origen, "manual")


class NominaTextoEditadoManualTests(TestCase):
    """Cambiar a mano la cédula, el nombre u otro texto de una fila calculada la
    vuelve MANUAL, y al recargar desde Conceptos no se pierde ni se duplica."""

    def setUp(self):
        anio = timezone.localdate().year
        comunes = dict(anio=anio, archivo="prueba", nombre_cen="ALMACEN TULUA", nomcosto="VENTAS",
                       nombrecar="ASESOR", cuenta="520506", concepto="001", concepto_f=2000000,
                       **{m: 2000000 for m in MESES_N[:8]})
        ConceptosNomina.objects.create(cedula=10, nombre="VACANTE", **comunes)
        ConceptosNomina.objects.create(cedula=20, nombre="LUIS PEREZ", **comunes)
        nomina_motor.recargar_bases()
        self.client.force_login(User.objects.create_user("admin"))

    def guardar_con(self, de, **cambios):
        filas = self.client.get(reverse("nomina_datos", args=["sueldos"])).json()["data"]
        for f in filas:
            if f["cedula"] == de:
                f.update(cambios)
        r = self.client.post(reverse("nomina_guardar", args=["sueldos"]), json.dumps({"filas": filas}),
                             content_type="application/json")
        self.assertEqual(r.status_code, 200, r.content)

    def sueldos(self):
        return sorted(PresupuestoNomina.objects.filter(tipo="sueldos").values_list("cedula", "nombre", "origen"))

    def test_cambiar_nombre_la_vuelve_manual_y_se_conserva_al_recargar(self):
        self.guardar_con("10", nombre="VACANTE - REEMPLAZO OSWALDO CAMPO")
        esperado = [("10", "VACANTE - REEMPLAZO OSWALDO CAMPO", "manual"), ("20", "LUIS PEREZ", "sistema")]
        self.assertEqual(self.sueldos(), esperado)
        nomina_motor.recargar_bases()
        self.assertEqual(self.sueldos(), esperado)

    def test_cambiar_cedula_la_vuelve_manual_sin_duplicar_al_recargar(self):
        self.guardar_con("10", cedula="14")
        self.assertEqual(self.sueldos(), [("14", "VACANTE", "manual"), ("20", "LUIS PEREZ", "sistema")])
        nomina_motor.recargar_bases()
        self.assertEqual(self.sueldos(), [("14", "VACANTE", "manual"), ("20", "LUIS PEREZ", "sistema")])

    def test_cambiar_cargo_tambien_la_vuelve_manual(self):
        self.guardar_con("20", cargo="CAJERO")
        self.assertIn(("20", "LUIS PEREZ", "manual"), self.sueldos())

    def test_sin_cambios_sigue_calculada(self):
        self.guardar_con("20")
        self.assertIn(("20", "LUIS PEREZ", "sistema"), self.sueldos())

    def test_filas_editadas_antes_de_esta_version_no_se_pierden_al_recargar(self):
        # Antes, cambiar el nombre dejaba la fila "calculada"; recargar la reemplazaba.
        PresupuestoNomina.objects.filter(tipo="sueldos", cedula="10").update(nombre="VACANTE - SANCHEZ DAVID")
        nomina_motor.recargar_bases()
        self.assertEqual(self.sueldos(), [("10", "VACANTE - SANCHEZ DAVID", "manual"), ("20", "LUIS PEREZ", "sistema")])


class NominaFilaEliminadaTests(TestCase):
    """Una fila de Conceptos eliminada en pantalla no vuelve al recargar."""

    def setUp(self):
        anio = timezone.localdate().year
        comunes = dict(anio=anio, archivo="prueba", nombre_cen="ALMACEN TULUA", nomcosto="VENTAS",
                       nombrecar="ASESOR", cuenta="520506", concepto="001", concepto_f=2000000,
                       **{m: 2000000 for m in MESES_N[:8]})
        ConceptosNomina.objects.create(cedula=10, nombre="VACANTE", **comunes)
        ConceptosNomina.objects.create(cedula=20, nombre="LUIS PEREZ", **comunes)
        nomina_motor.recargar_bases()
        self.client.force_login(User.objects.create_user("admin"))

    def datos(self):
        return self.client.get(reverse("nomina_datos", args=["sueldos"])).json()["data"]

    def enviar(self, filas):
        r = self.client.post(reverse("nomina_guardar", args=["sueldos"]), json.dumps({"filas": filas}),
                             content_type="application/json")
        self.assertEqual(r.status_code, 200, r.content)
        return r.json()

    def cedulas(self):
        return sorted(PresupuestoNomina.objects.filter(tipo="sueldos").values_list("cedula", flat=True))

    def test_no_vuelve_al_cargar_ni_al_recargar_todo(self):
        self.enviar([f for f in self.datos() if f["cedula"] != "10"])
        self.assertEqual(self.cedulas(), ["20"])
        r = self.client.post(reverse("nomina_cargar", args=["sueldos"]))
        self.assertIn("se habían eliminado", r.json()["msg"])
        self.assertEqual(self.cedulas(), ["20"])
        nomina_motor.recargar_bases()
        self.assertEqual(self.cedulas(), ["20"])
        self.assertFalse(PresupuestoNomina.objects.filter(cedula="10").exists())   # tampoco en prestaciones

    def test_deshacer_la_eliminacion_quita_la_marca(self):
        filas = self.datos()
        vacante = next(f for f in filas if f["cedula"] == "10")
        self.enviar([f for f in filas if f["cedula"] != "10"])
        self.enviar([f for f in self.datos()] + [dict(vacante, id=None, _uid="u1", _restaurada=True)])
        self.assertFalse(FilaEliminadaNomina.objects.exists())
        nomina_motor.recargar_bases()
        self.assertEqual(self.cedulas(), ["10", "20"])

    def test_volver_a_cargar_desde_el_tablero(self):
        self.enviar([f for f in self.datos() if f["cedula"] != "10"])
        e = FilaEliminadaNomina.objects.get()
        self.assertEqual((e.tipo, e.llave, e.nombre), ("sueldos", "10", "VACANTE"))
        html = self.client.get(reverse("presupuestoNomina")).content.decode()
        self.assertIn("Filas eliminadas que no se vuelven a cargar", html)
        self.client.post(reverse("presupuestoNomina"), {"action": "volver_a_cargar", "id": e.pk},
                         HTTP_X_REQUESTED_WITH="XMLHttpRequest")
        nomina_motor.recargar_bases()
        self.assertEqual(self.cedulas(), ["10", "20"])

    def test_filas_agregadas_en_pantalla_no_se_marcan(self):
        filas = self.datos()
        r = self.enviar(filas + [dict(filas[0], id=None, clave="", _uid="n1", cedula="30", nombre="NUEVA")])
        self.enviar([f for f in self.datos() if f["cedula"] != "30"])
        self.assertFalse(FilaEliminadaNomina.objects.exists())


class HorasExtraMesesRealesTests(TestCase):
    """Horas extra: histórico de enero hasta el mes elegido (fecha de corte o
    "meses con datos reales"), sin descartar el último; el resto con el promedio."""

    def setUp(self):
        anio = timezone.localdate().year
        valores = {m: (i + 1) * 100 for i, m in enumerate(MESES_N[:9])}      # ene=100 … sep=900
        ConceptosNomina.objects.create(anio=anio, archivo="prueba", concepto="110", cedula=10, nombre="ANA",
                                       nombre_cen="ALMACEN TULUA", nomcosto="VENTAS", **valores)
        self.config = origen_nomina.ConfiguracionNomina.actual()

    def horas(self):
        nomina_motor.recargar_bases()
        return PresupuestoNomina.objects.get(tipo="horas_extra")

    def test_meses_reales_elegidos(self):
        self.config.meses_reales = 8
        self.config.save()
        fila = self.horas()
        self.assertEqual([m for m in MESES_N if m in fila.historico], MESES_N[:8])   # enero..agosto (incluye agosto)
        factor = 1 + (nomina_motor.Parametros.cargar().incremento_salarial or 0) / 100
        self.assertEqual(fila.agosto, round(800 * factor))
        self.assertEqual(fila.septiembre, round(450 * factor))             # promedio de ene..ago = 450

    def test_fecha_de_corte(self):
        ConceptosNomina.objects.update(fecha_corte=datetime.date(timezone.localdate().year, 6, 30))
        fila = self.horas()
        self.assertEqual([m for m in MESES_N if m in fila.historico], MESES_N[:6])   # enero..junio


class AuxilioTransporteBaseTests(TestCase):
    """La base del auxilio de transporte ya no está fija en el código: se edita
    en la pantalla del concepto (o en los parámetros del tablero)."""

    def setUp(self):
        from .models import ParametrosPresupuestos
        ParametrosPresupuestos.objects.create(id=1, salario_minimo=1423500, incremento_salarial=7,
                                              auxilio_transporte=10)
        linea_nomina(origen="sistema", base=1500000, **{m: 1500000 for m in MESES_N}).save()
        nomina_motor.recalcular_todo()
        self.client.force_login(User.objects.create_user("admin"))

    def auxilio(self):
        return PresupuestoNomina.objects.get(tipo="auxilio_transporte")

    def test_sin_definir_usa_200000(self):
        f = self.auxilio()
        self.assertEqual((f.base, f.enero), (200000, 220000))

    def test_editar_la_base_recalcula(self):
        r = self.client.post(reverse("nomina_base_editable", args=["auxilio_transporte"]),
                             json.dumps({"valor": 249095}), content_type="application/json")
        self.assertEqual(r.status_code, 200, r.content)
        self.assertEqual(r.json()["valor"], 249095)
        f = self.auxilio()
        self.assertEqual((f.base, f.enero), (249095, round(249095 * 1.1)))
        self.assertTrue(any(d["tipo"] == "auxilio_transporte" for d in r.json()["data"]))

    def test_valor_invalido(self):
        for malo in ("abc", 0, -5):
            r = self.client.post(reverse("nomina_base_editable", args=["auxilio_transporte"]),
                                 json.dumps({"valor": malo}), content_type="application/json")
            self.assertEqual(r.status_code, 400, malo)

    def test_otro_concepto_no_tiene_base_editable(self):
        r = self.client.post(reverse("nomina_base_editable", args=["cesantias"]),
                             json.dumps({"valor": 5}), content_type="application/json")
        self.assertEqual(r.status_code, 400)

    def test_pantalla_muestra_el_campo(self):
        html = self.client.get(reverse("nomina_tabla", args=["auxilio_transporte"])).content.decode()
        self.assertIn('id="baseEditable"', html)
        self.assertIn('value="200000"', html)
        self.assertNotIn('id="baseEditable"', self.client.get(reverse("nomina_tabla", args=["prima"])).content.decode())


class HorasExtraSeptiembreTests(TestCase):
    """Datos reales hasta septiembre: septiembre toma su valor real (aunque sea 0)
    y el promedio va desde octubre. También si los meses reales se cambian
    después de cargar y solo se pulsa "Recalcular todo"."""

    def setUp(self):
        self.anio = timezone.localdate().year
        comunes = dict(anio=self.anio, archivo="prueba", cedula=10, nombre="ANA", nombre_cen="ALMACEN TULUA",
                       nomcosto="VENTAS")
        horas = {m: 100000 for m in MESES_N[:7]}                       # ene..jul; ago y sep en 0
        ConceptosNomina.objects.create(concepto="110", **comunes, **horas)
        ConceptosNomina.objects.create(concepto="001", concepto_f=2000000, **comunes,
                                       **{m: 2000000 for m in MESES_N[:9]})    # hay datos hasta septiembre
        self.config = origen_nomina.ConfiguracionNomina.actual()

    def horas(self):
        return PresupuestoNomina.objects.get(tipo="horas_extra")

    def test_septiembre_real_en_cero_y_promedio_desde_octubre(self):
        nomina_motor.recargar_bases()
        f = self.horas()
        self.assertEqual((f.agosto, f.septiembre), (0, 0))
        self.assertGreater(f.octubre, 0)
        self.assertEqual(f.octubre, f.diciembre)

    def test_cambiar_meses_reales_y_recalcular_todo(self):
        self.config.meses_reales = 8
        self.config.save()
        nomina_motor.recargar_bases()
        self.assertGreater(self.horas().septiembre, 0)                  # con 8 meses, septiembre es promedio
        self.config.meses_reales = 9
        self.config.save()
        nomina_motor.recalcular_todo()                                   # sin "Cargar desde Conceptos"
        f = self.horas()
        self.assertEqual(f.septiembre, 0)
        self.assertGreater(f.octubre, 0)


class RestablecerConMesesEnCeroTests(TestCase):
    """Restablecer el cálculo de una fila MANUAL: los meses que estaban en 0 se
    quedan en 0. Si todos estaban en 0 (solo se escribió la base) se calcula
    todo el año."""

    def setUp(self):
        from .models import ParametrosPresupuestos
        ParametrosPresupuestos.objects.create(id=1, salario_minimo=1423500, incremento_salarial=10)
        self.client.force_login(User.objects.create_user("admin"))

    def manual(self, meses, base=2000000, tipo="sueldos"):
        f = linea_nomina(tipo=tipo, origen="manual", base=base, clave="",
                         **{m: meses.get(m, 0) for m in MESES_N})
        f.save()
        return f

    def restablecer(self, fila, tipo="sueldos", **extra):
        datos = self.client.get(reverse("nomina_datos", args=[tipo])).json()["data"]
        for d in datos:
            if d["id"] == fila.pk:
                d["_recalcular"] = True
                d.update(extra)
        r = self.client.post(reverse("nomina_guardar", args=[tipo]), json.dumps({"filas": datos}),
                             content_type="application/json")
        self.assertEqual(r.status_code, 200, r.content)
        fila.refresh_from_db()
        return r.json()

    def test_los_meses_en_cero_se_quedan_en_cero(self):
        f = self.manual({m: 1000 for m in MESES_N[3:]})                 # ingresa en abril
        r = self.restablecer(f)
        self.assertEqual(f.origen, "sistema")
        self.assertEqual((f.enero, f.febrero, f.marzo), (0, 0, 0))
        self.assertEqual(f.abril, 2200000)                              # base + 10 %
        self.assertEqual(f.diciembre, 2200000)
        self.assertIn("se dejaron en 0", r["msg"])
        nomina_motor.recalcular_todo()                                  # se respeta al recalcular
        f.refresh_from_db()
        self.assertEqual((f.enero, f.marzo, f.abril), (0, 0, 2200000))

    def test_solo_la_base_calcula_todo_el_anio(self):
        f = self.manual({})
        self.restablecer(f)
        self.assertEqual((f.enero, f.abril, f.diciembre), (2000000, 2200000, 2200000))
        self.assertFalse(nomina_motor.meses_en_cero(f))

    def test_escribir_en_un_mes_fijo_en_cero_lo_libera(self):
        f = self.manual({m: 1000 for m in MESES_N[3:]})
        self.restablecer(f)
        datos = self.client.get(reverse("nomina_datos", args=["sueldos"])).json()["data"]
        datos[0]["marzo"] = 2200000
        self.client.post(reverse("nomina_guardar", args=["sueldos"]), json.dumps({"filas": datos}),
                         content_type="application/json")
        f.refresh_from_db()
        self.assertNotIn("marzo", nomina_motor.meses_en_cero(f))
        self.assertEqual(f.enero, 0)

    def test_promedio_sin_los_meses_en_cero(self):
        # horas extra (promedio): datos reales hasta agosto; 100.000 al mes desde abril
        config = origen_nomina.ConfiguracionNomina.actual()
        config.meses_reales = 8
        config.save()
        # (ingresó en abril: enero a marzo en 0; de septiembre a diciembre tenía valores escritos)
        f = self.manual({m: 100000 for m in MESES_N[3:]}, base=0, tipo="horas_extra")
        self.restablecer(f, tipo="horas_extra")
        self.assertEqual((f.enero, f.marzo), (0, 0))
        self.assertEqual((f.abril, f.agosto), (110000, 110000))         # real + 10 %
        self.assertEqual(f.septiembre, 110000)                          # promedio de abr-ago, sin diluir con los ceros
        self.assertEqual(f.diciembre, 110000)


class SueldosCrearEnOtrosConceptosTests(TestCase):
    """Persona nueva en Sueldos: se puede crear en cero en los conceptos que no
    dependen de Sueldos (comisiones, horas extra, medios de transporte…)."""

    def setUp(self):
        self.client.force_login(User.objects.create_user("admin"))

    def enviar(self, filas):
        r = self.client.post(reverse("nomina_guardar", args=["sueldos"]), json.dumps({"filas": filas}),
                             content_type="application/json")
        self.assertEqual(r.status_code, 200, r.content)
        return r.json()

    def datos(self):
        return self.client.get(reverse("nomina_datos", args=["sueldos"])).json()["data"]

    def tipos(self, cedula):
        return sorted(PresupuestoNomina.objects.filter(cedula=cedula).exclude(tipo="sueldos")
                      .filter(tipo__in=[c.slug for c in nomina_motor.BASE]).values_list("tipo", flat=True))

    def nueva(self, **kw):
        return {"_uid": "u1", "origen": "manual", "nombre": "", "cedula": "", "centro": "ALMACEN TULUA",
                "area": "VENTAS", "cargo": "CAJERO", "concepto": "SUELDO BASICO",
                "crear_en": ["comisiones", "horas_extra", "medios_transporte", "cesantias", "sueldos"],
                **{m: 0 for m in MESES_N}, **kw}

    def test_se_crea_en_cero_cuando_tiene_cedula(self):
        r = self.enviar([self.nueva(nombre="NUEVO")])                    # todavía sin cédula
        self.assertEqual(self.tipos(""), [])
        filas = self.datos()
        filas[0]["cedula"] = "555"
        r = self.enviar(filas)
        self.assertIn("Fila en cero creada en", r["aviso"])
        # solo conceptos base distintos de sueldos (cesantías es calculado: se ignora)
        self.assertEqual(self.tipos("555"), ["comisiones", "horas_extra", "medios_transporte"])
        otra = PresupuestoNomina.objects.get(tipo="comisiones", cedula="555")
        self.assertEqual((otra.origen, otra.nombre, otra.total, otra.area), ("manual", "NUEVO", 0, "VENTAS"))
        # no se vuelve a crear en el siguiente guardado
        self.enviar(self.datos())
        self.assertEqual(PresupuestoNomina.objects.filter(tipo="comisiones", cedula="555").count(), 1)

    def test_con_cedula_desde_el_inicio_y_sin_duplicar(self):
        linea_nomina(tipo="comisiones", cedula="777", origen="manual").save()
        self.enviar([self.nueva(cedula="777", nombre="ANA")])
        self.assertEqual(self.tipos("777"), ["comisiones", "horas_extra", "medios_transporte"])
        self.assertEqual(PresupuestoNomina.objects.filter(tipo="comisiones", cedula="777").count(), 1)

    def test_sin_elegir_no_crea_nada(self):
        self.enviar([self.nueva(cedula="888", crear_en=[])])
        self.assertEqual(self.tipos("888"), [])

    def test_la_pantalla_lista_los_conceptos(self):
        html = self.client.get(reverse("nomina_tabla", args=["sueldos"])).content.decode()
        self.assertIn('"crearEnDetalle"', html)
        self.assertIn("Horas extra", html)
        self.assertIn('id="dlgCrearEn"', html)


class AyudaTransportePegarFilaTests(TestCase):
    def test_tiene_boton_pegar_fila(self):
        self.client.force_login(User.objects.create_user("admin"))
        html = self.client.get(reverse("nomina_tabla", args=["ayuda_transporte"])).content.decode()
        self.assertIn('data-rol="pegar"', html)


class AuxilioTransporteRepartidoPorMesTests(TestCase):
    """Una persona con el sueldo en dos filas según el mes: el auxilio de
    transporte de cada mes va a la fila que tiene sueldo ese mes (no mitad y mitad)."""

    def setUp(self):
        from .models import ParametrosPresupuestos
        ParametrosPresupuestos.objects.create(id=1, salario_minimo=1750905, incremento_salarial=0,
                                              auxilio_transporte=12, base_auxilio_transporte=249095)
        aftosa = ["mayo", "junio", "noviembre", "diciembre"]
        comunes = dict(cedula="1116250847", nombre="PANESSO BARRETO SONNIA LILIANA", origen="manual",
                       cargo="SUPERNUMERARIO", concepto="SALARIO BASICO", base=2151008)
        linea_nomina(area="PROYECTO AFTOSA GASTOS DE PERSONAL", **comunes,
                     **{m: (2344599 if m in aftosa else 0) for m in MESES_N}).save()
        linea_nomina(area="VENTAS GASTOS DE PERSONAL", **comunes,
                     **{m: (0 if m in aftosa else 2344599) for m in MESES_N}).save()
        self.aftosa = aftosa
        nomina_motor.recalcular_todo()

    def test_cada_mes_en_la_fila_con_sueldo(self):
        valor = round(249095 * 1.12)                                       # 278.986
        filas = {f.area: f for f in PresupuestoNomina.objects.filter(tipo="auxilio_transporte")}
        aftosa = filas["PROYECTO AFTOSA GASTOS DE PERSONAL"]
        ventas = filas["VENTAS GASTOS DE PERSONAL"]
        for m in MESES_N:
            esperado_aftosa = valor if m in self.aftosa else 0
            self.assertEqual((m, getattr(aftosa, m)), (m, esperado_aftosa))
            self.assertEqual((m, getattr(ventas, m)), (m, valor - esperado_aftosa))
        self.assertEqual(aftosa.total + ventas.total, valor * 12)

    def test_cuotas_mensuales_sin_valor_usa_el_factor(self):
        class F:  # fila mínima
            def __init__(self, **kw):
                self.cedula, self.factor = "1", 1
                for m in MESES_N:
                    setattr(self, m, kw.get(m, 0))
        a, b = F(enero=100), F()
        cuota = nomina_motor.cuotas_mensuales([a, b], lambda f: f.cedula)
        self.assertEqual((cuota[id(a)]["enero"], cuota[id(b)]["enero"]), (1, 0))
        self.assertEqual((cuota[id(a)]["febrero"], cuota[id(b)]["febrero"]), (0.5, 0.5))


class EditarFilaCalculadaVuelveManualTests(TestCase):
    """En TODOS los conceptos base, editar un mes o un texto de una fila calculada
    la vuelve manual (antes, en los de histórico como auxilio TBC y KIT, comisiones,
    horas extra, bolsa de consumibles o auxilio de educación seguía "calculada")."""

    def setUp(self):
        from .models import ParametrosPresupuestos
        ParametrosPresupuestos.objects.create(id=1, salario_minimo=1423500, incremento_salarial=10,
                                              incremento_ipc=5, incremento_comisiones=8)
        config = origen_nomina.ConfiguracionNomina.actual()
        config.meses_reales = 8
        config.save()
        self.client.force_login(User.objects.create_user("admin"))

    def fila(self, slug):
        f = PresupuestoNomina(tipo=slug, origen="sistema", clave="9#0", cedula="9", nombre="PRUEBA",
                              centro="ALMACEN TULUA", area="VENTAS", cargo="X", concepto="C", base=1000000,
                              historico={m: 50000 for m in nomina_motor.MESES[:8]})
        nomina_motor.aplicar_formula(f, nomina_motor.CONCEPTOS[slug], nomina_motor.Parametros.cargar())
        f.save()
        return f

    def enviar(self, slug, cambios, editados=None):
        datos = self.client.get(reverse("nomina_datos", args=[slug])).json()["data"]
        datos[0].update(cambios)
        if editados is not None:
            datos[0]["_editados"] = editados
        cuerpo = {"filas": datos, **({"con_editados": True} if editados is not None else {})}
        r = self.client.post(reverse("nomina_guardar", args=[slug]), json.dumps(cuerpo),
                             content_type="application/json")
        self.assertEqual(r.status_code, 200, r.content)

    def test_todos_los_conceptos_base(self):
        for c in nomina_motor.BASE:
            for cambio in ("nombre", "marzo", "diciembre"):
                with self.subTest(concepto=c.slug, cambio=cambio):
                    f = self.fila(c.slug)
                    calculado = {m: getattr(f, m) for m in MESES_N}
                    valor = "OTRO" if cambio == "nombre" else calculado[cambio] + 12345
                    self.enviar(c.slug, {cambio: valor}, editados=[cambio])
                    f.refresh_from_db()
                    self.assertEqual(f.origen, "manual")
                    if cambio != "nombre":
                        self.assertEqual(getattr(f, cambio), valor)
                        otro = "enero" if cambio != "enero" else "febrero"
                        self.assertEqual(getattr(f, otro), calculado[otro])      # lo no editado no cambia
                    f.delete()

    def test_pantalla_vieja_no_deshace_lo_recalculado(self):
        a, b = self.fila("auxilio_tbckit"), self.fila("auxilio_tbckit")
        datos = self.client.get(reverse("nomina_datos", args=["auxilio_tbckit"])).json()["data"]
        # mientras la pantalla estaba abierta cambió el IPC y se recalculó todo
        from .models import ParametrosPresupuestos
        ParametrosPresupuestos.objects.filter(id=1).update(incremento_ipc=20)
        nomina_motor.recalcular_todo()
        nuevo_b = PresupuestoNomina.objects.get(pk=b.pk).enero
        # la pantalla vieja edita marzo de la fila A y envía TODA la tabla con los valores viejos
        fila_a = next(d for d in datos if d["id"] == a.pk)
        fila_a["marzo"] = 777
        fila_a["_editados"] = ["marzo"]
        self.client.post(reverse("nomina_guardar", args=["auxilio_tbckit"]),
                         json.dumps({"filas": datos, "con_editados": True}), content_type="application/json")
        a.refresh_from_db(); b.refresh_from_db()
        self.assertEqual((b.origen, b.enero), ("sistema", nuevo_b))                # B no se tocó
        self.assertEqual((a.origen, a.marzo, a.enero), ("manual", 777, nuevo_b))   # A: solo marzo


class InteresesCesantiasPersonaEnVariasFilasTests(TestCase):
    """Misma persona en dos filas según el mes: el acumulado de intereses no se
    reinicia cuando una de las filas tiene el mes en 0 (se lleva como una sola línea)."""

    def setUp(self):
        from .models import ParametrosPresupuestos
        ParametrosPresupuestos.objects.create(id=1, intereses_cesantias=12)
        self.aftosa = ["mayo", "junio", "noviembre", "diciembre"]
        self.ces = 218544                                    # cesantías del mes de la persona
        comunes = dict(tipo="cesantias", cedula="1116250847", nombre="PANESSO BARRETO SONNIA LILIANA",
                       origen="sistema", concepto="CESANTÍAS")
        PresupuestoNomina(area="PROYECTO AFTOSA GASTOS DE PERSONAL", clave="a", **comunes,
                          **{m: (self.ces if m in self.aftosa else 0) for m in MESES_N}).save()
        PresupuestoNomina(area="VENTAS GASTOS DE PERSONAL", clave="v", **comunes,
                          **{m: (0 if m in self.aftosa else self.ces) for m in MESES_N}).save()
        ctx = nomina_motor.Contexto()
        nomina_motor.regenerar(ctx, nomina_motor.CONCEPTOS["intereses_cesantias"])
        filas = PresupuestoNomina.objects.filter(tipo="intereses_cesantias")
        self.aftosa_f = filas.get(area__startswith="PROYECTO")
        self.ventas_f = filas.get(area__startswith="VENTAS")

    def test_valores_del_ejemplo(self):
        self.assertEqual((self.aftosa_f.mayo, self.aftosa_f.junio), (19669, 24040))
        self.assertEqual(self.ventas_f.julio, 28411)
        self.assertEqual((self.aftosa_f.julio, self.ventas_f.mayo), (0, 0))

    def test_total_igual_a_una_sola_linea(self):
        una_linea = nomina_motor.intereses_acumulados({m: self.ces for m in MESES_N}, 0.12)
        self.assertAlmostEqual(self.aftosa_f.total + self.ventas_f.total, sum(una_linea.values()), delta=12)


class CalcularSoloAuxilioEducacionTests(TestCase):
    """Botón del tablero: calcula solo el auxilio de educación (datos del año anterior)."""

    def setUp(self):
        self.client.force_login(User.objects.create_user("admin"))
        anio = timezone.localdate().year
        comunes = dict(archivo="prueba", cedula=10, nombre="ANA", nombre_cen="ALMACEN TULUA", nomcosto="VENTAS")
        ConceptosNomina.objects.create(anio=anio, concepto="001", concepto_f=2000000, **comunes,
                                       **{m: 2000000 for m in MESES_N[:8]})
        ConceptosNomina.objects.create(anio=anio - 1, concepto="016", diciembre=300000, **comunes)
        self.anio = anio

    def test_boton_y_calculo(self):
        html = self.client.get(reverse("presupuestoNomina")).content.decode()
        self.assertIn('id="btnCalcularEducacion"', html)
        self.assertIn(f"Usa los datos de {self.anio - 1}", html)
        sueldo = linea_nomina(cedula="10", origen="manual", enero=1)
        sueldo.save()
        r = self.client.post(reverse("nomina_cargar", args=["auxilio_educacion"]))
        self.assertEqual(r.json()["status"], "ok", r.content)
        self.assertTrue(PresupuestoNomina.objects.filter(tipo="auxilio_educacion", cedula="10").exists())
        sueldo.refresh_from_db()
        self.assertEqual(sueldo.enero, 1)                              # lo demás no se tocó
        self.assertFalse(PresupuestoNomina.objects.filter(tipo="cesantias").exists())

    def test_sin_datos_del_anio_anterior_deshabilitado(self):
        ConceptosNomina.objects.filter(anio=self.anio - 1).delete()
        html = self.client.get(reverse("presupuestoNomina")).content.decode()
        self.assertIn("No hay datos cargados de", html)


class IpcActualYEliminadosTests(TestCase):
    """Auxilio de educación = base × (1 + IPC año actual) × (1 + incremento IPC), y
    quien se eliminó de Sueldos no se carga en los demás conceptos."""

    def setUp(self):
        from .models import ParametrosPresupuestos
        ParametrosPresupuestos.objects.create(id=1, ipc_actual=5, incremento_ipc=4, salario_minimo=1423500)
        self.client.force_login(User.objects.create_user("admin"))
        anio = timezone.localdate().year
        for ced, nombre in [(10, "ANA"), (20, "LUIS")]:
            comunes = dict(archivo="prueba", cedula=ced, nombre=nombre, nombre_cen="ALMACEN TULUA", nomcosto="VENTAS")
            ConceptosNomina.objects.create(anio=anio, concepto="001", concepto_f=2000000, **comunes,
                                           **{m: 2000000 for m in MESES_N[:8]})
            ConceptosNomina.objects.create(anio=anio, concepto="389", **comunes, **{m: 300000 for m in MESES_N[:8]})
            ConceptosNomina.objects.create(anio=anio - 1, concepto="016", diciembre=100000, **comunes)
        nomina_motor.recargar_bases()

    def test_formula_auxilio_educacion(self):
        f = PresupuestoNomina.objects.get(tipo="auxilio_educacion", cedula="10")
        self.assertEqual(f.diciembre, round(100000 * 1.05 * 1.04))           # 109.200
        self.assertEqual(f.total, f.diciembre)

    def test_parametro_en_el_tablero(self):
        html = self.client.get(reverse("presupuestoNomina")).content.decode()
        self.assertIn('name="ipcActual"', html)
        self.client.post(reverse("presupuestoNomina"), {"ipcActual": "10", "incrementoIPC": "4"},
                         HTTP_X_REQUESTED_WITH="XMLHttpRequest")
        f = PresupuestoNomina.objects.get(tipo="auxilio_educacion", cedula="10")
        self.assertEqual(f.diciembre, round(100000 * 1.10 * 1.04))

    def test_eliminado_de_sueldos_no_se_carga_en_otros_conceptos(self):
        datos = self.client.get(reverse("nomina_datos", args=["sueldos"])).json()["data"]
        self.client.post(reverse("nomina_guardar", args=["sueldos"]),
                         json.dumps({"filas": [d for d in datos if d["cedula"] != "20"]}),
                         content_type="application/json")
        nomina_motor.recargar_bases()
        for tipo in ("sueldos", "comisiones", "auxilio_educacion"):
            self.assertEqual(sorted(PresupuestoNomina.objects.filter(tipo=tipo).values_list("cedula", flat=True)),
                             ["10"], tipo)
        # también con el botón "Calcular auxilio de educación"
        self.client.post(reverse("nomina_cargar", args=["auxilio_educacion"]))
        self.assertFalse(PresupuestoNomina.objects.filter(tipo="auxilio_educacion", cedula="20").exists())
