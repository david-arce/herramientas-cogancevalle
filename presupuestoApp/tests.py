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

from django.test import TestCase, TransactionTestCase
from django.urls import reverse
from django.utils import timezone

from . import views, views_presupuesto_areas as vpa
from .models import Cuenta5Presupuestado
from .models_presupuesto import (
    MESES, PlazoEdicionArea, PresupuestoArea, anio_elaboracion, anio_presupuesto, fecha_mes,
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
        self.client.force_login(User.objects.create_user("PLOZANO"))

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
        self.assertEqual(len(tarjetas), 14)
        self.assertEqual(tarjetas[AREA]["cuenta5"]["estado"], "pendiente")
        self.assertEqual(tarjetas["tecnologia"]["cuenta5"]["estado"], "sin_aprobar")
        self.assertContains(r, reverse("subir_cuenta5_sede", args=[AREA]))
        self.assertContains(r, "Pendiente de subir")
        self.assertContains(r, "Sin versión aprobada", count=13)

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
